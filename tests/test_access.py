import base64, json, time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
import main, telemetry
from security import IdentityStore


@pytest.fixture
def system(tmp_path):
    m = telemetry.Monitor(lambda: {}, lambda: {}, tmp_path / "history.sqlite3")
    m.initialise()
    IdentityStore(m).initialise()
    now = int(time.time())
    payload = {
        "timestamp": now,
        "healthy": True,
        "hostname": "Test server",
        "metrics": {
            "cpu": 17,
            "ram": 23,
            "storage": 12,
            "storage_used": 9000000000,
            "temperature": 42,
            "uptime": 1200,
            "stratum": 1,
            "last_offset": 0.1,
            "rms_offset": 0.2,
            "ntp_rtt": 0.3,
        },
        "tracking": {"Stratum": "1", "Reference ID": "GPS", "Leap status": "Normal"},
        "services": [
            {
                "name": "chrony.service",
                "startup": "enabled",
                "status": "running",
                "cpu": 0.1,
                "ram": 1000,
            }
        ],
        "gps": {
            "fix": "3D fix",
            "used": 8,
            "visible": 12,
            "pps": True,
            "fix_details": {"mode": 3, "time": "2026-09-05T12:00:00Z"},
            "satellites": [{"svid": 1, "gnssid": 0, "used": True}],
            "pps_details": {"precision": -20},
        },
        "acquisition": {
            "selected": "GPS",
            "sources": [{"name": "GPS", "state": "*", "stratum": 0}],
        },
        "clients": [
            {
                "addr": "192.0.2.10",
                "hostname": "private-client",
                "Last": "5",
                "Drop": "0",
                "NTP": "20",
            }
        ],
        "checks": {"required_services": True},
    }
    with m.connect() as db:
        for offset in range(0, 3601, 30):
            p = {**payload, "timestamp": now - offset}
            db.execute(
                "INSERT INTO samples VALUES (?,?)", (now - offset, json.dumps(p))
            )
    with patch.object(main, "monitor", m), patch.object(
        main, "query_ntp_server", return_value={"timestamp": now, "round_trip_ms": 1}
    ), patch("access_api.system_information", return_value={
        "operating_system": "Debian GNU/Linux 13 (trixie, 64-bit)",
        "hardware": "Raspberry Pi 5 (2.4 GHz Quad-Core, 16 GB RAM, 256 GB NVMe)",
    }):
        yield m, TestClient(main.app, base_url="https://testserver")


def login(c, username="admin", password="admin"):
    return c.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": "https://testserver"},
    )


def basic(username="admin", password="admin"):
    return {
        "Authorization": "Basic "
        + base64.b64encode((username + ":" + password).encode()).decode()
    }


def change(c, path, body):
    if path == '/administration/users' and not body.get('id'):
        body = {'name': 'Test User', 'email': 'test@example.test', 'enabled': True, **body}
    return c.put(path, json=body, headers={"Origin": "https://testserver"})


def test_bootstrap_and_permission_boundaries(system):
    m, c = system
    assert c.get("/health").json() == {
        "status": "healthy",
        "details": "/health/details",
    }
    for url in [
        "/dashboard/status",
        "/server/status",
        "/time/clients/details",
        "/administration",
        "/docs",
        "/openapi.json",
    ]:
        assert c.get(url).status_code == 401
    for url in [
        "/api/history",
        "/api/dashboard",
        "/api/chrony/clients",
        "/dashboard/sources",
    ]:
        assert c.get(url).status_code == 404
    result = login(c)
    assert (
        result.status_code == 200
        and "HttpOnly" in result.headers["set-cookie"]
        and "Secure" in result.headers["set-cookie"]
    )
    assert (
        change(
            c,
            "/administration/users",
            {"username": "viewer", "password": "viewer-password", "roles": ["User"]},
        ).status_code
        == 200
    )
    assert login(c, "viewer", "viewer-password").status_code == 200
    assert c.get("/administration").status_code == 403
    status = c.get("/dashboard/status").json()
    assert "clients" not in status
    clients = c.get("/dashboard/clients").json()
    assert clients["summary"]["total_clients_seen"] == 1 and "clients" not in clients
    assert "private-client" not in c.get("/dashboard/history?metric=cpu").text
    assert (
        c.get(
            "/time/clients/details"
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/user/keys",
            json={"name": "test"},
            headers={"Origin": "https://testserver"},
        ).status_code
        == 403
    )
    assert (
        c.patch(
            "/dashboard/settings",
            json={"version": 1, "clocks": []},
            headers={"Origin": "https://testserver"},
        ).status_code
        == 403
    )


