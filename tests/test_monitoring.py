import json
import os
import secrets
import time
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault("NTP_DASHBOARD_API_TOKEN", secrets.token_urlsafe(32))
import main
import telemetry
from fastapi.testclient import TestClient


def monitor(tmp_path):
    instance = telemetry.Monitor(lambda: {"Leap status": "Normal", "Stratum": "2", "Last offset": "0.001 seconds", "RMS offset": "0.002 seconds"},
                                 lambda: {"round_trip_ms": 1}, tmp_path / "history.sqlite3")
    instance.initialise()
    return instance


def test_health_failures_and_offsets(tmp_path):
    instance = monitor(tmp_path)
    with patch.object(telemetry, "system_metrics", return_value={"cpu": 10, "storage": 40}), patch.object(telemetry, "service_status", return_value=([{"name": "chrony", "running": True}], [])):
        payload = instance.collect()
        assert payload["healthy"]
        assert payload["metrics"]["last_offset"] == 1
        instance.tracking = lambda: {"Leap status": "Not synchronised", "Stratum": "0"}
        assert not instance.collect()["healthy"]
        instance.tracking = lambda: {"Leap status": "Normal", "Stratum": "2"}
        with patch.object(telemetry, "service_status", return_value=([{"name": "chrony", "running": False}], [])):
            assert not instance.collect()["healthy"]
        with patch.object(telemetry, "service_status", return_value=([{"name": "chrony", "running": True}], ["failed.service"])):
            assert not instance.collect()["healthy"]


def test_history_survives_reopen_retains_and_expires(tmp_path):
    instance = monitor(tmp_path)
    now = int(time.time())
    payload = {"timestamp": now, "healthy": True, "metrics": {"cpu": 7}}
    with instance.connect() as db:
        db.execute("INSERT INTO samples VALUES (?, ?)", (now - 90000, json.dumps(payload)))
    with patch.object(instance, "collect", return_value=payload):
        instance.sample()
    reopened = telemetry.Monitor(None, None, instance.database)
    assert len(reopened.history()) == 1
    assert len(reopened.history(now-100000,now)) == 2
    assert reopened.latest()["healthy"]
    with patch.object(telemetry.time, "time", return_value=now + 91):
        assert reopened.latest()["stale"]
        assert not reopened.latest()["healthy"]


def test_solar_day_night_and_polar():
    assert telemetry.solar_status(datetime(2026, 6, 21, 12, tzinfo=timezone.utc))["theme"] == "light"
    assert telemetry.solar_status(datetime(2026, 6, 21, 0, tzinfo=timezone.utc))["theme"] == "dark"
    assert telemetry.solar_status(datetime(2026, 6, 21, 12, tzinfo=timezone.utc), 89, 0)["theme"] == "light"
    assert telemetry.solar_status(datetime(2026, 12, 21, 12, tzinfo=timezone.utc), 89, 0)["theme"] == "dark"


def test_http_validation_auth_and_hostname(tmp_path):
    instance = monitor(tmp_path)
    with patch.object(main, "monitor", instance), patch.object(main, "pretty_hostname", return_value="Test <server>"):
        client = TestClient(main.app)
        assert client.get("/api/time").status_code == 401
        assert client.get("/dashboard/solar?latitude=999&longitude=0").status_code == 422
        assert client.get("/dashboard/solar?latitude=nan&longitude=0").status_code == 422
        assert client.get("/dashboard/solar?latitude=51.5&longitude=0").status_code == 200
        assert "Test &lt;server&gt; Server Dashboard" in client.get("/").text
        assert client.get("/dashboard/status").json()["healthy"] is False
        assert client.get("/dashboard/history").json() == {"samples": [], "bounds": {"first": None, "last": None}}


def test_dns_short_names_and_missing_ptr():
    import subprocess
    with patch.object(telemetry.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "1.0.0.10.in-addr.arpa name = example.home.test.\n")):
        assert telemetry.lookup_client("10.0.0.1") == "example"
    with patch.object(telemetry.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "NXDOMAIN")):
        assert telemetry.lookup_client("10.0.0.1") is None


