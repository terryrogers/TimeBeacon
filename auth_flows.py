"""Staged sign-in, single-use account recovery and administrator security policy."""
import base64
import io
import json
import secrets
import time
import pyotp
import qrcode
import qrcode.image.svg
from fastapi import BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from security import IdentityStore, digest, password_hash
from account_api import Verification
import mail_delivery

CHALLENGE_COOKIE = 'timebeacon_challenge'


def throttle(monitor, key, maximum=10, seconds=300):
    now = int(time.time())
    with monitor.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM auth_attempts WHERE stamp<?', (now-3600,))
        count = db.execute('SELECT count(*) FROM auth_attempts WHERE address=? AND stamp>?', (key, now-seconds)).fetchone()[0]
        if count >= maximum:
            raise HTTPException(429, 'Too many attempts. Please try again later.')
        db.execute('INSERT INTO auth_attempts VALUES (?,?)', (key, now))


def policy(monitor):
    return monitor.get_settings()['settings'].get('security', {'enforce_2fa': False, 'recovery_admin_id': None})


def fingerprint(db, user_id):
    row = db.execute('SELECT password,totp,email,require_2fa FROM users WHERE id=?', (user_id,)).fetchone()
    return digest(json.dumps(row)) if row else ''


def challenge(db, monitor, request, kind):
    hashed = digest(request.cookies.get(CHALLENGE_COOKIE, ''))
    row = db.execute('SELECT user_id,fingerprint,kind,expires FROM auth_challenges WHERE token=?', (hashed,)).fetchone()
    if not row or row[2] != kind or row[3] <= time.time() or row[1] != fingerprint(db, row[0]):
        raise HTTPException(401, 'Sign-in expired. Start again with your username and password.')
    return IdentityStore(monitor).identity(db, row[0])


def session_response(db, user, extra=None):
    token = secrets.token_urlsafe(32)
    db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
    db.execute('INSERT INTO sessions VALUES (?,?,?)', (digest(token), user['id'], int(time.time())+28800))
    response = JSONResponse({'success': True, 'stage': 'complete', **(extra or {})})
    response.set_cookie('timebeacon_session', token, httponly=True, secure=True, samesite='strict', max_age=28800, path='/')
    response.delete_cookie(CHALLENGE_COOKIE, path='/')
    return response


def revoke_credentials(db, user_id):
    db.execute('DELETE FROM password_resets WHERE user_id=?', (user_id,))
    db.execute('DELETE FROM auth_challenges WHERE user_id=?', (user_id,))
    db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
    db.execute('DELETE FROM api_keys WHERE user_id=?', (user_id,))


def begin_login(monitor, request, username, password):
    store = IdentityStore(monitor)
    store.same_origin(request)
    address = request.client.host if request.client else 'unknown'
    user = store.credential(username, password, address, password_only=True)
    throttle(monitor, 'start:'+str(user['id']), 20)
    with monitor.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        current = db.execute('SELECT password FROM users WHERE id=?', (user['id'],)).fetchone()
        if not current or digest(current[0]) != user.pop('_verified_password'):
            raise HTTPException(401, 'Credentials changed. Sign in again.')
        user = store.identity(db, user['id'])
        db.execute('DELETE FROM sessions WHERE token=?', (digest(request.cookies.get('timebeacon_session', '')),))
        db.execute('DELETE FROM auth_challenges WHERE expires<? OR token=?', (time.time(), digest(request.cookies.get(CHALLENGE_COOKIE, ''))))
        totp, required = db.execute('SELECT totp,require_2fa FROM users WHERE id=?', (user['id'],)).fetchone()
        if not totp and not required and not policy(monitor).get('enforce_2fa'):
            return session_response(db, user)
        kind = 'factor' if totp else 'enroll'
        token = secrets.token_urlsafe(32)
        db.execute('INSERT INTO auth_challenges VALUES (?,?,?,?,?)', (digest(token), user['id'], fingerprint(db, user['id']), kind, int(time.time())+600))
    response = JSONResponse({'success': True, 'stage': kind})
    response.delete_cookie('timebeacon_session', path='/')
    response.set_cookie(CHALLENGE_COOKIE, token, httponly=True, secure=True, samesite='strict', max_age=600, path='/')
    return response


