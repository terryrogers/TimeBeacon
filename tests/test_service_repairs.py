import subprocess
from unittest.mock import patch
from test_access import system, login, change

ORIGIN = {"Origin": "https://testserver"}
URL = "/administration/services/repair"
STOPPED = {"LoadState": "loaded", "ActiveState": "inactive"}
MISSING = {"LoadState": "not-found", "ActiveState": "inactive"}
ACTIVE = {"LoadState": "loaded", "ActiveState": "active"}


def configured(m, services):
    return m.save_settings(m.get_settings()["version"], {"services": services})[
        "version"
    ]


def test_repair_access_validation_and_stale_state(system):
    m, c = system
    assert c.get(URL, params={"unit": "chrony.service"}).status_code == 401
    login(c)
    change(
        c,
        "/administration/users",
        dict(username="viewer", password="viewer-password", roles=["User"]),
    )
    version = configured(m, ["chrony.service", "missing.service"])
    body = dict(unit="chrony.service", action="start", config_version=version)
    with patch("service_repairs.inspect_service", return_value=STOPPED), patch(
        "service_repairs.subprocess.run"
    ) as run:
        assert c.post(URL, json=body).status_code == 403
        assert (
            c.post(
                URL, json={**body, "unit": "bad.service;id"}, headers=ORIGIN
            ).status_code
            == 422
        )
        assert c.get(URL, params={"unit": "other.service"}).status_code == 404
        assert (
            c.post(URL, json={**body, "config_version": 0}, headers=ORIGIN).status_code
            == 409
        )
        login(c, "viewer", "viewer-password")
        assert c.get(URL, params={"unit": "chrony.service"}).status_code == 403
        assert c.post(URL, json=body, headers=ORIGIN).status_code == 403
        run.assert_not_called()


def test_start_service_audit_cooldown_and_already_active(system):
    m, c = system
    login(c)
    version = configured(m, ["chrony.service"])
    body = dict(unit="chrony.service", action="start", config_version=version)
    with patch("service_repairs.inspect_service", side_effect=[STOPPED, ACTIVE]), patch(
        "service_repairs.subprocess.run"
    ) as run:
        assert c.post(URL, json=body, headers=ORIGIN).json()["success"]
        assert run.call_args.args[0] == [
            "sudo",
            "-n",
            "/usr/bin/systemctl",
            "start",
            "chrony.service",
        ]
    with m.connect() as db:
        assert db.execute(
            "SELECT unit,action,result FROM service_actions"
        ).fetchone() == ("chrony.service", "start", "started")
    with patch("service_repairs.inspect_service", return_value=STOPPED):
        assert c.post(URL, json=body, headers=ORIGIN).status_code == 429
    with patch("service_repairs.inspect_service", return_value=ACTIVE), patch(
        "service_repairs.subprocess.run"
    ) as run:
        assert c.get(URL, params={"unit": "chrony.service"}).json()["action"] is None
        assert c.post(URL, json=body, headers=ORIGIN).status_code == 409
        run.assert_not_called()


def test_missing_service_requires_explicit_monitoring_removal(system):
    m, c = system
    login(c)
    version = configured(m, ["chrony.service", "missing.service"])
    body = dict(unit="missing.service", action="remove_check", config_version=version)
    with patch("service_repairs.inspect_service", return_value=MISSING), patch(
        "service_repairs.subprocess.run"
    ) as run:
        proposed = c.get(URL, params={"unit": "missing.service"}).json()
        assert proposed["label"] == "Remove health check"
        assert "does not install" in proposed["message"]
        assert (
            c.post(URL, json={**body, "action": "start"}, headers=ORIGIN).status_code
            == 409
        )
        assert c.post(URL, json=body, headers=ORIGIN).json()["success"]
        assert m.get_settings()["settings"]["services"] == ["chrony.service"]
        assert c.post(URL, json=body, headers=ORIGIN).status_code == 404
        version = configured(m, ["last.service"])
        assert (
            c.post(
                URL,
                json={**body, "unit": "last.service", "config_version": version},
                headers=ORIGIN,
            ).status_code
            == 422
        )
        run.assert_not_called()


def test_service_start_failure_is_not_reported_as_success(system):
    m, c = system
    login(c)
    version = configured(m, ["chrony.service"])
    with patch("service_repairs.inspect_service", return_value=STOPPED), patch(
        "service_repairs.subprocess.run",
        side_effect=subprocess.CalledProcessError(
            1, "systemctl", stderr="private diagnostic"
        ),
    ):
        response = c.post(
            URL,
            json=dict(unit="chrony.service", action="start", config_version=version),
            headers=ORIGIN,
        )
        assert response.status_code == 503 and "private diagnostic" not in response.text
    with m.connect() as db:
        assert (
            db.execute("SELECT result FROM service_actions").fetchone()[0] == "failed"
        )
