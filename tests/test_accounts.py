import io
import json
import time
from unittest.mock import patch
import pyotp
from test_access import system, login, change, basic
from security import IdentityStore

ORIGIN = {"Origin": "https://testserver"}


def test_private_pages_and_unsupported_auth(system):
    _, c = system
    for url in (
        "/",
        "/admin",
        "/admin/users",
        "/admin/roles",
        "/admin/services",
        "/user-settings",
    ):
        response = c.get(url, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/login"
        assert "system-cpu" not in response.text
    assert "system-cpu" not in c.get("/login").text
    login(c)
    assert c.get("/server/status", headers=basic()).status_code == 401
    assert (
        c.put(
            "/administration/roles",
            headers={"Authorization": "Unknown invalid"},
            json={"name": "bad", "permissions": []},
        ).status_code
        == 401
    )
    change(
        c,
        "/administration/users",
        dict(username="viewer", password="viewer-password", roles=["User"]),
    )
    login(c, "viewer", "viewer-password")
    assert c.get("/admin/users").status_code == 403
    assert c.get("/user-settings").status_code == 200


def test_profiles_personal_location_and_migration(system):
    m, c = system
    login(c)
    initial = c.get("/user/profile").json()
    assert initial["location"]["location"] == "London"
    response = c.put(
        "/user/profile",
        json={"name": "Terry Rogers", "email": "TERRY@example.com", "photo": ""},
        headers=ORIGIN,
    )
    assert (
        response.status_code == 200 and response.json()["email"] == "terry@example.com"
    )
    assert response.json()["avatar"].startswith("https://gravatar.com/avatar/")
    assert (
        c.put(
            "/user/profile", json={"photo": "javascript:alert(1)"}, headers=ORIGIN
        ).status_code
        == 422
    )
    change(
        c,
        "/administration/users",
        dict(
            username="viewer",
            name="Other Person",
            email="viewer@example.com",
            password="viewer-password",
            roles=["User"],
        ),
    )
    with patch(
        "account_api.urllib.request.urlopen",
        return_value=io.BytesIO(b'{"address":{"city":"Manchester"}}'),
    ) as geocoder:
        response = c.post(
            "/user/location",
            json={"latitude": 53.4808, "longitude": -2.2426},
            headers=ORIGIN,
        )
        assert (
            response.status_code == 200 and response.json()["location"] == "Manchester"
        )
        assert (
            c.post(
                "/user/location",
                json={"latitude": 53.4808, "longitude": -2.2426},
                headers=ORIGIN,
            ).status_code
            == 200
        )
        assert geocoder.call_count == 1
    assert c.get("/dashboard/settings").json()["settings"]["location"] == "Manchester"
    assert m.get_settings()["settings"]["location"] == "London"
    IdentityStore(m).initialise()
    assert c.get("/user/profile").json()["location"]["location"] == "Manchester"
    login(c, "viewer", "viewer-password")
    assert c.get("/user/profile").json()["location"]["location"] == "London"
    assert c.get("/user/profile").json()["name"] == "Other Person"


def test_two_factor_enrollment_login_replay_recovery_and_disable(system):
    m, c = system
    login(c)
    assert (
        c.post(
            "/user/2fa/register", json={"password": "wrong"}, headers=ORIGIN
        ).status_code
        == 401
    )
    enrollment = c.post(
        "/user/2fa/register", json={"password": "admin"}, headers=ORIGIN
    ).json()
    secret = enrollment["secret"]
    assert enrollment["qr"].startswith("data:image/svg+xml;base64,")
    with m.connect() as db:
        assert (
            secret
            not in db.execute("SELECT totp_pending FROM users WHERE id=1").fetchone()[0]
        )
    assert c.get("/user/profile").json()["two_factor"] is False
    assert (
        c.post("/user/2fa/confirm", json={"code": "000000"}, headers=ORIGIN).status_code
        == 422
    )
    code = pyotp.TOTP(secret).now()
    response = c.post("/user/2fa/confirm", json={"code": code}, headers=ORIGIN)
    assert response.status_code == 200
    recovery = response.json()["recovery_codes"]
    assert c.get("/user/profile").json()["two_factor"] is True
    c.cookies.clear()
    assert login(c).json()['stage'] == 'factor'
    assert c.get('/auth/me').status_code == 401
    assert c.post('/auth/second-factor', json={'code': code}, headers=ORIGIN).status_code == 401
    assert c.post('/auth/second-factor', json={'code': recovery[0], 'recovery': True}, headers=ORIGIN).status_code == 200
    assert login(c).json()['stage'] == 'factor'
    assert c.post('/auth/second-factor', json={'code': recovery[0], 'recovery': True}, headers=ORIGIN).status_code == 401
    next_time = (int(time.time()) // 30 + 2) * 30
    with patch('time.time', return_value=next_time):
        assert c.post('/auth/second-factor', json={'code': pyotp.TOTP(secret).at(next_time)}, headers=ORIGIN).status_code == 200
        assert login(c).json()['stage'] == 'factor'
        assert c.post('/auth/second-factor', json={'code': pyotp.TOTP(secret).at(next_time)}, headers=ORIGIN).status_code == 401
        assert c.post('/auth/second-factor', json={'code': recovery[2], 'recovery': True}, headers=ORIGIN).status_code == 200
    assert (
        c.post(
            "/user/2fa/disable",
            json={"password": "admin", "code": recovery[1]},
            headers=ORIGIN,
        ).status_code
        == 200
    )
    assert c.get("/user/profile").json()["two_factor"] is False
    c.cookies.clear()
    assert login(c).status_code == 200


def test_two_factor_failed_attempts_are_throttled(system):
    m, c = system
    login(c)
    result = c.post(
        "/user/2fa/register", json={"password": "admin"}, headers=ORIGIN
    ).json()
    assert (
        c.post(
            "/user/2fa/confirm",
            json={"code": pyotp.TOTP(result["secret"]).now()},
            headers=ORIGIN,
        ).status_code
        == 200
    )
    c.cookies.clear()
    assert login(c).json()['stage'] == 'factor'
    for _ in range(10):
        assert c.post('/auth/second-factor', json={'code': 'invalid'}, headers=ORIGIN).status_code == 401
    assert c.post('/auth/second-factor', json={'code': 'invalid'}, headers=ORIGIN).status_code == 429
