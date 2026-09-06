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
            route.fulfill(status=response.status_code,headers=dict(response.headers),body=response.content)
        page.route('**/*',route)
        page.route('**/dashboard/clocks/image?*',lambda r:r.fulfill(json={'image':None}))
        page.route('https://gravatar.com/**',lambda r:r.abort())
        page.goto('https://testserver/')
        page.locator('[name=username]').fill('admin');page.locator('[name=password]').fill('admin');page.locator('#login-form button').click()
        expect(page.locator('#world-panel')).to_be_visible()
        page.locator('#world-panel>summary').click()
        page.locator('#reset-clocks').click()
        expect(page.locator('#clock-feedback')).to_contain_text('reset to system defaults')
        expect(page.locator('.clock-card')).to_have_count(6)
        expect(page.locator('.clock-card').first).to_contain_text('Los Angeles')
        page.screenshot(path=str(Path('work/clocks-570.png').resolve()),full_page=True)
        page.get_by_role('button',name='Reorder Los Angeles clock',exact=True).press('ArrowRight')
        expect(page.locator('.clock-card').first).to_contain_text('New York')
        # Real pointer drag on the dashboard, saving the new order.
        source=page.get_by_role('button',name='Reorder New York clock',exact=True).bounding_box()
        target=page.locator('.clock-card').nth(2).bounding_box()
        page.mouse.move(source['x']+14,source['y']+14);page.mouse.down();page.mouse.move(target['x']+60,target['y']+65,steps=12);page.mouse.up()
        expect(page.locator('.clock-card').nth(2)).to_contain_text('New York')
        page.get_by_role('button',name='Remove Dubai clock',exact=True).click()
        expect(page.locator('.clock-card')).to_have_count(5)
        page.reload();page.locator('#world-panel>summary').click()
        expect(page.locator('.clock-card')).to_have_count(5)
        expect(page.locator('.clock-card').nth(2)).to_contain_text('New York')
        page.goto('https://testserver/user-settings#user-clocks')
        expect(page.locator('.personal-clock-row')).to_have_count(5)
        source=page.locator('.clock-drag').first.bounding_box();target=page.locator('.personal-clock-row').nth(2).bounding_box()
        page.mouse.move(source['x']+8,source['y']+8);page.mouse.down();page.mouse.move(target['x']+80,target['y']+20,steps=12);page.mouse.up()
        expect(page.locator('.personal-clock-row').nth(2)).to_contain_text('America/Los_Angeles')
        page.locator('#reset-clocks').click()
        expect(page.locator('.personal-clock-row')).to_have_count(6)
        page.goto('https://testserver/admin/defaults')
        expect(page.locator('#page-title')).to_have_text('Defaults')
        expect(page.locator('#default-clock-1')).to_have_value('America/Los_Angeles')
        page.locator('#default-picker-1 input.search').fill('Tokyo')
        page.locator('#default-picker-1 .menu .item[data-value="Asia/Tokyo"]').click()
        page.get_by_role('button',name='Save Defaults',exact=True).click()
        expect(page.locator('#page-feedback')).to_contain_text('Defaults saved')
        page.reload();expect(page.locator('#default-clock-1')).to_have_value('Asia/Tokyo')
        page.screenshot(path=str(Path('work/defaults-570.png').resolve()),full_page=True)
        page.goto('https://testserver/user-settings#user-clocks')
        expect(page.locator('.personal-clock-row').first).to_contain_text('America/Los_Angeles')
        page.locator('#reset-clocks').click();expect(page.locator('.personal-clock-row').first).to_contain_text('Asia/Tokyo')
        for theme in ['dark','light']:
            page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
            colours=page.locator('#clock-picker .menu').evaluate('(el)=>getComputedStyle(el).scrollbarColor')
            assert colours!='auto' and 'rgb(0, 0, 0)' not in colours
        assert not errors,errors
        browser.close()
