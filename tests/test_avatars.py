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
