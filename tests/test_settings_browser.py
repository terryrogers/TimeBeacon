from test_access import browser_headers
from pathlib import Path
from unittest.mock import patch
import pytest
from playwright.sync_api import sync_playwright, expect
from test_access import system
from test_avatars import photo_bytes

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('scenario', ['clear', 'changed', 'blocked'])
def test_clipboard_countdown_never_displays_key(scenario):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page()
        page.clock.install()
        page.set_content('<form id="key-form"><input name="name" value="Test"><button>Create API Key</button></form><output id="new-key"></output><button id="copy-key-retry" hidden>Copy Key</button>')
        page.evaluate('''() => {
            window.testSecret = 'synthetic-test-only-key';
            window.clipboardValue = ''; window.blockWrite = false; window.blockRead = false;
            Object.defineProperty(navigator, 'clipboard', {value: {
                writeText: async text => {if(window.blockWrite) throw Error('blocked'); window.clipboardValue=text;},
                readText: async () => {if(window.blockRead) throw Error('blocked'); return window.clipboardValue;}
            }});
            window.accessRequest = async () => ({key: window.testSecret});
            window.listKeys = async () => {};
        }''')
        if scenario == 'blocked':
            page.evaluate('window.blockWrite=true')
        page.add_script_tag(path=str(ROOT/'static/key-clipboard.js'))
        page.evaluate('initialiseKeyClipboard()')
        page.get_by_role('button', name='Create API Key').click()
        if scenario == 'blocked':
            expect(page.locator('#new-key')).to_contain_text('clipboard access was blocked')
            page.evaluate('window.blockWrite=false')
            page.get_by_role('button', name='Copy Key', exact=True).click()
        expect(page.locator('#new-key')).to_contain_text('30 seconds')
        assert page.evaluate('window.clipboardValue===window.testSecret')
        assert 'synthetic-test-only-key' not in page.content()
        page.clock.fast_forward(15000)
        expect(page.locator('#new-key')).to_contain_text('15 seconds')
        if scenario == 'changed':
            page.evaluate("window.clipboardValue='User replacement'")
        if scenario == 'blocked':
            page.evaluate('window.blockRead=true')
        page.clock.fast_forward(15000)
        if scenario == 'blocked':
            expect(page.locator('#new-key')).to_contain_text('waiting for clipboard access')
            page.evaluate("window.blockRead=false; window.dispatchEvent(new Event('focus'))")
        expect(page.locator('#new-key')).to_contain_text('Clipboard changed' if scenario == 'changed' else 'cleared from the clipboard')
        assert page.evaluate('window.clipboardValue') == ('User replacement' if scenario == 'changed' else '')
        expect(page.get_by_role('button', name='Create API Key')).to_be_enabled()
        assert 'synthetic-test-only-key' not in page.content()
        browser.close()

def test_photo_editor_and_clock_controls(system):
    m, c = system
    with sync_playwright() as p, patch('access_api.city_image', return_value=None):
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        def route(route):
            r=route.request
            c.cookies.clear()
            response=c.request(r.method,r.url,headers=r.headers,content=r.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route)
        page.route('https://gravatar.com/**',lambda r:r.abort())
        page.goto('https://testserver/')
        page.locator('[name=username]').fill('admin')
        page.locator('[name=password]').fill('admin')
        page.locator('#login-form button').click()
        page.locator('#world-panel>summary').click()
        expect(page.locator('.clock-card').last).to_be_visible()
        for card, country in zip(page.locator('.clock-card').all(), ['us', 'gb', 'fr', 'il', 'jp', 'au']):
            expect(card.locator('.clock-zone .flag')).to_have_class(country + ' flag')
            expect(card.locator('.clock-offset')).to_contain_text('UTC ')
            assert card.locator('.clock-zone .flag').evaluate("e=>getComputedStyle(e,'::before').backgroundImage") != 'none'
            positions = card.evaluate("""card => ['.clock-city','.clock-time','.clock-date','.clock-offset'].map(selector => {
                const range=document.createRange(); range.selectNodeContents(card.querySelector(selector));
                return range.getBoundingClientRect().left;
            })""")
            assert max(positions)-min(positions)<2
        page.locator('#world-panel').screenshot(path=str(ROOT/'work/world-clocks-552.png'),animations='disabled')
        last=page.locator('.clock-card').last.bounding_box()
        manage=page.locator('.world-manage').bounding_box()
        assert abs(last['x']+last['width']-manage['x']-manage['width'])<2
        page.get_by_role('button',name='Settings',exact=True).click()
        expect(page.locator('#profile-form [name=photo]')).to_have_count(0)
        for theme in ['light', 'dark']:
            page.evaluate('(theme)=>document.documentElement.dataset.theme=theme', theme)
            page.locator('#page-title').hover()
            expect(page.locator('#edit-photo')).to_have_css('opacity', '0')
            page.locator('#profile-avatar').hover()
            expect(page.locator('#edit-photo')).to_have_css('opacity', '1')
            page.locator('#page-title').hover()
            page.locator('#edit-photo').focus()
            expect(page.locator('#edit-photo')).to_have_css('opacity', '1')
            page.locator('#profile-username').focus()
        page.locator('#profile-avatar').hover()
        page.locator('.profile-heading').screenshot(path=str(ROOT/'work/photo-hover-551.png'),animations='disabled')
        page.get_by_role('button',name='Edit',exact=True).click()
        expect(page.locator('#photo-dialog')).to_be_visible()
        page.locator('#photo-gravatar').uncheck()
        expect(page.locator('#photo-feedback')).to_have_text('Profile photo updated.')
        expect(page.locator('#photo-preview')).to_have_attribute('src','/static/avatar-default.svg')
        page.locator('#photo-file').set_input_files({'name':'sample.png','mimeType':'image/png','buffer':photo_bytes()})
        expect(page.locator('#clear-photo')).to_be_visible()
        expect(page.locator('#photo-preview')).to_have_attribute('src', __import__('re').compile('/user/avatar/'))
        page.screenshot(path=str(ROOT/'work/photo-editor-55.png'),animations='disabled')
        page.get_by_role('button',name='Clear Current Image').click()
        expect(page.locator('#clear-photo')).not_to_be_visible()
        page.get_by_role('button',name='Close Photo Editor').click()
        expect(page.locator('.personal-clock-row').first.locator('.flag')).to_have_count(1)
        expect(page.locator('.personal-clock-row').first.locator('.clock-picker-zone')).not_to_be_empty()
        expect(page.locator('.personal-clock-row').first.locator('.clock-picker-location')).to_contain_text('(')
        dropdown=page.locator('#clock-picker').bounding_box()
        add=page.get_by_role('button',name='Add Clock',exact=True).bounding_box()
        assert add['x']>dropdown['x']+dropdown['width']
        assert abs(add['y']+add['height']-dropdown['y']-dropdown['height'])<2
        page.screenshot(path=str(ROOT/'work/settings-55.png'),full_page=True,animations='disabled')
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors
        browser.close()
