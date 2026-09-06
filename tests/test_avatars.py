import base64
import io
from PIL import Image, PngImagePlugin
from test_access import system, login, change

ORIGIN = {'Origin': 'https://testserver'}

def photo_bytes():
    output = io.BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('private-metadata', 'synthetic-test')
    Image.new('RGB', (800, 400), '#3399aa').save(output, format='PNG', pnginfo=metadata)
    return output.getvalue()

def test_photo_upload_preferences_preservation_and_access(system):
    m, c = system
    body = {'image': base64.b64encode(photo_bytes()).decode()}
    assert c.post('/user/photo', json=body, headers=ORIGIN).status_code == 401
    login(c)
    assert c.post('/user/photo', json=body).status_code == 403
    initial = c.get('/user/profile').json()
    assert initial['gravatar_enabled'] and not initial['custom_photo']
    response = c.post('/user/photo', json=body, headers=ORIGIN)
    assert response.status_code == 200
    saved = response.json()
    assert saved['custom_photo'] and saved['avatar'].startswith('/user/avatar/')
    downloaded = c.get(saved['avatar'])
    assert 'no-store' in downloaded.headers['cache-control']
    image = Image.open(io.BytesIO(downloaded.content))
    assert image.size == (512, 256) and image.format == 'PNG'
    assert 'private-metadata' not in image.info
    updated = change(c, '/user/profile', {'name': 'Updated Person', 'email': 'person@example.test'}).json()
    assert updated['avatar'] == saved['avatar']
    assert c.get(saved['avatar']).content == downloaded.content
    disabled = c.patch('/user/photo', json={'gravatar_enabled': False}, headers=ORIGIN).json()
    assert disabled['custom_photo'] and not disabled['gravatar_enabled']
    change(c, '/administration/users', {'username': 'viewer', 'password': 'test-password', 'roles': ['User']})
    login(c, 'viewer', 'test-password')
    assert c.get(saved['avatar']).status_code == 403
    login(c)
    cleared = c.patch('/user/photo', json={'gravatar_enabled': False, 'clear': True}, headers=ORIGIN).json()
    assert cleared['avatar'] == '/static/avatar-default.svg' and not cleared['custom_photo']
    assert c.get(saved['avatar']).status_code == 404
    restored = c.patch('/user/photo', json={'gravatar_enabled': True}, headers=ORIGIN).json()
    assert restored['avatar'].startswith('https://gravatar.com/')

def test_invalid_photo_does_not_change_existing_photo(system):
    m, c = system
    login(c)
    before = c.get('/user/profile').json()
    for encoded in ['not-base64!', base64.b64encode(b'<svg></svg>').decode(), base64.b64encode(b'a' * (4 * 1024 * 1024 + 1)).decode()]:
        assert c.post('/user/photo', json={'image': encoded}, headers=ORIGIN).status_code == 422
        assert c.get('/user/profile').json() == before
    output = io.BytesIO()
    Image.new('1', (4001, 4001)).save(output, format='PNG')
    assert c.post('/user/photo', json={'image': base64.b64encode(output.getvalue()).decode()}, headers=ORIGIN).status_code == 422

def test_admin_photo_access_targeting_and_user_save_preservation(system):
    m,c=system
    body={'image':base64.b64encode(photo_bytes()).decode()}
    assert c.post('/administration/users/1/photo',json=body,headers=ORIGIN).status_code==401
    login(c)
    original=c.get('/user/profile').json()
    change(c,'/administration/users',{'username':'viewer','password':'test-password','roles':['User'],'photo':'https://example.test/photo.png'})
    target=next(u for u in c.get('/administration').json()['users'] if u['username']=='viewer')
    url=f"/administration/users/{target['id']}/photo"
    assert c.post(url,json=body).status_code==403
    assert c.patch(url,json={'gravatar_enabled':False}).status_code==403
    # Saving the profile without the removed photo field preserves legacy image URLs.
    edit={k:target[k] for k in ['id','name','username','email','roles','enabled']}
    assert change(c,'/administration/users',edit).status_code==200
    assert next(u for u in c.get('/administration').json()['users'] if u['id']==target['id'])['photo']==target['photo']
    uploaded=c.post(url,json=body,headers=ORIGIN)
    assert uploaded.status_code==200 and uploaded.json()['custom_photo']
    assert uploaded.json()['avatar'].startswith(f"/user/avatar/{target['id']}?")
    c.patch(url,json={'gravatar_enabled':False},headers=ORIGIN).raise_for_status()
    edit['name']='Updated Viewer'
    assert change(c,'/administration/users',edit).status_code==200
    assert c.get('/user/profile').json()==original
    assert c.post('/administration/users/9999/photo',json=body,headers=ORIGIN).status_code==404
    assert c.patch('/administration/users/9999/photo',json={'gravatar_enabled':False},headers=ORIGIN).status_code==404
    login(c,'viewer','test-password')
    own=c.get('/user/profile').json()
    assert own['custom_photo'] and not own['gravatar_enabled'] and own['name']=='Updated Viewer'
    for target_url in [url,'/administration/users/1/photo']:
        assert c.post(target_url,json=body,headers=ORIGIN).status_code==403
        assert c.patch(target_url,json={'gravatar_enabled':True,'clear':True},headers=ORIGIN).status_code==403
    login(c)
    cleared=c.patch(url,json={'gravatar_enabled':True,'clear':True},headers=ORIGIN).json()
    assert not cleared['custom_photo'] and cleared['avatar'].startswith('https://gravatar.com/')