def test_roles_keys_and_per_user_clocks(system):
    m, c = system
    login(c)
    assert (
        change(
            c,
            "/administration/roles",
            {
                "name": "ClockAPI",
                "permissions": [
                    "dashboard.view",
                    "api.view",
                    "clocks.view",
                    "clocks.amend",
                    "clients.summary",
                ],
            },
        ).status_code
        == 200
    )
    assert (
        change(
            c,
            "/administration/users",
            {
                "username": "clock-user",
                "password": "clock-password",
                "roles": ["ClockAPI"],
            },
        ).status_code
        == 200
    )
    login(c, "clock-user", "clock-password")
    assert c.get("/dashboard/settings").json()["settings"]["clocks"] == []
    token = c.post(
        "/user/keys",
        json={"name": "integration"},
        headers={"Origin": "https://testserver"},
    ).json()["key"]
    headers = {"Authorization": "Bearer " + token}
    assert c.post("/clocks/add", headers=headers, json={"timezone_name": "UTC"}).json()[
        "success"
    ]
    assert c.get("/clocks", headers=headers).json()[0]["timezone_name"] == "UTC"
    assert c.get("/server/status", headers=headers).status_code == 403
    assert c.get("/time/clients", headers=headers).status_code == 200
    assert c.get("/time/clients/details", headers=headers).status_code == 403
    login(c)
    assert all(
        x["zone"] != "UTC"
        for x in c.get("/dashboard/settings").json()["settings"]["clocks"]
    )
    change(
        c,
        "/administration/roles",
        {"name": "ClockAPI", "permissions": ["dashboard.view", "clocks.view"]},
    )
    assert c.get("/clocks", headers=headers).status_code == 403
    with m.connect() as db:
        assert token not in db.execute("SELECT token FROM api_keys").fetchone()[0]
        assert (
            db.execute(
                "SELECT password FROM users WHERE username=?", ("admin",)
            ).fetchone()[0]
            != "admin"
        )


def test_api_contracts_history_and_csrf(system):
    m, c = system
    login(c)
    h = {}
    for url in [
        "/health/details",
        "/server/status",
        "/time/status",
        "/time/gps",
        "/time/satellites",
        "/time/pps",
        "/time/acquisition",
        "/time/sources",
        "/clocks",
        "/time/clients",
        "/time/clients/details",
    ]:
        assert c.get(url, headers=h).status_code == 200, url
    disk = c.get("/server/status", headers=h).json()["disk_used"]
    assert disk["bytes"] == 9000000000 and disk["gb"] == 9
    first = c.get("/server/status/history?parameter=cpu&limit=2", headers=h)
    assert len(first.json()) == 2
    assert first.json()[0]["value"] == 17 and "x-next-after" in first.headers
    url = f"/server/status/history?parameter=cpu&from={first.headers['x-history-from']}&to={first.headers['x-history-to']}&after={first.headers['x-next-after']}"
    assert c.get(url, headers=h).json()[0]["timestamp"] > first.json()[-1]["timestamp"]
    assert (
        c.get(
            "/server/status/history?parameter=cpu&from=2026-09-01T10:00:00Z&to=2026-09-01T11:00:00Z",
            headers=h,
        ).status_code
        == 200
    )
    assert c.get("/time/history?parameter=cpu", headers=h).status_code == 422
    assert (
        c.get("/time/history?parameter=stratum&from=9&to=8", headers=h).status_code
        == 422
    )
    login(c)
    assert (
        c.put(
            "/administration/roles", json={"name": "x", "permissions": []}
        ).status_code
        == 403
    )
    assert (
        change(
            c,
            "/administration/users",
            {
                "id": 1,
                "username": "admin",
                "enabled": False,
                "roles": ["Administrator"],
            },
        ).status_code
        == 422
    )
    config = c.get("/administration").json()["config"]
    config["services"] = ["chrony.service;touch /tmp/bad"]
    assert change(c, "/administration/config", config).status_code == 422
    assert c.get("/openapi.json").json()["paths"]["/server/status"]["get"]["security"]


