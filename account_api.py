"""Personal profiles, daylight preferences and authenticator registration."""

import base64
import hashlib
import io
import json
import secrets
import time
import urllib.parse
import urllib.request
import pyotp
import qrcode
import qrcode.image.svg
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from security import IdentityStore, digest


class ProfileInput(BaseModel):
    name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    photo: str = Field(default="", max_length=2000)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if value and (
            "@" not in value
            or "." not in value.split("@")[-1]
            or any(c.isspace() for c in value)
        ):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("photo")
    @classmethod
    def photo_valid(cls, value):
        value = value.strip()
        if value:
            url = urllib.parse.urlsplit(value)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("Use an HTTPS photo URL, or leave empty for Gravatar")
        return value


class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class ClockBackgrounds(BaseModel):
    enabled: bool


class Verification(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    code: str = Field(default="", max_length=80)


class Confirm(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


def profile(db, user_id):
    row = db.execute(
        "SELECT name,email,photo,totp,location,clock_backgrounds,gravatar_enabled,avatar_upload,version FROM users WHERE id=?", (user_id,)
    ).fetchone()
    return dict(
        name=row[0],
        email=row[1],
        photo=row[2],
        two_factor=bool(row[3]),
        avatar=(f'/user/avatar/{user_id}?v={row[8]}' if row[7] else row[2]
        or ("https://gravatar.com/avatar/"
        + hashlib.sha256(row[1].strip().lower().encode()).hexdigest()
        + "?s=160&d=mp" if row[6] else '/static/avatar-default.svg')),
        gravatar_enabled=bool(row[6]),
        custom_photo=bool(row[7] or row[2]),
        location=json.loads(row[4]),
        clock_backgrounds=bool(row[5]),
    )


def install(app, backend):
    def store():
        return IdentityStore(backend.monitor)

    def user(request, mutate=False):
        result = store().authenticate(request)
        if mutate:
            store().same_origin(request)
        return result

    def reauthenticate(request, identity, body):
        return store().credential(
            identity["username"],
            body.password,
            request.client.host if request.client else "unknown",
            body.code,
        )

    @app.put('/user/clock-backgrounds', include_in_schema=False)
    def save_clock_backgrounds(request: Request, body: ClockBackgrounds):
        identity = user(request, True)
        with backend.monitor.connect() as db:
            db.execute('UPDATE users SET clock_backgrounds=?,version=version+1 WHERE id=?', (body.enabled,identity['id']))
        return {'success':True, 'enabled':body.enabled}

    @app.get("/user/profile", include_in_schema=False)
    def get_profile(request: Request):
        identity = user(request)
        with backend.monitor.connect() as db:
            return profile(db, identity["id"])

    @app.put("/user/profile", include_in_schema=False)
    def save_profile(request: Request, body: ProfileInput):
        identity = user(request, True)
        with backend.monitor.connect() as db:
            db.execute(
                "UPDATE users SET name=?,email=? WHERE id=?",
                (body.name, body.email, identity["id"]),
            )
            if 'photo' in body.model_fields_set:
                db.execute('UPDATE users SET photo=?,avatar_upload=NULL,version=version+1 WHERE id=?', (body.photo,identity['id']))
            return profile(db, identity["id"])

    @app.post("/user/location", include_in_schema=False)
    def save_location(request: Request, body: LocationInput):
        identity = user(request, True)
        # Shared SQLite cache/rate gate also covers multiple web workers.
        key = f"{body.latitude:.3f},{body.longitude:.3f}"
        with backend.monitor.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS geocodes(key TEXT PRIMARY KEY,payload TEXT,stamp REAL)"
            )
            db.execute("BEGIN IMMEDIATE")
            cached = db.execute(
                "SELECT payload FROM geocodes WHERE key=? AND stamp>?",
                (key, time.time() - 2592000),
            ).fetchone()
            if not cached:
                last = db.execute(
                    "SELECT stamp FROM geocodes WHERE key='rate-limit'"
                ).fetchone()
                if last and time.time() - last[0] < 1.1:
                    raise HTTPException(
                        429, "Please wait a moment before locating again"
                    )
                db.execute(
                    "INSERT OR REPLACE INTO geocodes VALUES ('rate-limit','',?)",
                    (time.time(),),
                )
        if cached:
            city = cached[0]
        else:
            query = urllib.parse.urlencode(
                dict(
                    format="jsonv2",
                    lat=round(body.latitude, 3),
                    lon=round(body.longitude, 3),
                    zoom=10,
                    addressdetails=1,
                )
            )
            req = urllib.request.Request(
                "https://nominatim.openstreetmap.org/reverse?" + query,
                headers={
                    "User-Agent": "TimeBeacon/5.0 (https://github.com/terryrogers/TimeBeacon)"
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    address = json.load(response).get("address", {})
                city = next(
                    (
                        address[k]
                        for k in ("city", "town", "municipality", "village", "county")
                        if address.get(k)
                    ),
                    None,
                )
                if not city:
                    raise ValueError()
            except Exception:
                raise HTTPException(
                    503,
                    "Town/city lookup unavailable. Your previous location has been kept; please try again later.",
                )
            with backend.monitor.connect() as db:
                db.execute(
                    "INSERT OR REPLACE INTO geocodes VALUES (?,?,?)",
                    (key, city, time.time()),
                )
        location = dict(location=city, latitude=body.latitude, longitude=body.longitude)
        with backend.monitor.connect() as db:
            db.execute(
                "UPDATE users SET location=?,version=version+1 WHERE id=?",
                (json.dumps(location), identity["id"]),
            )
        return location

    @app.post("/user/2fa/register", include_in_schema=False)
    def register(request: Request, body: Verification):
        identity = user(request, True)
        reauthenticate(request, identity, body)
        secret = pyotp.random_base32()
        with backend.monitor.connect() as db:
            if db.execute(
                "SELECT totp FROM users WHERE id=?", (identity["id"],)
            ).fetchone()[0]:
                raise HTTPException(
                    409, "Two-factor authentication is already registered"
                )
            db.execute(
                "UPDATE users SET totp_pending=?,totp_pending_until=? WHERE id=?",
                (
                    store().cipher().encrypt(secret.encode()).decode(),
                    int(time.time()) + 600,
                    identity["id"],
                ),
            )
        uri = pyotp.TOTP(secret).provisioning_uri(
            name=identity["username"], issuer_name="TimeBeacon"
        )
        output = io.BytesIO()
        qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(output)
        return {
            "secret": secret,
            "qr": "data:image/svg+xml;base64,"
            + base64.b64encode(output.getvalue()).decode(),
        }

    @app.post("/user/2fa/confirm", include_in_schema=False)
    def confirm(request: Request, body: Confirm):
        identity = user(request, True)
        address = "enroll:" + str(identity["id"])
        with backend.monitor.connect() as db:
            db.execute("DELETE FROM login_attempts WHERE stamp<?", (time.time() - 300,))
            if (
                db.execute(
                    "SELECT count(*) FROM login_attempts WHERE address=?", (address,)
                ).fetchone()[0]
                >= 10
            ):
                raise HTTPException(
                    429, "Too many attempts. Try again in five minutes."
                )
            db.execute(
                "INSERT INTO login_attempts VALUES (?,?)", (address, time.time())
            )
        codes = [secrets.token_hex(5) for _ in range(8)]
        with backend.monitor.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            pending, expiry, enabled = db.execute(
                "SELECT totp_pending,totp_pending_until,totp FROM users WHERE id=?",
                (identity["id"],),
            ).fetchone()
            if enabled or not pending or expiry < time.time():
                raise HTTPException(409, "Start a new registration")
            totp = pyotp.TOTP(store().cipher().decrypt(pending.encode()).decode())
            if not totp.verify(body.code):
                raise HTTPException(
                    422, "Incorrect code. Try the latest code from your authenticator."
                )
            db.execute(
                "UPDATE users SET totp=totp_pending,totp_pending='',totp_pending_until=0,totp_last=?,recovery=? WHERE id=?",
                (
                    int(time.time()) // 30,
                    json.dumps([digest(c) for c in codes]),
                    identity["id"],
                ),
            )
            db.execute(
                "DELETE FROM sessions WHERE user_id=? AND token!=?",
                (identity["id"], digest(request.cookies.get("timebeacon_session", ""))),
            )
        return {
            "recovery_codes": codes,
            "message": "Save these recovery codes securely. Each can be used once.",
        }

    @app.post("/user/2fa/disable", include_in_schema=False)
    def disable(request: Request, body: Verification):
        identity = user(request, True)
        reauthenticate(request, identity, body)
        with backend.monitor.connect() as db:
            db.execute(
                "UPDATE users SET totp='',totp_pending='',recovery='[]',totp_last=-1 WHERE id=?",
                (identity["id"],),
            )
        return {"success": True}
