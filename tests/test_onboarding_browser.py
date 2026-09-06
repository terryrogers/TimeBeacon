import re
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from test_access import system,login,browser_headers
from test_auth_flows import email_config
from test_avatars import photo_bytes


def test_account_setup_email_editor_and_reference_photo(system):
    m,client=system;login(client);email_config(client);client.cookies.clear()
    photo=dict(city='London',image_url='https://upload.wikimedia.org/test.png',artist='Test Artist',credit='Test Photo',license='CC BY-SA 4.0',source_url='https://commons.wikimedia.org/wiki/File:Test.png')
    with sync_playwright() as p,patch('places.city_image',return_value=photo),patch('mail_delivery.send_message') as sender:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1100})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        def route(route):
            req=route.request;client.cookies.clear();response=client.request(req.method,req.url,headers=req.headers,content=req.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route);page.route('https://gravatar.com/**',lambda r:r.abort());page.route('https://upload.wikimedia.org/test.png',lambda r:r.fulfill(content_type='image/png',body=photo_bytes()))
        page.goto('https://testserver/login');page.locator('#login-form [name=username]').fill('admin');page.locator('#login-form [name=password]').fill('admin');page.locator('#login-form button').click();expect(page.locator('#system-cpu')).to_be_visible()
        page.goto('https://testserver/user-settings');expect(page.locator('#reference-clock .gb.flag')).to_have_count(1)
        expect(page.locator('#get-location')).to_be_enabled()
        expect(page.locator('.daylight-photo')).to_be_visible();page.get_by_role('button',name='Reference Clock Photo Credit').click();expect(page.locator('#reference-photo-dialog')).to_be_visible();page.get_by_role('button',name='Close Reference Photo Credit').click()
        for theme in ['light','dark']:
            page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
            panel=page.locator('#daylight-display').bounding_box();image=page.locator('.daylight-photo').bounding_box()
            assert abs(panel['height']-image['height'])<=2 and abs(panel['width']-image['width'])<=2
            page.locator('#daylight-display').screenshot(path=str(Path('work/daylight-photo-590-'+theme+'.png').resolve()))
        page.locator('#clock-backgrounds').uncheck();expect(page.locator('.daylight-photo')).to_have_count(0)
        page.locator('#clock-backgrounds').check();expect(page.locator('.daylight-photo')).to_be_visible()
        page.goto('https://testserver/admin/email');form=page.locator('#admin-email-form');expect(form.locator('[name=hostname]')).to_have_value('mail.example.test')
        form.locator('[name=message_type]').select_option('html');form.locator('[name=footer]').fill('Example Footer')
        form.locator('[name=new_user_subject]').fill('Welcome {name}');form.locator('[name=password_reset_subject]').fill('Reset {product} Password');form.locator('button').click();expect(page.locator('#page-feedback')).to_contain_text('Email settings saved')
        page.reload();expect(form.locator('[name=footer]')).to_have_value('Example Footer');expect(form.locator('[name=message_type]')).to_have_value('html')
        page.goto('https://testserver/admin/users');page.locator('#new-user').click();form=page.locator('#admin-user-form')
        expect(page.locator('#user-roles')).to_have_value('User')
        for field,value in dict(name='New Person',username='newperson',email='person@example.test',password='temporary-password').items():form.locator('[name='+field+']').fill(value)
        form.locator('[name=enabled]').check();page.locator('#force-password-change').check();form.locator('button').click();expect(page.locator('#page-feedback')).to_have_text('User saved.')
        page.locator('#logout-button').click();page.locator('#login-form [name=username]').fill('newperson');page.locator('#login-form [name=password]').fill('temporary-password');page.locator('#login-form button').click()
        expect(page.locator('#required-password-form')).to_be_visible();expect(page.locator('#system-cpu')).to_have_count(0)
        page.locator('#required-password-form [name=required_password]').fill('chosen-password');page.locator('#required-password-form [name=confirm]').fill('chosen-password');page.locator('#required-password-form button').click();expect(page.locator('#system-cpu')).to_be_visible()
        page.locator('#logout-button').click();page.locator('#login-form [name=username]').fill('admin');page.locator('#login-form [name=password]').fill('admin');page.locator('#login-form button').click();expect(page.locator('#system-cpu')).to_be_visible()
        page.goto('https://testserver/admin/users');page.locator('#new-user').click();form=page.locator('#admin-user-form')
        page.locator('#onboarding-method').select_option('invite');expect(page.locator('#new-user-password')).to_be_hidden();expect(page.locator('#force-password-field')).to_be_hidden()
        for field,value in dict(name='Invited Person',username='invited',email='invited@example.test').items():form.locator('[name='+field+']').fill(value)
        form.locator('[name=enabled]').check();form.locator('button').click();expect(page.locator('#page-feedback')).to_contain_text('setup link will be emailed')
        assert sender.call_count==1 and sender.call_args.args[2]=='Welcome Invited Person'
        token=re.search(r'#reset=([A-Za-z0-9_-]+)',sender.call_args.args[3]).group(1)
        page.locator('#logout-button').click();expect(page.locator('#login-form button')).to_be_enabled();page.goto('https://testserver/login#reset='+token);expect(page.locator('#reset-password-form')).to_be_visible();assert token not in page.url
        page.locator('#reset-password-form [name=new_password]').fill('invitation-password');page.locator('#reset-password-form [name=confirm]').fill('invitation-password');page.locator('#reset-password-form button').click();expect(page.locator('#login-feedback')).to_contain_text('Password reset')
        page.locator('#login-form [name=username]').fill('invited');page.locator('#login-form [name=password]').fill('invitation-password');page.locator('#login-form button').click();expect(page.locator('#system-cpu')).to_be_visible()
        assert not errors,errors;browser.close()