class Factor(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    recovery: bool = False


class ForgotPassword(BaseModel):
    username: str = Field(min_length=1, max_length=80)


class ResetPassword(BaseModel):
    token: str = Field(min_length=20, max_length=100)
    password: str = Field(min_length=8, max_length=256)


class SecurityPolicy(BaseModel):
    version: int
    enforce_2fa: bool = False
    recovery_admin_id: int | None = None


def install(app, backend):
    def store():
        return IdentityStore(backend.monitor)

    def limited_challenge(request, kind):
        store().same_origin(request)
        throttle(backend.monitor, 'factor-ip:'+(request.client.host if request.client else 'unknown'), 30)
        with backend.monitor.connect() as db:
            user = challenge(db, backend.monitor, request, kind)
        throttle(backend.monitor, 'factor-user:'+str(user['id']))
        return user

    def admin(request, mutate=False):
        user = store().authenticate(request)
        store().require(user, 'admin')
        if mutate:
            store().same_origin(request)
        return user

    @app.post('/auth/second-factor', include_in_schema=False)
    def second_factor(request: Request, body: Factor):
        limited_challenge(request, 'factor')
        if not body.recovery and (len(body.code) != 6 or not body.code.isascii() or not body.code.isdigit()):
            raise HTTPException(401, 'Enter the six-digit authenticator code')
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = challenge(db, backend.monitor, request, 'factor')
            if body.recovery:
                codes = json.loads(db.execute('SELECT recovery FROM users WHERE id=?', (user['id'],)).fetchone()[0])
                hashed = digest(body.code.replace(' ', '').lower())
                if hashed not in codes:
                    raise HTTPException(401, 'Enter an unused recovery code')
                codes.remove(hashed)
                db.execute('UPDATE users SET recovery=? WHERE id=?', (json.dumps(codes), user['id']))
            else:
                store().verify_second_factor(db, user['id'], body.code)
            db.execute('DELETE FROM auth_challenges WHERE token=?', (digest(request.cookies.get(CHALLENGE_COOKIE, '')),))
            return session_response(db, user)

    @app.post('/auth/enrollment/start', include_in_schema=False)
    def enrollment_start(request: Request):
        limited_challenge(request, 'enroll')
        secret = pyotp.random_base32()
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = challenge(db, backend.monitor, request, 'enroll')
            db.execute('UPDATE users SET totp_pending=?,totp_pending_until=? WHERE id=?', (store().cipher().encrypt(secret.encode()).decode(), int(time.time())+600, user['id']))
        uri = pyotp.TOTP(secret).provisioning_uri(name=user['username'], issuer_name='TimeBeacon')
        image = io.BytesIO()
        qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(image)
        return {'secret': secret, 'qr': 'data:image/svg+xml;base64,'+base64.b64encode(image.getvalue()).decode()}

    @app.post('/auth/enrollment/confirm', include_in_schema=False)
    def enrollment_confirm(request: Request, body: Factor):
        limited_challenge(request, 'enroll')
        codes = [secrets.token_hex(5) for _ in range(8)]
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            user = challenge(db, backend.monitor, request, 'enroll')
            pending, expiry = db.execute('SELECT totp_pending,totp_pending_until FROM users WHERE id=?', (user['id'],)).fetchone()
            if not pending or expiry <= time.time():
                raise HTTPException(401, 'Registration expired. Start again.')
            if not pyotp.TOTP(store().cipher().decrypt(pending.encode()).decode()).verify(body.code):
                raise HTTPException(401, 'Enter the current authenticator code')
            db.execute("UPDATE users SET totp=totp_pending,totp_pending='',totp_pending_until=0,totp_last=?,recovery=?,require_2fa=0 WHERE id=?", (int(time.time())//30, json.dumps([digest(code) for code in codes]), user['id']))
            db.execute('DELETE FROM auth_challenges WHERE user_id=?', (user['id'],))
            db.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
            db.execute('DELETE FROM api_keys WHERE user_id=?', (user['id'],))
            db.execute("UPDATE recovery_requests SET status='resolved' WHERE user_id=?", (user['id'],))
            return session_response(db, user, {'recovery_codes': codes})

    @app.post('/auth/forgot-password', include_in_schema=False)
    def forgot_password(request: Request, body: ForgotPassword, tasks: BackgroundTasks):
        store().same_origin(request)
        if not mail_delivery.ready(backend.monitor):
            raise HTTPException(503, 'Email recovery is not configured. Contact your administrator.')
        throttle(backend.monitor, 'forgot-ip:'+(request.client.host if request.client else 'unknown'), 10, 900)
        throttle(backend.monitor, 'forgot-name:'+digest(body.username.casefold()), 3, 900)
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT id,email FROM users WHERE username=? AND enabled=1', (body.username,)).fetchone()
            if row and row[1]:
                token = secrets.token_urlsafe(32)
                db.execute('DELETE FROM password_resets WHERE expires<? OR user_id=?', (time.time(), row[0]))
                db.execute('INSERT INTO password_resets VALUES (?,?,?,?)', (digest(token), row[0], fingerprint(db, row[0]), int(time.time())+900))
                url = mail_delivery.configuration(backend.monitor)['public_url']+'/login#reset='+token
                tasks.add_task(mail_delivery.safe_send, backend.monitor, row[1], 'Reset Your TimeBeacon Password', 'A password reset was requested for your TimeBeacon account.\n\nOpen this link within 15 minutes:\n'+url+'\n\nThis link can be used once. If you did not request this, ignore this email. Your authenticator remains enabled.')
        return {'message': 'If that account has an email address, a password reset link will be sent. Check your inbox.'}

    @app.post('/auth/reset-password', include_in_schema=False)
    def reset_password(request: Request, body: ResetPassword):
        store().same_origin(request)
        throttle(backend.monitor, 'reset-ip:'+(request.client.host if request.client else 'unknown'), 10, 900)
        hashed_password = password_hash(body.password)
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT user_id,fingerprint,expires FROM password_resets WHERE token=?', (digest(body.token),)).fetchone()
            if not row or row[2] <= time.time() or row[1] != fingerprint(db, row[0]):
                raise HTTPException(401, 'This reset link is invalid or expired. Request a new one.')
            store().identity(db, row[0])
            db.execute('UPDATE users SET password=? WHERE id=?', (hashed_password, row[0]))
            revoke_credentials(db, row[0])
        response = JSONResponse({'message': 'Password reset. Sign in with your new password.'})
        response.delete_cookie('timebeacon_session', path='/')
        response.delete_cookie(CHALLENGE_COOKIE, path='/')
        return response

    @app.post('/auth/recovery-request', include_in_schema=False)
    def recovery_request(request: Request, tasks: BackgroundTasks):
        user = limited_challenge(request, 'factor')
        administrator_id = policy(backend.monitor).get('recovery_admin_id')
        if not administrator_id or not mail_delivery.ready(backend.monitor):
            raise HTTPException(503, 'Email recovery is not configured. Contact your administrator.')
        with backend.monitor.connect() as db:
            try:
                recipient = store().identity(db, administrator_id)
                store().require(recipient, 'admin')
            except HTTPException:
                raise HTTPException(503, 'Recovery administrator unavailable. Contact your administrator.')
            email = db.execute('SELECT email FROM users WHERE id=?', (administrator_id,)).fetchone()[0]
        if not email:
            raise HTTPException(503, 'Recovery administrator has no email address.')
        throttle(backend.monitor, 'recovery-email:'+str(user['id']), 1, 900)
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            challenge(db, backend.monitor, request, 'factor')
            row = db.execute("SELECT id FROM recovery_requests WHERE user_id=? AND status='pending' AND fingerprint=?", (user['id'], fingerprint(db, user['id']))).fetchone()
            request_id = row[0] if row else db.execute('INSERT INTO recovery_requests(user_id,created,fingerprint) VALUES (?,?,?)', (user['id'], int(time.time()), fingerprint(db, user['id']))).lastrowid
        url = mail_delivery.configuration(backend.monitor)['public_url']+'/admin/security'
        tasks.add_task(mail_delivery.safe_send, backend.monitor, email, 'TimeBeacon Authenticator Recovery Request', 'Account '+user['username']+' has verified its password and requested authenticator recovery. Request '+str(request_id)+'.\n\nVerify the person through a trusted channel before permitting authenticator re-registration in Administration > Security:\n'+url+'\n\nThis email does not itself approve recovery.')
        return {'message': 'Your recovery request has been submitted and an email will be sent to the recovery administrator.'}

    @app.get('/administration/security', include_in_schema=False)
    def get_security(request: Request):
        admin(request)
        state = backend.monitor.get_settings()
        with backend.monitor.connect() as db:
            candidates = []
            for row in db.execute("SELECT id,name,username,email FROM users WHERE enabled=1 AND email!=''").fetchall():
                if 'admin' in store().identity(db, row[0])['permissions']:
                    candidates.append(dict(zip(('id', 'name', 'username', 'email'), row)))
            requests = [dict(zip(('id', 'username', 'name', 'created'), row)) for row in db.execute("SELECT r.id,u.username,u.name,r.created FROM recovery_requests r JOIN users u ON u.id=r.user_id WHERE r.status='pending' ORDER BY r.created")]
        return {'version': state['version'], 'settings': policy(backend.monitor), 'administrators': candidates, 'requests': requests}

    @app.put('/administration/security', include_in_schema=False)
    def save_security(request: Request, body: SecurityPolicy):
        user = admin(request, True)
        with backend.monitor.connect() as db:
            if body.enforce_2fa and not db.execute('SELECT totp FROM users WHERE id=?', (user['id'],)).fetchone()[0]:
                raise HTTPException(422, 'Register your own authenticator before enforcing 2FA.')
            if body.recovery_admin_id is not None:
                try:
                    target = store().identity(db, body.recovery_admin_id)
                    store().require(target, 'admin')
                except HTTPException:
                    raise HTTPException(422, 'Choose an enabled administrator with an email address.')
                if not db.execute('SELECT email FROM users WHERE id=?', (target['id'],)).fetchone()[0]:
                    raise HTTPException(422, 'The recovery administrator needs an email address.')
        saved = backend.monitor.save_settings(body.version, {'security': body.model_dump(exclude={'version'})})
        if saved is None:
            raise HTTPException(409, 'Configuration changed. Reload and retry.')
        return {'success': True, 'version': saved['version']}

    @app.post('/administration/security/recovery/{request_id}', include_in_schema=False)
    def approve_recovery(request_id: int, request: Request, body: Verification):
        user = admin(request, True)
        if policy(backend.monitor).get('recovery_admin_id') != user['id']:
            raise HTTPException(403, 'Only the configured recovery administrator can approve recovery.')
        store().credential(user['username'], body.password, request.client.host if request.client else 'unknown', body.code)
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT user_id,fingerprint FROM recovery_requests WHERE id=? AND status='pending'", (request_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'Recovery request is no longer pending.')
            if row[1] != fingerprint(db, row[0]):
                raise HTTPException(409, 'Account security changed after this request. Ask the user to submit a new request.')
            if row[0] == user['id']:
                raise HTTPException(403, 'Another recovery administrator must handle your request.')
            store().identity(db, row[0])
            db.execute("UPDATE users SET totp='',totp_pending='',totp_pending_until=0,totp_last=-1,recovery='[]',require_2fa=1 WHERE id=?", (row[0],))
            revoke_credentials(db, row[0])
            db.execute("UPDATE recovery_requests SET status='approved' WHERE id=?", (request_id,))
        return {'message': 'Recovery approved. The user must sign in with their password and register a new authenticator.'}