def test_settings_keys_revocation_and_disabled_users(system):
    m, c = system
    login(c)
    key = c.post(
        "/user/keys", json={"name": "test"}, headers={"Origin": "https://testserver"}
    ).json()["key"]
    assert (
        c.get("/server/status", headers={"Authorization": "Bearer " + key}).status_code
        == 200
    )
    key_id = c.get("/user/keys").json()[0]["id"]
    assert (
        c.delete(
            "/user/keys/" + str(key_id), headers={"Origin": "https://testserver"}
        ).status_code
        == 200
    )
    assert (
        c.get("/server/status", headers={"Authorization": "Bearer " + key}).status_code
        == 401
    )
    cfg = c.get("/administration").json()["config"]
    cfg["services"] = ["chrony.service"]
    cfg["warning_seconds"] = 10
    cfg["critical_seconds"] = 20
    assert change(c, "/administration/config", cfg).status_code == 200
    assert m.get_settings()["settings"]["services"] == ["chrony.service"]
    old = c.get("/dashboard/settings").json()
    clocks = [{"zone": "UTC"}]
    assert (
        c.patch(
            "/dashboard/settings",
            json={"version": old["version"], "clocks": clocks},
            headers={"Origin": "https://testserver"},
        ).status_code
        == 200
    )
    assert (
        c.patch(
            "/dashboard/settings",
            json={"version": old["version"], "clocks": clocks},
            headers={"Origin": "https://testserver"},
        ).status_code
        == 409
    )


def test_migration_and_live_permission_removal(system):
    m, c = system
    with m.connect() as db:
        before = db.execute("SELECT COUNT(*),MIN(timestamp) FROM samples").fetchone()
        original = db.execute(
            "SELECT password,clocks FROM users WHERE username=?", ("admin",)
        ).fetchone()
    IdentityStore(m).initialise()
    with m.connect() as db:
        assert (
            db.execute("SELECT COUNT(*),MIN(timestamp) FROM samples").fetchone()
            == before
        )
        assert (
            db.execute(
                "SELECT password,clocks FROM users WHERE username=?", ("admin",)
            ).fetchone()
            == original
        )
        assert "clocks" not in json.loads(
            db.execute("SELECT payload FROM settings").fetchone()[0]
        )
    login(c)
    change(
        c,
        "/administration/roles",
        {"name": "Minimal", "permissions": ["dashboard.view", "clocks.view"]},
    )
    change(
        c,
        "/administration/users",
        {"username": "minimal", "password": "minimal-password", "roles": ["Minimal"]},
    )
    login(c, "minimal", "minimal-password")
    data = c.get("/dashboard/status").json()
    assert data["metrics"] == {} and "gps" not in data and "services" not in data
    assert c.get("/dashboard/history?metric=cpu").status_code == 403
    assert c.get("/dashboard/tracking").status_code == 403
    assert "round_trip_ms" not in c.get("/dashboard/time").json()


def test_password_change_and_attempt_limit(system):
    m, c = system
    login(c)
    token = c.post(
        "/user/keys",
        json={"name": "password-test"},
        headers={"Origin": "https://testserver"},
    ).json()["key"]
    result = c.post(
        "/user/password",
        json={"current_password": "admin", "new_password": "new-local-password"},
        headers={"Origin": "https://testserver"},
    )
    assert result.status_code == 200
    assert c.get("/auth/me").status_code == 401
    assert (
        c.get(
            "/server/status", headers={"Authorization": "Bearer " + token}
        ).status_code
        == 401
    )
    assert login(c, "admin", "new-local-password").status_code == 200
    for _ in range(10):
        assert login(c, "invalid", "invalid").status_code == 401
    assert login(c, "invalid", "invalid").status_code == 429


def test_session_probe_does_not_trigger_browser_basic_prompt(system):
    _,client=system
    assert "www-authenticate" not in client.get("/auth/me").headers
    assert "www-authenticate" not in client.get("/server/status").headers
    assert client.get("/server/status", headers=basic()).status_code == 401
