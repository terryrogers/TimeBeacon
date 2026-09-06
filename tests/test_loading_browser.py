from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_access import system, browser_headers


def test_slow_requests_dropdown_and_loader_cleanup(system):
    _, client = system
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        delayed={'path':None,'routes':[]}
        def fulfill(route):
            req=route.request;client.cookies.clear()
            response=client.request(req.method,req.url,headers=req.headers,content=req.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        def route(request):
            if delayed['path'] and delayed['path'] in request.request.url:
                delayed['routes'].append(request)
            else:fulfill(request)
        page.route('**/*',route)
        page.route('https://gravatar.com/**',lambda r:r.abort())
        page.goto('https://testserver/login')
        page.locator('#login-form [name=username]').fill('admin')
        page.locator('#login-form [name=password]').fill('admin')
        delayed['path']='/auth/login'
        page.locator('#login-form button').click()
        expect(page.locator('.signin-card .loading-status')).to_be_visible()
        expect(page.locator('#system-cpu')).to_have_count(0)
        delayed['path']=None;fulfill(delayed['routes'].pop())
        expect(page.locator('#system-cpu')).to_have_text('17.0 %',timeout=15000)

        delayed['path']='/administration'
        with page.expect_request('**/administration'):
            page.goto('https://testserver/admin/users')
        expect(page.locator('#user-directory #users-loading')).to_be_visible()
        delayed['path']=None;fulfill(delayed['routes'].pop())
        expect(page.locator('#new-user')).to_be_enabled()
        expect(page.locator('.loading-status:not([hidden])')).to_have_count(0)
        page.locator('#new-user').click()
        expect(page.locator('#onboarding-method')).to_have_value('invite')
        for theme in ['light','dark']:
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
                select=page.locator('#onboarding-method')
                metrics=select.evaluate('e=>{const s=getComputedStyle(e);return {height:e.clientHeight,line:parseFloat(s.lineHeight)||parseFloat(s.fontSize)*1.5,top:parseFloat(s.paddingTop),bottom:parseFloat(s.paddingBottom)}}')
                assert metrics['height']>=metrics['line']+metrics['top']+metrics['bottom']
                assert metrics['top']==metrics['bottom']
                select.screenshot(path=str(Path(f'work/dropdown-594-{theme}-{width}.png').resolve()))
        page.set_viewport_size({'width':1440,'height':1000})
        page.get_by_role('button',name='Close User Details').click()

        # Concurrent operations must keep one indicator until the last completes.
        page.evaluate("""()=>{window.finishA=beginLoading({target:document.querySelector('.page-content'),label:'Loading Users…'});window.finishB=beginLoading({target:document.querySelector('.page-content')});}""")
        expect(page.locator('.page-content>.loading-status')).to_have_count(1)
        expect(page.locator('.page-content>.loading-status')).to_be_visible()
        page.evaluate('finishA()')
        expect(page.locator('.page-content>.loading-status')).to_be_visible()
        page.evaluate('finishB()')
        expect(page.locator('.loading-status:not([hidden])')).to_have_count(0)
        expect(page.locator('.page-content')).not_to_have_attribute('aria-busy','true')

        # An aborted network request must also remove its indicator.
        delayed['path']='/slow-test'
        page.evaluate("""()=>{requestData('/slow-test',{signal:AbortSignal.timeout(1400)},{target:document.querySelector('.page-content')}).catch(()=>{});}""")
        expect(page.locator('.page-content>.loading-status')).to_be_visible()
        expect(page.locator('.page-content>.loading-status')).to_have_count(0)
        for request in delayed['routes']:request.abort()
        delayed['routes'].clear();delayed['path']=None

        page.goto('https://testserver/')
        expect(page.locator('#system-cpu')).to_have_text('17.0 %',timeout=15000)
        delayed['path']='/dashboard/history'
        page.locator('[data-history=cpu]').click()
        expect(page.locator('#history-dialog .loading-status')).to_be_visible()
        expect(page.locator('#history-dialog .window-close')).to_be_enabled()
        expect(page.locator('#history-dialog .window-statusbar')).to_be_visible()
        expect(page.locator('#history-dialog .loading-status')).to_have_class(__import__('re').compile('ui active inverted dimmer'))
        overlay=page.locator('#history-dialog .loading-status').bounding_box()
        header=page.locator('#history-dialog .window-titlebar').bounding_box()
        footer=page.locator('#history-dialog .window-statusbar').bounding_box()
        assert overlay['y']>=header['y']+header['height']-1
        assert overlay['y']+overlay['height']<=footer['y']+1
        page.locator('#history-dialog').screenshot(path=str(Path('work/history-loader-594.png').resolve()))
        delayed['routes'].pop().fulfill(status=500,content_type='application/json',body='{"detail":"Unavailable"}')
        expect(page.locator('#history-message')).to_contain_text('History unavailable')
        expect(page.locator('#history-dialog .loading-status')).to_have_count(0)
        page.locator('#history-dialog .window-close').click()
        assert not errors,errors
        browser.close()
