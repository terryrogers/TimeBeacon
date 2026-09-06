from test_access import browser_headers
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_access import system, login, change
from test_avatars import photo_bytes

def test_admin_photo_editor_preserves_draft_and_updates_selected_account(system):
    m,c=system
    login(c)
    change(c,'/administration/users',{'username':'viewer','name':'Photo User','password':'test-password','roles':['User']})
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route(route):
            r=route.request;c.cookies.clear()
            response=c.request(r.method,r.url,headers=r.headers,content=r.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route)
        page.route('https://gravatar.com/**',lambda r:r.abort())
        page.goto('https://testserver/login')
        page.locator('[name=username]').fill('admin')
        page.locator('[name=password]').fill('admin')
        page.locator('#login-form button').click()
        expect(page.locator('#system-cpu')).to_be_visible()
        page.goto('https://testserver/admin/users')
        page.get_by_role('button',name='New User',exact=True).click()
        expect(page.locator('#edit-photo')).to_be_disabled()
        expect(page.locator('#admin-photo-note')).to_contain_text('Save this user')
        page.get_by_role('button',name='Close User Details').click()
        page.locator('#admin-users tr').filter(has_text='viewer').get_by_role('button',name='Edit',exact=True).click()
        expect(page.locator('#admin-user-form [name=photo]')).to_have_count(0)
        expect(page.locator('#onboarding-field')).to_be_hidden()
        expect(page.locator('#new-user-password')).to_be_visible()
        page.locator('#admin-user-form [name=name]').fill('Draft Name')
        page.locator('#admin-profile-avatar').hover()
        expect(page.locator('#edit-photo')).to_have_css('opacity','1')
        page.locator('#edit-photo').click()
        expect(page.locator('#photo-dialog')).to_be_visible()
        page.locator('#photo-gravatar').uncheck()
        expect(page.locator('#photo-preview')).to_have_attribute('src','/static/avatar-default.svg')
        expect(page.locator('#photo-file')).to_be_enabled()
        page.locator('#photo-file').set_input_files({'name':'sample.png','mimeType':'image/png','buffer':photo_bytes()})
        expect(page.locator('#clear-photo')).to_be_visible()
        expect(page.locator('#photo-feedback')).to_have_text('Profile photo updated.')
        page.get_by_role('button',name='Close Photo Editor').click()
        expect(page.locator('#admin-user-form [name=name]')).to_have_value('Draft Name')
        expect(page.locator('#admin-profile-avatar')).to_have_attribute('src',__import__('re').compile('/user/avatar/2'))
        page.screenshot(path=str(Path(__file__).resolve().parents[1]/'work/admin-photo-560.png'),animations='disabled')
        page.get_by_role('button',name='Save User',exact=True).click()
        expect(page.locator('#page-feedback')).to_have_text('User saved.')
        page.reload()
        row=page.locator('#admin-users tr').filter(has_text='viewer')
        expect(row).to_contain_text('Draft Name')
        expect(row.locator('img')).to_have_attribute('src',__import__('re').compile('/user/avatar/2'))
        row.get_by_role('button',name='Edit',exact=True).click()
        page.locator('#admin-profile-avatar').hover()
        page.locator('#edit-photo').click()
        page.get_by_role('button',name='Clear Current Image').click()
        expect(page.locator('#clear-photo')).not_to_be_visible()
        expect(page.locator('#photo-gravatar')).to_be_enabled()
        with page.expect_response(lambda r:r.url.endswith('/users/2/photo') and r.request.method=='PATCH') as saved:
            page.locator('#photo-gravatar').check()
        assert saved.value.json()['avatar'].startswith('https://gravatar.com/')
        assert not errors
        browser.close()
