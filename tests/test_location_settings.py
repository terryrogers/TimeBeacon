import json
from unittest.mock import patch
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_access import system, login, browser_headers, change
from security import IdentityStore

ORIGIN={'Origin':'https://testserver'}


def test_personal_search_selection_clear_and_manual_theme(system):
    monitor,client=system
    assert client.get('/user/locations/search?q=London').status_code==401
    login(client)
    assert client.get('/user/locations/search?q=x').status_code==422
    hits=client.get('/user/locations/search?q=London United Kingdom').json()['places']
    london=next(place for place in hits if place['city']=='London')
    assert london['country_code']=='gb' and london['timezone']=='Europe/London'
    assert client.get('/user/locations/search?q=São Paulo').json()['places'][0]['country_code']=='br'
    assert client.get('/user/locations/search?q=Woking').json()['places']
    assert client.put('/user/location',json={'id':london['id']},headers={'Origin':'https://evil.test'}).status_code==403
    assert client.put('/user/location',json={'id':-1},headers=ORIGIN).status_code==404
    tokyo=client.get('/user/locations/search?q=Tokyo Japan').json()['places'][0]
    assert client.put('/user/location',json={'id':tokyo['id']},headers=ORIGIN).status_code==200
    profile=client.get('/user/profile').json()
    assert profile['reference_clock']['timezone']=='Asia/Tokyo'
    assert profile['reference_clock']['utc']=='UTC +09:00'
    assert client.get('/dashboard/solar').json()['automatic'] is True
    assert client.put('/user/theme',json={'theme':'dark'},headers=ORIGIN).status_code==409
    assert client.delete('/user/location',headers=ORIGIN).status_code==200
    assert client.get('/user/profile').json()['reference_clock'] is None
    for theme in ['dark','light']:
        assert client.put('/user/theme',json={'theme':theme},headers=ORIGIN).status_code==200
        solar=client.get('/dashboard/solar').json()
        assert solar['theme']==theme and solar['automatic'] is False
    IdentityStore(monitor).initialise()
    assert client.get('/user/profile').json()['location']['latitude'] is None
    assert client.put('/user/theme',json={'theme':'invalid'},headers=ORIGIN).status_code==422
    change(client,'/administration/users',dict(username='viewer',password='viewer-password',roles=['User']))
    login(client,'viewer','viewer-password')
    assert client.get('/user/profile').json()['location']['location']=='London'


def test_location_browser_search_reference_and_themes(system):
    _,client=system
    with sync_playwright() as p,patch('access_api.city_image',return_value=None):
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1100})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        def route(route):
            req=route.request;client.cookies.clear()
            response=client.request(req.method,req.url,headers=req.headers,content=req.post_data_buffer,follow_redirects=True)
            route.fulfill(status=response.status_code,headers=browser_headers(response),body=response.content)
        page.route('**/*',route);page.route('https://gravatar.com/**',lambda route:route.abort())
        page.goto('https://testserver/login');page.locator('#login-form [name=username]').fill('admin');page.locator('#login-form [name=password]').fill('admin');page.locator('#login-form button').click()
        expect(page.locator('#system-cpu')).to_be_visible();page.goto('https://testserver/user-settings')
        expect(page.locator('#get-location')).to_be_enabled()
        expect(page.locator('#manual-theme')).to_be_hidden()
        search=page.get_by_role('textbox',name='Search Cities and Towns');search.fill('Tokyo Japan')
        result=page.locator('#location-picker .menu .item').filter(has_text='Asia/Tokyo').first
        expect(result).to_be_visible();expect(result.locator('i.jp.flag')).to_have_count(1)
        page.locator('#daylight-display').screenshot(path=str(Path('work/location-picker-580.png').resolve()))
        result.click();expect(page.locator('#location-label')).to_contain_text('Tokyo')
        expect(page.locator('#reference-clock')).to_contain_text('Asia/Tokyo (UTC +09:00)')
        page.reload();expect(page.locator('#location-label')).to_contain_text('Tokyo');expect(page.locator('#reference-clock')).to_be_visible()
        page.locator('#clear-location').click();expect(page.locator('#manual-theme')).to_be_visible();expect(page.locator('#reference-clock')).to_be_hidden()
        page.locator('#manual-dark').check();expect(page.locator('html')).to_have_attribute('data-theme','dark')
        page.reload();expect(page.locator('#manual-dark')).to_be_checked()
        page.locator('#daylight-display').screenshot(path=str(Path('work/location-manual-580.png').resolve()))
        page.locator('#manual-dark').uncheck();expect(page.locator('html')).to_have_attribute('data-theme','light')
        page.goto('https://testserver/');expect(page.locator('#solar-summary')).to_have_text('Manual Theme · Light')
        assert not errors,errors
        browser.close()