def test_gps_reports_and_timeout_partial_data():
    import subprocess
    report = "\n".join(json.dumps(row) for row in [
        {"class": "TPV", "mode": 3, "time": datetime.now(timezone.utc).isoformat()},
        {"class": "SKY", "nSat": 21, "uSat": 9}, {"class": "PPS"},
    ])
    with patch.object(telemetry.subprocess, "run", side_effect=subprocess.TimeoutExpired("gpspipe", 3, output=report.encode())):
        actual=telemetry.gps_status()
        assert {k:actual[k] for k in ("fix","visible","used","pps")} == {"fix": "3D fix", "visible": 21, "used": 9, "pps": True}
    with patch.object(telemetry.subprocess, "run", side_effect=FileNotFoundError()):
        assert telemetry.gps_status()["fix"] == "Unavailable"


def test_service_accounting_cpu_delta_and_memory():
    def output(*args):
        if "list-units" in args:
            return ""
        return "Id=test.service\nActiveState=active\nSubState=running\nUnitFileState=enabled\nCPUUsageNSec=2000000000\nMemoryCurrent=1048576\nControlGroup="
    with patch.object(telemetry, "REQUIRED_SERVICES", ("test.service",)), patch.object(telemetry, "command", side_effect=output), patch.object(telemetry.time, "monotonic", return_value=20):
        telemetry._service_cpu["test.service"] = (1000000000, 10)
        services, failed = telemetry.service_status()
        assert services[0]["cpu"] == 10
        assert services[0]["ram"] == 1048576
        assert services[0]["ram_kind"] == "cgroup"
        assert services[0]["startup"] == "enabled"
        assert not failed


def test_shared_settings_persistence_conflicts_and_origin(tmp_path):
    instance=monitor(tmp_path)
    with patch.object(main,"monitor",instance):
        client=TestClient(main.app)
        saved=client.get('/dashboard/settings').json()
        headers={"Origin":"http://testserver","X-Dashboard-Settings":"1"}
        response=client.patch('/dashboard/settings',json={"version":saved['version'],"location":"Paris","latitude":48.85,"longitude":2.35},headers=headers)
        assert response.status_code==200
        assert client.patch('/dashboard/settings',json={"version":saved['version'],"location":"Old edit"},headers=headers).status_code==409
        assert client.patch('/dashboard/settings',json={"version":2,"location":"Unsafe"}).status_code==403
        assert client.patch('/dashboard/settings',json={"version":2,"clocks":[{"name":"bad","zone":"Invalid/Zone"}]},headers=headers).status_code==422
        reopened=telemetry.Monitor(None,None,instance.database)
        assert reopened.get_settings()['settings']['location']=='Paris'
        assert len(reopened.get_settings()['settings']['clocks'])==6


def test_full_history_exports_and_auth(tmp_path):
    instance=monitor(tmp_path);now=int(time.time())
    with instance.connect() as db:
        for stamp in [now-7200,now-60,now-30]:
            payload={"timestamp":stamp,"metrics":{"cpu":7},"gps":{"used":9,"pps":True},"acquisition":{"selected":"GPS"}}
            db.execute("INSERT INTO samples VALUES (?,?)",(stamp,json.dumps(payload)))
    with patch.object(main,"monitor",instance):
        client=TestClient(main.app);headers={"Authorization":"Bearer "+main.API_TOKEN}
        assert client.get("/api/dashboard").status_code==401
        assert client.get("/api/history").status_code==401
        first=client.get("/api/history?limit=1",headers=headers).json()
        assert first["samples"][0]["gps"]["used"]==9
        assert first["next_after"]==now-60
        second=client.get(f"/api/history?start={first['start']}&end={first['end']}&after={first['next_after']}",headers=headers).json()
        assert len(second["samples"])==1 and second["next_after"] is None
        assert len(client.get("/api/history?start=0",headers=headers).json()["samples"])==3
        assert client.get("/api/history?start=3&end=2",headers=headers).status_code==422
        samples=client.get("/dashboard/history").json()["samples"]
        assert samples[0]["metrics"]["gps_used"]==9
        assert samples[0]["acquisition"]["selected"]=="GPS"


def test_full_dashboard_snapshot(tmp_path):
    instance=monitor(tmp_path)
    with patch.object(main,"monitor",instance),patch.object(main,"get_clients",return_value=[]),patch.object(main,"query_ntp_server",return_value={"timestamp":1,"round_trip_ms":1}):
        response=TestClient(main.app).get("/api/dashboard",headers={"Authorization":"Bearer "+main.API_TOKEN})
        assert response.status_code==200
        assert set(response.json())=={"dashboard_version","api_version","status","settings","clients","time","solar"}
        assert response.json()["api_version"]=="2.1.0"
