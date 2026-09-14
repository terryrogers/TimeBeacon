import json
import re
import time
from unittest.mock import patch, MagicMock
import pyotp
from test_access import system, login, change
from security import IdentityStore, digest
from auth_flows import policy

ORIGIN={'Origin':'https://testserver'}


def enroll(client):
    result=client.post('/user/2fa/register',json={'password':'admin'},headers=ORIGIN).json()
    codes=client.post('/user/2fa/confirm',json={'code':pyotp.TOTP(result['secret']).now()},headers=ORIGIN).json()['recovery_codes']
    return result['secret'],codes


def email_config(client):
    version=client.get('/administration/email').json()['version']
    return change(client,'/administration/email',dict(version=version,hostname='mail.example.test',port=587,security='starttls',username='smtp-user',password='synthetic-mail-password',from_email='timebeacon@example.test',from_name='TimeBeacon',public_url='https://testserver'))


def test_email_configuration_encryption_and_transports(system):
    m,c=system;login(c)
    assert email_config(c).status_code==200
    values=c.get('/administration/email').json()
    assert values['settings']['password_set']
    assert 'password_encrypted' not in values['settings']
    assert 'synthetic-mail-password' not in c.get('/administration').text
    stored=m.get_settings()['settings']['email']
    assert stored['password_encrypted']!='synthetic-mail-password'
    assert IdentityStore(m).cipher().decrypt(stored['password_encrypted'].encode()).decode()=='synthetic-mail-password'
    assert 'email' not in c.get('/administration').json()['config']
    for mode in ['starttls','ssl','none']:
        body={**values['settings'],'version':m.get_settings()['version'],'security':mode,'password':'','username':'' if mode=='none' else 'smtp-user'}
        assert change(c,'/administration/email',body).status_code==200
        with patch('mail_delivery.smtplib.SMTP') as smtp,patch('mail_delivery.smtplib.SMTP_SSL') as ssl:
            response=c.post('/administration/email/test',json={'to_email':'recipient@example.test'},headers=ORIGIN)
            assert response.status_code==200
            connection=(ssl if mode=='ssl' else smtp).return_value.__enter__.return_value
            assert connection.send_message.call_count==1
            assert connection.starttls.call_count==(1 if mode=='starttls' else 0)
            assert connection.login.call_count==(0 if mode=='none' else 1)
            assert (ssl if mode=='ssl' else smtp).call_args.kwargs.get('timeout')==15
    body={**values['settings'],'version':m.get_settings()['version'],'security':'none','username':'smtp-user'}
    assert change(c,'/administration/email',body).status_code==422
    body['security']='ssl';body['public_url']='http://evil.example.test'
    assert change(c,'/administration/email',body).status_code==422
    assert c.post('/administration/email/test',json={'to_email':'recipient@example.test'}).status_code==403
    change(c,'/administration/users',dict(username='viewer',password='viewer-password',roles=['User']))
    login(c,'viewer','viewer-password')
    assert c.get('/administration/email').status_code==403
    assert c.post('/administration/email/test',json={'to_email':'recipient@example.test'},headers=ORIGIN).status_code==403


def test_password_reset_single_use_expiry_and_account_privacy(system):
    m,c=system;login(c);email_config(c)
    c.put('/user/profile',json={'name':'Test Admin','email':'admin@example.test'},headers=ORIGIN)
    secret,codes=enroll(c)
    c.cookies.clear()
    with patch('mail_delivery.send_message') as sender:
        unknown=c.post('/auth/forgot-password',json={'username':'unknown'},headers=ORIGIN)
        known=c.post('/auth/forgot-password',json={'username':'admin'},headers=ORIGIN)
        assert unknown.json()==known.json()
        assert sender.call_count==1
        text=sender.call_args.args[3];token=re.search(r'#reset=([A-Za-z0-9_-]+)',text).group(1)
        assert token not in known.text
        with m.connect() as db:
            saved=db.execute('SELECT token FROM password_resets').fetchone()[0]
            assert saved==digest(token) and saved!=token
        response=c.post('/auth/reset-password',json={'token':token,'password':'new-admin-password'},headers=ORIGIN)
        assert response.status_code==200
        assert c.get('/auth/me').status_code==401
        assert c.post('/auth/reset-password',json={'token':token,'password':'another-password'},headers=ORIGIN).status_code==401
        assert login(c,'admin','new-admin-password').json()['stage']=='factor'
        assert c.post('/auth/second-factor',json={'code':codes[0],'recovery':True},headers=ORIGIN).status_code==200
        c.post('/auth/forgot-password',json={'username':'admin'},headers=ORIGIN)
        token=re.search(r'#reset=([A-Za-z0-9_-]+)',sender.call_args.args[3]).group(1)
        with patch('auth_flows.time.time',return_value=time.time()+901):
            assert c.post('/auth/reset-password',json={'token':token,'password':'another-password'},headers=ORIGIN).status_code==401
        with m.connect() as db:
            assert db.execute('SELECT totp FROM users WHERE id=1').fetchone()[0]
    assert c.post('/auth/forgot-password',json={'username':'admin'}).status_code==403


