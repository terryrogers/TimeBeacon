from test_access import browser_headers
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_access import system


def test_clock_controls_and_admin_defaults(system):
    m,client=system
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True,ignore_default_args=['--hide-scrollbars'])
        page=browser.new_page(viewport={'width':1600,'height':1100})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        def route(route):
            r=route.request;client.cookies.clear()
            response=client.request(r.method,r.url,headers=r.headers,content=r.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route)
        page.route('**/dashboard/clocks/image?*',lambda r:r.fulfill(json={'image':None}))
        page.route('https://gravatar.com/**',lambda r:r.abort())
        page.goto('https://testserver/')
        page.locator('[name=username]').fill('admin');page.locator('[name=password]').fill('admin');page.locator('#login-form button').click()
        expect(page.locator('#world-panel')).to_be_visible()
        expect(page.locator('#reset-clocks')).to_have_count(0)
        page.goto('https://testserver/user-settings#user-clocks')
        page.locator('#reset-clocks').click()
        expect(page.locator('#clock-feedback')).to_contain_text('reset to system defaults')
        page.goto('https://testserver/')
        page.locator('#world-panel>summary').click()
        expect(page.locator('.clock-card')).to_have_count(6)
        expect(page.locator('.clock-card').first).to_contain_text('Los Angeles')
        expect(page.locator('.clock-card').first.locator('.clock-drag circle')).to_have_count(9)
        handle=page.locator('.clock-card').first.locator('.clock-drag').bounding_box()
        remove=page.locator('.clock-card').first.locator('.clock-remove').bounding_box()
        title=page.locator('.clock-card').first.locator('.clock-city').bounding_box()
        assert remove['x']+remove['width']<=handle['x']
        assert handle['y']+handle['height']<=title['y']
        page.screenshot(path=str(Path('work/clocks-571.png').resolve()),full_page=True)
        page.get_by_role('button',name='Reorder Los Angeles clock',exact=True).press('ArrowRight')
        expect(page.locator('.clock-card').first).to_contain_text('New York')
        # Real pointer drag on the dashboard, saving the new order.
        source=page.get_by_role('button',name='Reorder New York clock',exact=True).bounding_box()
        target=page.locator('.clock-card').nth(2).bounding_box()
        page.mouse.move(source['x']+14,source['y']+14);page.mouse.down();page.mouse.move(target['x']+60,target['y']+65,steps=12)
        expect(page.locator('.clock-drag-preview')).to_be_visible()
        preview=page.locator('.clock-drag-preview').bounding_box()
        page.mouse.move(target['x']+85,target['y']+70)
        moved=page.locator('.clock-drag-preview').bounding_box()
        assert moved['x']!=preview['x']
        page.mouse.up()
        expect(page.locator('.clock-drag-preview')).to_have_count(0)
        expect(page.locator('.clock-card').nth(2)).to_contain_text('New York')
        # Escape cancels an in-progress drag and removes its preview without saving.
        source=page.get_by_role('button',name='Reorder New York clock',exact=True).bounding_box()
        page.mouse.move(source['x']+14,source['y']+14);page.mouse.down();page.mouse.move(source['x']-60,source['y']+50,steps=8)
        expect(page.locator('.clock-drag-preview')).to_be_visible()
        page.keyboard.press('Escape');page.mouse.up()
        expect(page.locator('.clock-drag-preview')).to_have_count(0)
        expect(page.locator('.clock-card').nth(2)).to_contain_text('New York')
        page.get_by_role('button',name='Remove Dubai clock',exact=True).click()
        expect(page.locator('.clock-card')).to_have_count(5)
        page.reload();page.locator('#world-panel>summary').click()
        expect(page.locator('.clock-card')).to_have_count(5)
        expect(page.locator('.clock-card').nth(2)).to_contain_text('New York')
        page.goto('https://testserver/user-settings#user-clocks')
        expect(page.locator('.personal-clock-row')).to_have_count(5)
        source=page.locator('.clock-drag').first.bounding_box();target=page.locator('.personal-clock-row').nth(2).bounding_box()
        page.mouse.move(source['x']+8,source['y']+8);page.mouse.down();page.mouse.move(target['x']+80,target['y']+20,steps=12)
        expect(page.locator('.clock-drag-preview')).to_be_visible()
        preview=page.locator('.clock-drag-preview').bounding_box()
        page.mouse.move(target['x']+100,target['y']+20)
        assert page.locator('.clock-drag-preview').bounding_box()['x']>preview['x']
        page.mouse.up()
        expect(page.locator('.clock-drag-preview')).to_have_count(0)
        expect(page.locator('.personal-clock-row').nth(2)).to_contain_text('America/Los_Angeles')
        page.locator('#reset-clocks').click()
        expect(page.locator('.personal-clock-row')).to_have_count(6)
        page.goto('https://testserver/admin/defaults')
        expect(page.locator('#page-title')).to_have_text('Defaults')
        expect(page.locator('#default-clock-1')).to_have_value('America/Los_Angeles')
        expect(page.locator('#default-picker-1 > .text .flag')).to_have_count(1)
        expect(page.locator('#default-picker-1 > .text .clock-picker-location')).to_contain_text('UTC -')
        page.locator('#default-picker-1 input.search').fill('Tokyo')
        page.locator('#default-picker-1 .menu .item[data-value="Asia/Tokyo"]').click()
        page.get_by_role('button',name='Save Defaults',exact=True).click()
        expect(page.locator('#page-feedback')).to_contain_text('Defaults saved')
        page.reload();expect(page.locator('#default-clock-1')).to_have_value('Asia/Tokyo')
        page.screenshot(path=str(Path('work/defaults-571.png').resolve()),full_page=True)
        page.goto('https://testserver/user-settings#user-clocks')
        expect(page.locator('.personal-clock-row').first).to_contain_text('America/Los_Angeles')
        page.locator('#reset-clocks').click();expect(page.locator('.personal-clock-row').first).to_contain_text('Asia/Tokyo')
        expect(page.locator('.personal-clock-row .clock-drag svg').first).to_have_css('width','12px')
        expect(page.locator('.personal-clock-row').first).to_contain_text('UTC +09:00')
        page.locator('#clock-picker input.search').fill('London')
        page.locator('#clock-picker .menu .item[data-value="Europe/London"]').click()
        expect(page.locator('#clock-picker > .text .flag')).to_have_count(1)
        expect(page.locator('#clock-picker > .text .clock-picker-location')).to_contain_text('UTC +00:00')
        for theme in ['dark','light']:
            page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
            colours=page.locator('#clock-picker .menu').evaluate('(el)=>getComputedStyle(el).scrollbarColor')
            assert colours!='auto' and 'rgb(0, 0, 0)' not in colours
        assert not errors,errors
        browser.close()
