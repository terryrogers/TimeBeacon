import json
from types import SimpleNamespace
from unittest.mock import patch

import server_info
from test_access import system, login, change


def test_detect_pi_and_root_drive():
    disks = [
        {
            "name": "sda",
            "type": "disk",
            "tran": "usb",
            "size": 1000000000000,
            "mountpoints": ["/media/archive"],
        },
        {
            "name": "nvme0n1",
            "type": "disk",
            "tran": "nvme",
            "size": 256060514304,
            "children": [{"type": "part", "mountpoints": ["/"]}],
        },
    ]

    def read(path):
        return {
            "/sys/firmware/devicetree/base/model": "Raspberry Pi 5 Model B Rev 1.1",
            "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq": "2400000",
        }.get(path, "")

    with patch.object(server_info, "read_text", side_effect=read), patch.object(
        server_info.platform,
        "freedesktop_os_release",
        return_value={"PRETTY_NAME": "Debian GNU/Linux 13 (trixie)"},
    ), patch.object(server_info.struct, "calcsize", return_value=8), patch.object(
        server_info.psutil, "cpu_count", return_value=4
    ), patch.object(
        server_info.psutil,
        "virtual_memory",
        return_value=SimpleNamespace(total=16607616 * 1024),
    ), patch.object(
        server_info.subprocess,
        "run",
        return_value=SimpleNamespace(stdout=json.dumps({"blockdevices": disks})),
    ):
        result = server_info.detect_system_information()
    assert result["operating_system"] == "Debian GNU/Linux 13 (trixie, 64-bit)"
    assert (
        result["hardware"]
        == "Raspberry Pi 5 (2.4 GHz Quad-Core, 16 GB RAM, 256 GB NVMe)"
    )
    assert result["storage"][0]["size_bytes"] == 256060514304
    assert len(result["storage"]) == 1


def test_missing_inventory_is_not_invented():
    with patch.object(server_info, "read_text", return_value=""), patch.object(
        server_info.platform, "freedesktop_os_release", side_effect=OSError
    ), patch.object(server_info.psutil, "cpu_count", return_value=None), patch.object(
        server_info.psutil, "cpu_freq", return_value=None
    ), patch.object(
        server_info.psutil, "virtual_memory", side_effect=OSError
    ), patch.object(
        server_info.subprocess, "run", side_effect=FileNotFoundError
    ):
        result = server_info.detect_system_information()
    assert result["cpu_max_ghz"] is None and result["ram_bytes"] is None
    assert result["storage"] == [] and "GHz" not in result["hardware"]


def test_inventory_requires_server_permission(system):
    _, client = system
    login(client)
    inventory = {
        "operating_system": "Example OS (64-bit)",
        "hardware": "Example hardware",
    }
    with patch("access_api.system_information", return_value=inventory):
        assert client.get("/dashboard/status").json()["system_information"] == inventory
        assert client.get("/server/status").json()["system_information"] == inventory
        assert (
            change(
                client,
                "/administration/roles",
                {
                    "name": "Summary",
                    "permissions": ["dashboard.view", "api.view", "clients.summary"],
                },
            ).status_code
            == 200
        )
        assert (
            change(
                client,
                "/administration/users",
                {
                    "username": "summary",
                    "password": "summary-password",
                    "roles": ["Summary"],
                },
            ).status_code
            == 200
        )
        login(client, "summary", "summary-password")
        assert "system_information" not in client.get("/dashboard/status").json()
        assert client.get("/server/status").status_code == 403