def test_challenge_is_not_a_session_and_expires(system):
    m,c=system;login(c);secret,codes=enroll(c);c.cookies.clear()
    assert c.post('/auth/login',json={'username':'admin','password':'admin','code':codes[0]},headers=ORIGIN).json()['stage']=='factor'
    for url in ['/auth/me','/dashboard/data','/user/profile','/administration/security','/administration/email']:
        assert c.get(url).status_code in (401,404)
    assert c.get('/',follow_redirects=False).status_code==303
    assert c.post('/auth/second-factor',json={'code':codes[0],'recovery':True}).status_code==403
    with patch('auth_flows.time.time',return_value=time.time()+601):
        assert c.post('/auth/second-factor',json={'code':codes[0],'recovery':True},headers=ORIGIN).status_code==401
    assert login(c).json()['stage']=='factor'
    with m.connect() as db:db.execute("UPDATE users SET email='changed@example.test' WHERE id=1")
    assert c.post('/auth/second-factor',json={'code':codes[0],'recovery':True},headers=ORIGIN).status_code==401


def test_enforcement_requires_enrollment_and_blocks_api(system):
    m,c=system;login(c)
    change(c,'/administration/users',dict(username='viewer',password='viewer-password',roles=['User']))
    body={'version':m.get_settings()['version'],'enforce_2fa':True,'recovery_admin_id':None}
    assert change(c,'/administration/security',body).status_code==422
    secret,codes=enroll(c)
    assert change(c,'/administration/security',body).status_code==200
    assert c.post('/user/2fa/disable',json={'password':'admin','code':codes[0]},headers=ORIGIN).status_code==403
    c.cookies.clear();assert login(c,'viewer','viewer-password').json()['stage']=='enroll'
    assert c.get('/auth/me').status_code==401
    registration=c.post('/auth/enrollment/start',json={},headers=ORIGIN).json()
    assert c.post('/auth/second-factor',json={'code':'123456'},headers=ORIGIN).status_code==401
    response=c.post('/auth/enrollment/confirm',json={'code':pyotp.TOTP(registration['secret']).now()},headers=ORIGIN)
    assert response.status_code==200 and len(response.json()['recovery_codes'])==8
    assert c.get('/auth/me').status_code==200
    assert c.get('/administration/security').status_code==403
    assert c.post('/auth/enrollment/confirm',json={'code':pyotp.TOTP(registration['secret']).now()},headers=ORIGIN).status_code==401


def test_administrator_recovery_requires_confirmation_and_new_enrollment(system):
    m,c=system;login(c);email_config(c)
    change(c,'/administration/users',dict(username='recoveryadmin',password='recovery-password',roles=['Administrator']))
    recovery_id=[u['id'] for u in c.get('/administration').json()['users'] if u['username']=='recoveryadmin'][0]
    assert change(c,'/administration/security',{'version':m.get_settings()['version'],'enforce_2fa':False,'recovery_admin_id':recovery_id}).status_code==200
    secret,codes=enroll(c);c.cookies.clear();login(c)
    with patch('mail_delivery.send_message') as sender:
        assert c.post('/auth/recovery-request',json={},headers=ORIGIN).status_code==200
        assert sender.call_count==1
        assert c.post('/auth/recovery-request',json={},headers=ORIGIN).status_code==429
    assert c.get('/auth/me').status_code==401
    c.cookies.clear();login(c,'recoveryadmin','recovery-password')
    state=c.get('/administration/security').json();request_id=state['requests'][0]['id']
    url='/administration/security/recovery/'+str(request_id)
    assert c.post(url,json={'password':'wrong'},headers=ORIGIN).status_code==401
    assert c.post(url,json={'password':'recovery-password'},headers=ORIGIN).status_code==200
    c.cookies.clear();assert login(c).json()['stage']=='enroll'
    assert c.get('/auth/me').status_code==401
    with m.connect() as db:
        assert db.execute('SELECT require_2fa,totp FROM users WHERE id=1').fetchone()==(1,'')

def test_existing_sessions_and_keys_are_denied_when_2fa_is_required(system):
    m,c=system;login(c)
    key=c.post('/user/keys',json={'name':'Synthetic API key'},headers=ORIGIN).json()['key']
    with m.connect() as db:db.execute('UPDATE users SET require_2fa=1 WHERE id=1')
    assert c.get('/auth/me').status_code==403
    assert c.get('/server/status',headers={'Authorization':'Bearer '+key}).status_code==403
    assert login(c).json()['stage']=='enroll'


def test_reset_rejects_disabled_and_changed_accounts_and_mail_failures(system):
    m,c=system;login(c);email_config(c)
    c.put('/user/profile',json={'email':'admin@example.test'},headers=ORIGIN)
    with patch('mail_delivery.send_message') as sender:
        c.post('/auth/forgot-password',json={'username':'admin'},headers=ORIGIN)
        token=re.search(r'#reset=([A-Za-z0-9_-]+)',sender.call_args.args[3]).group(1)
        with m.connect() as db:db.execute("UPDATE users SET email='other@example.test' WHERE id=1")
        assert c.post('/auth/reset-password',json={'token':token,'password':'new-password'},headers=ORIGIN).status_code==401
        c.post('/auth/forgot-password',json={'username':'admin'},headers=ORIGIN)
        token=re.search(r'#reset=([A-Za-z0-9_-]+)',sender.call_args.args[3]).group(1)
        with m.connect() as db:db.execute('UPDATE users SET enabled=0 WHERE id=1')
        assert c.post('/auth/reset-password',json={'token':token,'password':'new-password'},headers=ORIGIN).status_code==401
        with m.connect() as db:db.execute('UPDATE users SET enabled=1 WHERE id=1')
    with patch('mail_delivery.send_message',side_effect=OSError('synthetic failure')):
        assert c.post('/auth/forgot-password',json={'username':'admin'},headers=ORIGIN).status_code==200
