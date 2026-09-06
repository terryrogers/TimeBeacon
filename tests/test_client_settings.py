import copy
from test_access import system, login, change


def test_clients_and_services_save_independently(system):
    m, c = system
    login(c)
    settings = c.get("/administration").json()["config"]
    body = {
        key: settings[key]
        for key in [
            "warning_seconds",
            "critical_seconds",
            "warning_drops",
            "critical_drops",
            "client_colours",
        ]
    }
    body["warning_seconds"] = 450
    body["client_colours"]["healthy"] = {
        "background": "#224466",
        "foreground": "#ffffff",
    }
    body["client_colours"]["mode"] = "dark"
    assert change(c, "/administration/clients", body).status_code == 200
    assert c.get("/dashboard/clients").json()["colours"] == body["client_colours"]
    assert c.get("/administration").json()["config"]["services"] == settings["services"]
    assert (
        change(
            c, "/administration/services", {"services": ["chrony.service"]}
        ).status_code
        == 200
    )
    saved = c.get("/administration").json()["config"]
    assert (
        saved["warning_seconds"] == 450
        and saved["client_colours"] == body["client_colours"]
    )
    invalid = copy.deepcopy(body)
    invalid["client_colours"]["healthy"]["foreground"] = "red;display:none"
    assert change(c, "/administration/clients", invalid).status_code == 422
    assert (
        change(
            c, "/administration/clients", {**body, "critical_seconds": 400}
        ).status_code
        == 422
    )
    assert c.put("/administration/clients", json=body).status_code == 403
    change(
        c,
        "/administration/users",
        dict(username="viewer", password="viewer-password", roles=["User"]),
    )
    login(c, "viewer", "viewer-password")
    assert change(c, "/administration/clients", body).status_code == 403
    assert (
        change(
            c, "/administration/services", {"services": ["chrony.service"]}
        ).status_code
        == 403
    )
    assert c.get("/admin/clients").status_code == 403
