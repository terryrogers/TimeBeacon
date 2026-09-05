"""Read-only operating system and hardware inventory, cached for five minutes."""

import json
import platform
import re
import struct
import subprocess
import time
from pathlib import Path
from threading import Lock

import psutil

_cached = None
_expires = 0
_lock = Lock()


def read_text(path):
    try:
        return Path(path).read_text().strip().strip("\x00")
    except (OSError, UnicodeError):
        return ""


def root_disks(devices):
    """Select whole disks backing /, including partition and device-mapper trees."""

    def contains_root(device):
        return "/" in (device.get("mountpoints") or []) or any(
            contains_root(child) for child in device.get("children", [])
        )

    found = {}

    def visit(device):
        if device.get("type") == "disk" and contains_root(device):
            found[device.get("name")] = device
        for child in device.get("children", []):
            visit(child)

    for device in devices:
        visit(device)
    return list(found.values())


def detect_system_information():
    bits = struct.calcsize("P") * 8
    try:
        os_name = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
    except (OSError, AttributeError):
        os_name = " ".join(filter(None, (platform.system(), platform.release())))
    operating_system = (
        f"{os_name[:-1]}, {bits}-bit)"
        if os_name.endswith(")")
        else f"{os_name} ({bits}-bit)"
    )
    model = read_text("/sys/firmware/devicetree/base/model") or read_text(
        "/proc/device-tree/model"
    )
    if model.startswith("Raspberry Pi"):
        model = re.sub(r"\s+Model\s+.*$", "", model)
    if not model:
        model = (
            read_text("/sys/class/dmi/id/product_name")
            or platform.machine()
            or "Hardware unavailable"
        )
    try:
        cores = psutil.cpu_count(logical=False) or psutil.cpu_count()
    except (OSError, psutil.Error):
        cores = None
    try:
        max_khz = read_text("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
        if max_khz:
            ghz = int(max_khz) / 1e6
        else:
            frequency = psutil.cpu_freq()
            ghz = frequency.max / 1000 if frequency and frequency.max > 0 else None
    except (ValueError, OSError, psutil.Error, NotImplementedError):
        ghz = None
    try:
        ram_bytes = psutil.virtual_memory().total
    except (OSError, psutil.Error):
        ram_bytes = None
    disks = []
    try:
        raw = subprocess.run(
            ["lsblk", "-b", "-J", "-o", "NAME,TYPE,SIZE,TRAN,ROTA,MOUNTPOINTS"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        ).stdout
        for disk in root_disks(json.loads(raw).get("blockdevices", [])):
            size = int(disk.get("size") or 0)
            if size <= 0:
                continue
            transport = disk.get("tran")
            kind = (
                "NVMe"
                if transport == "nvme" or disk.get("name", "").startswith("nvme")
                else (
                    "SD"
                    if disk.get("name", "").startswith("mmcblk")
                    else (
                        "USB storage"
                        if transport == "usb"
                        else (
                            "HDD"
                            if disk.get("rota") in (True, 1, "1")
                            else (
                                "SSD"
                                if disk.get("rota") in (False, 0, "0")
                                else "storage"
                            )
                        )
                    )
                )
            )
            disks.append(
                {
                    "size_bytes": size,
                    "type": kind,
                    "description": f"{size/1e9:.0f} GB {kind}",
                }
            )
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        pass
    parts = []
    core_label = {1: "Single-Core", 2: "Dual-Core", 4: "Quad-Core", 8: "Octa-Core"}.get(
        cores, f"{cores}-Core" if cores else ""
    )
    cpu = " ".join(filter(None, (f"{ghz:g} GHz" if ghz else "", core_label)))
    if cpu:
        parts.append(cpu)
    if ram_bytes:
        # Present nominal GB for the hardware summary; retain exact usable bytes.
        gib = ram_bytes / 2**30
        parts.append(f"{round(gib) if gib >= 1 else round(gib, 1):g} GB RAM")
    parts.extend(disk["description"] for disk in disks)
    return {
        "operating_system": operating_system,
        "hardware": model + (" (" + ", ".join(parts) + ")" if parts else ""),
        "model": model,
        "architecture_bits": bits,
        "cpu_cores": cores,
        "cpu_max_ghz": ghz,
        "ram_bytes": ram_bytes,
        "storage": disks,
    }


def system_information():
    global _cached, _expires
    with _lock:
        if _cached is None or time.monotonic() >= _expires:
            _cached = detect_system_information()
            _expires = time.monotonic() + 300
        return _cached
