from unittest.mock import patch
from test_access import system, login
from test_service_repairs import configured, MISSING, ORIGIN, URL


def test_repair_verifies_fresh_health_and_remaining_issues(system):
    m, c = system
    login(c)
    version = configured(m, ["chrony.service", "missing.service"])
    fresh = {
        **m.latest(),
        "healthy": False,
        "checks": {"ntp_response": False},
        "services": [{"name": "chrony.service", "running": True}],
    }
    with patch("service_repairs.inspect_service", return_value=MISSING), patch.object(
        m, "collect", return_value=fresh
    ) as collect:
        result = c.post(
            URL,
            json=dict(
                unit="missing.service", action="remove_check", config_version=version
            ),
            headers=ORIGIN,
        ).json()
        assert result["resolved"] is True and result["healthy"] is False
        assert "remains degraded: ntp response" in result["message"]
        assert m.latest()["checks"] == fresh["checks"]
        collect.assert_called_once()


def test_repair_collection_failure_is_unconfirmed(system):
    m, c = system
    login(c)
    version = configured(m, ["chrony.service", "missing.service"])
    with patch("service_repairs.inspect_service", return_value=MISSING), patch.object(
        m, "sample", side_effect=OSError("unavailable")
    ):
        result = c.post(
            URL,
            json=dict(
                unit="missing.service", action="remove_check", config_version=version
            ),
            headers=ORIGIN,
        ).json()
        assert (
            result["success"]
            and result["resolved"] is None
            and result["healthy"] is None
        )
        assert "not yet confirmed" in result["message"]
