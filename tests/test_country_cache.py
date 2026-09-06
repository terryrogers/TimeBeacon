from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_access import system,login,browser_headers


def test_country_catalogue_authentication_and_scope(system):
    _,client=system
    assert client.get('/user/locations/country?code=gb').status_code==401
    login(client)
    assert client.get('/user/locations/country?code=invalid').status_code==422
    result=client.get('/user/locations/country?code=GB').json()
    assert result['country_code']=='gb'
    assert len(result['places'])>1000
    assert all(place['country_code']=='gb' for place in result['places'])
    assert any(place['city']=='Woking' for place in result['places'])
    assert all(set(place)=={'id','city','country_code','country','region','latitude','longitude','timezone','search','city_search'} for place in result['places'])
    japan=client.get('/user/locations/country?code=jp').json()['places']
    assert all(place['country_code']=='jp' for place in japan)
    assert any(place['city']=='Tokyo' for place in japan)


def test_cached_country_search_and_visible_loaders(system):
    _,client=system
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1100})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        held=[];delay={'path':None};country_calls=[]
        def fulfill(route):
            req=route.request;client.cookies.clear()
            response=client.request(req.method,req.url,headers=req.headers,content=req.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        def route(request):
            if '/user/locations/country?' in request.request.url:country_calls.append(request.request.url)
            if delay['path'] and delay['path'] in request.request.url:held.append(request)
            else:fulfill(request)
        page.route('**/*',route);page.route('https://gravatar.com/**',lambda r:r.abort())
        page.goto('https://testserver/login')
        page.locator('#login-form [name=username]').fill('admin');page.locator('#login-form [name=password]').fill('admin');page.locator('#login-form button').click()
        expect(page.locator('#system-cpu')).to_be_visible()
        delay['path']='/user/locations/country?'
        page.goto('https://testserver/user-settings')
        expect(page.locator('#location-search-loading')).to_be_visible()
        expect(page.locator('#location-picker')).to_have_class(__import__('re').compile('loading'))
        delay['path']=None;fulfill(held.pop())
        expect(page.locator('#location-search-loading')).to_be_hidden()
        assert len(country_calls)==1 and 'code=gb' in country_calls[0]
        search=page.get_by_role('textbox',name='Search Cities and Towns')
        search.click()
        expect(page.locator('#location-picker .menu .item').filter(has_text='London').first).to_be_visible()

        delay['path']='/user/locations/search?'
        with page.expect_request('**/user/locations/search?*'):
            search.fill('Woking')
        expect(page.locator('#location-search-loading')).to_be_visible()
        expect(page.locator('#location-search-loading')).to_contain_text('Searching Cities And Towns')
        expect(page.locator('#location-picker .menu .item').filter(has_text='Woking').first).to_be_visible()
        # Cached country matches are available while the worldwide request is held.
        for theme in ['light','dark']:
            page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
            page.locator('#daylight-display').screenshot(path=str(Path(f'work/country-loader-593-{theme}.png').resolve()))
        held.pop().fulfill(status=500,content_type='application/json',body='{"detail":"Unavailable"}')
        expect(page.locator('#location-feedback')).to_contain_text('Cached country results')
        expect(page.locator('#location-search-loading')).to_be_hidden()
        delay['path']=None
        page.reload();expect(page.locator('#get-location')).to_be_enabled()
        search.click();expect(page.locator('#location-picker .menu .item').filter(has_text='London').first).to_be_visible()
        assert len(country_calls)==1

        search.fill('Tokyo Japan')
        tokyo=page.locator('#location-picker .menu .item').filter(has_text='Tokyo').first
        expect(tokyo).to_be_visible();tokyo.click()
        expect(page.locator('#location-label')).to_contain_text('Tokyo')
        expect(page.locator('#location-search-loading')).to_be_hidden()
        assert any('code=jp' in url for url in country_calls)
        search.click()
        expect(page.locator('#location-picker .menu .item').first.locator('i.jp.flag')).to_have_count(1)
        page.locator('#clear-location').click()
        expect(page.locator('#manual-theme')).to_be_visible()
        expect(page.locator('#location-picker .menu .item')).to_have_count(0)

        delay['path']='/administration'
        page.goto('https://testserver/admin/users')
        expect(page.locator('#user-directory #users-loading')).to_be_visible()
        expect(page.locator('#users-loading .ui.loader')).to_be_visible()
        page.locator('#user-directory').screenshot(path=str(Path('work/users-loader-593.png').resolve()))
        held.pop().fulfill(status=500,content_type='application/json',body='{"detail":"Users unavailable"}')
        expect(page.locator('#users-loading')).to_be_hidden()
        expect(page.locator('#page-feedback')).to_contain_text('Users unavailable')
        assert not errors,errors
        browser.close()
