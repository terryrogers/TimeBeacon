from pathlib import Path
from unittest.mock import patch
import re
from playwright.sync_api import sync_playwright, expect
from test_access import system, login, browser_headers, change
from test_auth_flows import enroll


def test_staged_login_and_email_security_administration(system):
    m,client=system;login(client);secret,codes=enroll(client);client.cookies.clear()
    with sync_playwright() as p,patch('mail_delivery.send_message') as send:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1050})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def route(route):
            req=route.request;client.cookies.clear()
            response=client.request(req.method,req.url,headers=req.headers,content=req.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route);page.route('https://gravatar.com/**',lambda route:route.abort())
        page.goto('https://testserver/login')
        expect(page.locator('#login-form')).to_be_visible();expect(page.locator('#factor-form')).to_be_hidden();expect(page.locator('#no-authenticator-link')).to_be_hidden()
        page.screenshot(path=str(Path('work/login-580.png').resolve()),full_page=True)
        page.locator('#login-form [name=username]').fill('admin');page.locator('#login-form [name=password]').fill('admin');page.locator('#login-form button').click()
        expect(page.locator('#factor-form')).to_be_visible();expect(page.locator('#login-form')).to_be_hidden();expect(page.locator('#system-cpu')).to_have_count(0)
        assert not any(cookie['name']=='timebeacon_session' for cookie in page.context.cookies())
        page.screenshot(path=str(Path('work/authenticator-580.png').resolve()),full_page=True)
        page.get_by_text('No Authenticator Code',exact=True).click();expect(page.locator('#recovery-form')).to_be_visible()
        page.locator('#email-recovery-admin').click();expect(page.locator('#login-feedback')).to_contain_text('not configured');send.assert_not_called()
        page.locator('#recovery-form [name=code]').fill(codes[0]);page.locator('#recovery-form button').click()
        expect(page.locator('#system-cpu')).to_be_visible()
        page.goto('https://testserver/admin/email')
        expect(page.locator('#page-title')).to_have_text('Email')
        form=page.locator('#admin-email-form')
        for name,value in {'hostname':'mail.example.test','username':'smtp-user','password':'synthetic-mail-password','from_email':'timebeacon@example.test','from_name':'TimeBeacon'}.items():
            form.locator('[name='+name+']').fill(value)
        form.locator('button').click();expect(page.locator('#page-feedback')).to_contain_text('Email settings saved')
        expect(form.locator('[name=password]')).to_have_value('')
        page.locator('#test-email-form [name=to_email]').fill('recipient@example.test');page.locator('#test-email-form button').click()
        expect(page.locator('#email-test-feedback')).to_contain_text('accepted by the mail server');assert send.call_count==1
        page.reload();expect(page.locator('#admin-email-form [name=hostname]')).to_have_value('mail.example.test');expect(page.locator('#admin-email-form [name=password]')).to_have_value('')
        page.screenshot(path=str(Path('work/email-580.png').resolve()),full_page=True)
        page.goto('https://testserver/user-settings')
        expect(page.locator('#profile-form button')).to_be_enabled()
        page.locator('#profile-form [name=email]').fill('admin@example.test');page.locator('#profile-form button').click();expect(page.locator('#page-feedback')).to_contain_text('Profile saved')
        page.goto('https://testserver/admin/security')
        expect(page.locator('#admin-security-form button')).to_be_enabled(timeout=5000)
        assert not errors,errors
        page.locator('#recovery-administrator').select_option('1');page.locator('#enforce-2fa').check();page.locator('#admin-security-form button').click()
        expect(page.locator('#page-feedback')).to_contain_text('Security settings saved')
        page.screenshot(path=str(Path('work/security-580.png').resolve()),full_page=True)
        page.locator('#logout-button').click();expect(page.locator('#login-form')).to_be_visible()
        page.locator('#forgot-password-link').click();page.locator('#forgot-form [name=account]').fill('admin');page.locator('#forgot-form button').click()
        expect(page.locator('#login-feedback')).to_contain_text('If that account has an email address')
        token=re.search(r'#reset=([A-Za-z0-9_-]+)',send.call_args.args[3]).group(1)
        page.goto('https://testserver/login#reset='+token)
        expect(page.locator('#reset-password-form')).to_be_visible()
        assert page.url=='https://testserver/login' and token not in page.content()
        page.locator('#reset-password-form [name=new_password]').fill('replacement-password');page.locator('#reset-password-form [name=confirm]').fill('replacement-password');page.locator('#reset-password-form button').click()
        expect(page.locator('#login-feedback')).to_contain_text('Password reset')
        expect(page.locator('#login-form')).to_be_visible()
        page.locator('#login-form [name=username]').fill('admin');page.locator('#login-form [name=password]').fill('replacement-password');page.locator('#login-form button').click()
        expect(page.locator('#factor-form')).to_be_visible()
        assert not errors,errors
        browser.close()

def test_mandatory_enrollment_browser(system):
    import pyotp
    m,client=system;login(client)
    change(client,'/administration/users',dict(username='viewer',password='viewer-password',roles=['User']))
    enroll(client)
    state=client.get('/administration/security').json()
    assert change(client,'/administration/security',{'version':state['version'],'enforce_2fa':True,'recovery_admin_id':None}).status_code==200
    client.cookies.clear()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page()
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def route(route):
            req=route.request;client.cookies.clear()
            response=client.request(req.method,req.url,headers=req.headers,content=req.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route);page.route('https://gravatar.com/**',lambda route:route.abort());page.route('**/dashboard/clocks/image?*',lambda route:route.fulfill(json={'image':None}))
        page.goto('https://testserver/login')
        page.locator('#login-form [name=username]').fill('viewer');page.locator('#login-form [name=password]').fill('viewer-password');page.locator('#login-form button').click()
        expect(page.locator('#signin-enrollment-form')).to_be_visible()
        expect(page.locator('#signin-enrollment-secret')).not_to_be_empty()
        assert not any(cookie['name']=='timebeacon_session' for cookie in page.context.cookies())
        secret=page.locator('#signin-enrollment-secret').inner_text()
        page.locator('#signin-enrollment-form [name=code]').fill(pyotp.TOTP(secret).now());page.locator('#signin-enrollment-form button').click()
        expect(page.locator('#signin-recovery-codes')).not_to_be_empty()
        expect(page.locator('#system-cpu')).to_have_count(0)
        page.locator('#finish-enrollment').click();expect(page.locator('#system-cpu')).to_be_visible()
        assert not errors,errors;browser.close()
