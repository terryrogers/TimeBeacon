from unittest.mock import patch
from types import SimpleNamespace
from test_access import system, login, change
from client_settings import system_services

ORIGIN = {"Origin": "https://testserver"}


def test_new_account_required_fields_single_role_disabled_default(system):
    m, c = system
    login(c)
    body = dict(
        name="New Person",
        username="new-person",
        email="person@example.test",
        password="test-password",
        roles=["User"],
    )
    for missing in ["name", "username", "email"]:
        invalid = {key: value for key, value in body.items() if key != missing}
        assert (
            c.put("/administration/users", json=invalid, headers=ORIGIN).status_code
            == 422
        )
    assert (
        c.put(
            "/administration/users", json={**body, "name": "   "}, headers=ORIGIN
        ).status_code
        == 422
    )
    assert (
        c.put(
            "/administration/users",
            json={**body, "roles": ["User", "Administrator"]},
            headers=ORIGIN,
        ).status_code
        == 422
    )
    assert c.put("/administration/users", json=body, headers=ORIGIN).status_code == 200
    user = next(
        u
        for u in c.get("/administration").json()["users"]
        if u["username"] == "new-person"
    )
    assert not user["enabled"] and user["roles"] == ["User"]
    assert login(c, "new-person", "test-password").status_code == 401


def test_service_inventory_combines_unit_files_and_transient_services(system):
    m, c = system
    with patch(
        "client_settings.system_services", return_value=["a.service", "chrony.service"]
    ) as inventory:
        assert c.get("/administration/services").status_code == 401
        inventory.assert_not_called()
        login(c)
        response = c.get("/administration/services")
        assert response.status_code == 200 and response.json()["services"] == [
            "a.service",
            "chrony.service",
        ]
        assert "chrony.service" in response.json()["monitored"]
        change(
            c,
            "/administration/users",
            dict(username="viewer", password="test-password", roles=["User"]),
        )
        login(c, "viewer", "test-password")
        assert c.get("/administration/services").status_code == 403
    with patch(
        "client_settings.subprocess.run",
        side_effect=[
            SimpleNamespace(
                stdout="a.service enabled enabled\ntemplate@.service disabled enabled\n"
            ),
            SimpleNamespace(
                stdout="a.service loaded active running\ntransient.service loaded inactive dead\n"
            ),
        ],
    ) as command:
        assert system_services(details=True) == [
            {'name':'a.service','startup':'enabled','status':'active / running'},
            {'name':'template@.service','startup':'disabled','status':'inactive'},
            {'name':'transient.service','startup':'transient','status':'inactive / dead'},
        ]
        assert command.call_count == 2
