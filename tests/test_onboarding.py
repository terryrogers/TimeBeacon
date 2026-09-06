import re
import time
from unittest.mock import patch
from test_access import system, login, change
from test_auth_flows import email_config, enroll
from security import digest

ORIGIN={'Origin':'https://testserver'}


def test_required_password_change_and_factor_sequence(system):
    m,c=system;login(c)
    change(c,'/administration/users',dict(username='newuser',password='temporary-password',roles=['User'],force_password_change=True))
    assert login(c,'newuser','temporary-password').json()['stage']=='password-change'
    assert c.get('/auth/me').status_code==401
    assert c.get('/user/profile').status_code==401
    assert c.post('/auth/change-required-password',json={'password':'temporary-password'},headers=ORIGIN).status_code==422
    assert c.post('/auth/change-required-password',json={'password':'replacement-password'}).status_code==403
    assert c.post('/auth/change-required-password',json={'password':'replacement-password'},headers=ORIGIN).json()['stage']=='complete'
    assert c.get('/auth/me').status_code==200
    assert login(c,'newuser','temporary-password').status_code==401
    login(c);_,codes=enroll(c)
    with m.connect() as db:db.execute('UPDATE users SET require_password_change=1 WHERE id=1')
    assert c.get('/auth/me').status_code==403
    assert login(c).json()['stage']=='factor'
    assert c.post('/auth/second-factor',json={'code':codes[0],'recovery':True},headers=ORIGIN).json()['stage']=='password-change'
    assert c.get('/auth/me').status_code==401
    assert c.post('/auth/change-required-password',json={'password':'updated-admin-password'},headers=ORIGIN).json()['stage']=='complete'


def test_invitation_single_use_and_templates(system):
    m,c=system;login(c)
    body=dict(username='invitee',name='New Person',email='person@example.test',roles=['User'],enabled=True,onboarding='invite')
    assert c.put('/administration/users',json=body,headers=ORIGIN).status_code==422
    email_config(c)
    with patch('mail_delivery.send_message') as sender:
        result=c.put('/administration/users',json=body,headers=ORIGIN)
        assert result.status_code==200 and sender.call_count==1
        assert sender.call_args.args[1]=='person@example.test'
        token=re.search(r'#reset=([A-Za-z0-9_-]+)',sender.call_args.args[3]).group(1)
        assert 'New Person' in sender.call_args.args[3] and '24 hours' in sender.call_args.args[3]
        assert token not in result.text
        with m.connect() as db:
            assert db.execute('SELECT token FROM password_resets').fetchone()[0]==digest(token)
        assert c.put('/administration/users',json={**body,'username':'disabled','enabled':False},headers=ORIGIN).status_code==422
        assert sender.call_count==1
    c.cookies.clear()
    with patch('auth_flows.time.time',return_value=time.time()+86401):
        assert c.post('/auth/reset-password',json={'token':token,'password':'chosen-password'},headers=ORIGIN).status_code==401
    assert c.post('/auth/reset-password',json={'token':token,'password':'chosen-password'},headers=ORIGIN).status_code==200
    assert c.post('/auth/reset-password',json={'token':token,'password':'other-password'},headers=ORIGIN).status_code==401
    assert login(c,'invitee','chosen-password').json()['stage']=='complete'


def test_html_plain_footer_and_template_validation(system):
    m,c=system;login(c);email_config(c)
    state=c.get('/administration/email').json()
    body={**state['settings'],'version':state['version'],'message_type':'html','footer':'Footer <script>bad</script>','new_user_subject':'Welcome {name}','new_user_body':'Hello {name}\nSet your password: {link}'}
    assert change(c,'/administration/email',body).status_code==200
    from mail_delivery import send_message,render_template
    subject,text=render_template(m,'new_user',name='<b>Person</b>',link='https://example.test/login#reset=synthetic')
    with patch('mail_delivery.smtplib.SMTP') as smtp:
        send_message(m,'person@example.test',subject,text)
        message=smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        assert message.is_multipart()
        plain=message.get_body(preferencelist=('plain',)).get_content()
        html=message.get_body(preferencelist=('html',)).get_content()
        assert 'Footer <script>' in plain
        assert '<script>' not in html and '&lt;script&gt;' in html
        assert '&lt;b&gt;Person&lt;/b&gt;' in html and '<a href="https://example.test/login#reset=synthetic">' in html
    body['version']=m.get_settings()['version'];body['message_type']='plain'
    assert change(c,'/administration/email',body).status_code==200
    with patch('mail_delivery.smtplib.SMTP') as smtp:
        send_message(m,'person@example.test','Test','Body')
        message=smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        assert message.get_content_type()=='text/plain' and 'Footer' in message.get_content()
    body['version']=m.get_settings()['version'];body['new_user_body']='No link'
    assert change(c,'/administration/email',body).status_code==422


def test_reference_photo_permission_and_background_preference(system):
    _,c=system
    assert c.get('/user/location/image').status_code==401
    login(c)
    assert c.get('/user/profile').json()['reference_clock']['country_code']=='gb'
    with patch('places.city_image',return_value={'city':'London','image_url':'https://upload.wikimedia.org/test.jpg'}) as image:
        assert c.get('/user/location/image').json()['image']['city']=='London'
        image.assert_called_once()
        c.put('/user/clock-backgrounds',json={'enabled':False},headers=ORIGIN)
        assert c.get('/user/location/image').json()['image'] is None
        assert image.call_count==1
        c.put('/user/clock-backgrounds',json={'enabled':True},headers=ORIGIN)
        c.delete('/user/location',headers=ORIGIN)
        assert c.get('/user/location/image').json()['image'] is None


def test_force_password_change_then_mandatory_enrollment(system):
    m,c=system;login(c)
    from auth_flows import fingerprint
    import json
    with m.connect() as db:
        old=db.execute('SELECT password,totp,email,require_2fa FROM users WHERE id=1').fetchone()
        assert fingerprint(db,1)==digest(json.dumps(old))
    _,codes=enroll(c)
    change(c,'/administration/security',dict(version=m.get_settings()['version'],enforce_2fa=True))
    change(c,'/administration/users',dict(username='required',password='temporary-password',roles=['User'],force_password_change=True))
    assert login(c,'required','temporary-password').json()['stage']=='password-change'
    assert c.post('/auth/change-required-password',json={'password':'chosen-password'},headers=ORIGIN).json()['stage']=='enroll'
    assert c.get('/auth/me').status_code==401
