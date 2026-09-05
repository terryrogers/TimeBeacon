"""Persistent, browser-independent monitoring for the dashboard."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import threading
import time
import ipaddress
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil
from astral import Observer
from astral.sun import elevation, sunrise, sunset


ROOT = Path(__file__).resolve().parent
DATABASE = Path(os.getenv("NTP_DASHBOARD_HISTORY_DB", str(ROOT / "data" / "history.sqlite3")))
REQUIRED_SERVICES = tuple(os.getenv(
    "NTP_DASHBOARD_SERVICES",
    "chrony.service ntp-dashboard.service gpsd.service NetworkManager.service "
    "ssh.service cron.service systemd-journald.service avahi-daemon.service "
    "colord.service cups-browsed.service cups.service dbus.service "
    "ModemManager.service polkit.service rtkit-daemon.service systemd-logind.service "
    "systemd-udevd.service thetechwizardagent.service triggerhappy.service wpa_supplicant.service",
).split())


def command(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=5, check=True).stdout.strip()


def pretty_hostname():
    try:
        return command("hostnamectl", "--pretty") or socket.gethostname()
    except (OSError, subprocess.SubprocessError):
        return socket.gethostname()


def solar_status(now=None, latitude=None, longitude=None):
    zone = ZoneInfo(os.getenv("NTP_DASHBOARD_TIMEZONE", "Europe/London"))
    now = now or datetime.now(zone)
    observer = Observer(latitude if latitude is not None else float(os.getenv("NTP_DASHBOARD_LATITUDE", "51.5074")),
                        longitude if longitude is not None else float(os.getenv("NTP_DASHBOARD_LONGITUDE", "-0.1278")))
    result = {"location": os.getenv("NTP_DASHBOARD_LOCATION", "London"),
              "theme": "light" if elevation(observer, now, with_refraction=False) >= -0.833 else "dark"}
    for label, calculate in (("sunrise", sunrise), ("sunset", sunset)):
        try:
            result[label] = calculate(observer, date=now.astimezone(zone).date(), tzinfo=zone).isoformat()
        except ValueError:
            result[label] = None  # Polar day/night; solar elevation still defines the theme.
    return result


_cpu_sample = threading.local()


def system_metrics():
    cpu = psutil.cpu_percent(interval=None if getattr(_cpu_sample, "primed", False) else 1.0)
    _cpu_sample.primed = True
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getenv("NTP_DASHBOARD_STORAGE_PATH", "/"))
    temperatures = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
    temps = [entry.current for group in temperatures.values() for entry in group if entry.current is not None]
    return {"cpu": cpu, "ram": memory.percent,
            "storage": disk.percent, "temperature": max(temps) if temps else None,
            "uptime": time.time() - psutil.boot_time(), "ram_total": memory.total,
            "ram_used": memory.total - memory.available,
            "storage_total": disk.total, "storage_used": disk.used}


_service_cpu = {}


def service_status():
    properties = "Id,Description,ActiveState,SubState,UnitFileState,CPUUsageNSec,MemoryCurrent,ControlGroup"
    try:
        output = command("systemctl", "show", *REQUIRED_SERVICES, "-p", properties)
        units = {}
        for block in output.split("\n\n"):
            values = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
            if values.get("Id"):
                units[values["Id"]] = values
    except (OSError, subprocess.SubprocessError):
        units = {}
    results = []
    now = time.monotonic()
    for name in REQUIRED_SERVICES:
        values = units.get(name, {})
        state = values.get("ActiveState", "unknown")
        cpu = None
        try:
            used = int(values["CPUUsageNSec"])
            if used >= 2**64-1:
                raise ValueError()
            previous = _service_cpu.get(name)
            if previous and now > previous[1] and used >= previous[0]:
                cpu = (used-previous[0])/1e9/(now-previous[1])*100
            _service_cpu[name] = (used, now)
        except (KeyError, ValueError):
            pass
        ram = None
        ram_kind = "RSS"
        try:
            measured = int(values["MemoryCurrent"])
            if 0 <= measured < 2**64-1:
                ram = measured
                ram_kind = "cgroup"
        except (KeyError, ValueError):
            pass
        group = values.get("ControlGroup", "")
        if group and ram is None:
            base = Path("/sys/fs/cgroup")
            directory = (base / group.lstrip("/")).resolve()
            if directory.is_relative_to(base):
                try:
                    pids = {int(pid) for file in directory.rglob("cgroup.procs") for pid in file.read_text().split()}
                    total, readable = 0, False
                    for pid in pids:
                        try:
                            total += psutil.Process(pid).memory_info().rss
                            readable = True
                        except psutil.Error:
                            pass
                    if readable:
                        ram = total
                except (OSError, ValueError):
                    pass
        results.append({"name": name, "description": values.get("Description", name),
                        "running": state == "active", "state": state,
                        "startup": values.get("UnitFileState") or "unknown",
                        "status": values.get("SubState") or state, "cpu": cpu, "ram": ram, "ram_kind": ram_kind})
    try:
        failed = command("systemctl", "list-units", "--state=failed", "--type=service", "--no-legend", "--plain").splitlines()
        failed = [row.split()[0] for row in failed if row.strip()]
    except (OSError, subprocess.SubprocessError):
        failed = ["Service checks unavailable"]
    return results, failed


def time_daemon():
    names = {p.info["name"] for p in psutil.process_iter(["name"])}
    for process, label in (("chronyd", "Chrony"), ("ntpsec", "NTPsec"), ("ntpd", "NTP (ntpd)"), ("systemd-timesyncd", "systemd-timesyncd")):
        if process in names:
            return label
    return "Time Server (not detected)"


def gps_status():
    result = {"fix": "Unavailable", "visible": None, "used": None, "pps": False}
    try:
        output = subprocess.run(["/usr/bin/gpspipe", "-w", "-n", "12"], capture_output=True, text=True, timeout=3).stdout
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
    except OSError:
        return result
    for line in output.splitlines():
        try:
            report = json.loads(line)
        except ValueError:
            continue
        if report.get("class") == "TPV":
            stamp = report.get("time")
            try:
                fresh = abs(time.time() - datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()) < 10
            except (ValueError, TypeError, AttributeError):
                fresh = False
            result["fix_details"] = {k: report[k] for k in ("time", "mode", "eph", "epv", "ept") if k in report}
            result["fix"] = {1: "No fix", 2: "2D fix", 3: "3D fix"}.get(report.get("mode"), "Unknown") if fresh else "No recent fix"
        elif report.get("class") == "SKY":
            result["satellites"] = [{k: satellite[k] for k in ("PRN", "gnssid", "svid", "el", "az", "ss", "used") if k in satellite} for satellite in report.get("satellites", [])]
            result["dop"] = {k: report[k] for k in ("gdop", "hdop", "pdop", "tdop", "vdop") if k in report}
            result["visible"] = report.get("nSat", len(report.get("satellites", [])))
            result["used"] = report.get("uSat", sum(bool(s.get("used")) for s in report.get("satellites", [])))
        elif report.get("class") == "PPS":
            result["pps"] = True
            result["pps_details"] = {k: report[k] for k in ("real_sec", "real_nsec", "clock_sec", "clock_nsec", "precision") if k in report}
    return result


_dns_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="client-dns")
_dns_lock = threading.Lock()
_dns_cache = {}


def lookup_client(address):
    ipaddress.ip_address(address)  # Only reverse lookups of validated addresses.
    try:
        output = subprocess.run(["/usr/bin/nslookup", "-timeout=2", "-retry=1", address], capture_output=True, text=True, timeout=3).stdout
        match = re.search(r"name\s*=\s*([^\s]+)", output, re.IGNORECASE)
        return match.group(1).rstrip(".").split(".")[0] if match else None
    except (OSError, subprocess.SubprocessError):
        return None


def client_hostname(address):
    """Never hold up the dashboard while DNS is slow or a PTR is missing."""
    with _dns_lock:
        now = time.monotonic()
        entry = _dns_cache.get(address)
        if entry is None or (entry[0].done() and now - entry[1] > 600):
            if len(_dns_cache) >= 4096:
                for key, (future, stamp) in list(_dns_cache.items()):
                    if future.done() and now - stamp > 600:
                        del _dns_cache[key]
                if len(_dns_cache) >= 4096:
                    return None
            entry = (_dns_pool.submit(lookup_client, address), now)
            _dns_cache[address] = entry
        if entry[0].done():
            try:
                return entry[0].result()
            except Exception:
                return None
        return None


class Monitor:
    def __init__(self, tracking, ntp, database=DATABASE, sources=None, clients=None):
        self.tracking = tracking
        self.ntp = ntp
        self.database = Path(database)
        self.sources = sources
        self.clients = clients
        self.stop = threading.Event()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialise(self):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS samples (timestamp INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, payload TEXT NOT NULL)")
            defaults = {"location": "London", "latitude": 51.5074, "longitude": -0.1278,
                        "clocks": [{"name": name,"zone": zone} for name,zone in [("New York","America/New_York"),("London","Europe/London"),("Paris","Europe/Paris"),("Tel Aviv","Asia/Jerusalem"),("Tokyo","Asia/Tokyo"),("Sydney","Australia/Sydney")]]}
            db.execute("INSERT OR IGNORE INTO settings VALUES (1,1,?)", (json.dumps(defaults),))

    def collect(self):
        checks, errors = {}, []
        metrics, tracking, ntp = {}, {}, {}
        try:
            metrics = system_metrics()
            checks["system_metrics"] = True
        except Exception:
            checks["system_metrics"] = False
            errors.append("System metrics unavailable")
        services, failed = service_status()
        checks["required_services"] = bool(services) and all(item["running"] for item in services)
        checks["no_failed_services"] = not failed
        try:
            tracking = self.tracking()
            checks["chrony_synchronised"] = tracking.get("Leap status") in ("Normal", "Insert second", "Delete second") and 0 < int(tracking.get("Stratum", 0)) < 16
        except Exception:
            checks["chrony_synchronised"] = False
            errors.append("Chrony tracking unavailable")
        try:
            ntp = self.ntp()
            checks["ntp_response"] = True
        except Exception:
            checks["ntp_response"] = False
            errors.append("Healthy NTP response unavailable")
        checks["storage_capacity"] = metrics.get("storage", 100) < 95
        metrics["ntp_rtt"] = ntp.get("round_trip_ms")
        for key, label, scale in (("last_offset", "Last offset", 1000), ("rms_offset", "RMS offset", 1000), ("stratum", "Stratum", 1)):
            try:
                metrics[key] = float(tracking[label].split()[0]) * scale
            except (KeyError, ValueError, IndexError):
                metrics[key] = None
        try:
            daemon = time_daemon()
        except (OSError, psutil.Error):
            daemon = "Time Server (not detected)"
        acquisition = {"selected": None}
        if self.sources:
            try:
                sources = self.sources()
                acquisition["selected"] = next((s["name"] for s in sources if s.get("state") == "*"), None)
                acquisition["sources"] = sources
            except Exception:
                pass
        clients=[]
        if self.clients:
            try:clients=self.clients()
            except Exception:errors.append("Client snapshot unavailable")
        return {"clients":clients,"ntp":ntp,"timestamp": int(time.time()), "hostname": pretty_hostname(), "metrics": metrics,
                "time_daemon": daemon, "gps": gps_status(), "acquisition": acquisition,
                "tracking": tracking, "checks": checks, "services": services, "failed_services": failed,
                "errors": errors, "healthy": all(checks.values())}

    def sample(self):
        payload = self.collect()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO samples VALUES (?, ?)", (payload["timestamp"], json.dumps(payload)))

    def latest(self):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM samples ORDER BY timestamp DESC LIMIT 1").fetchone()
        result = json.loads(row[0]) if row else {"healthy": False, "timestamp": None, "metrics": {}, "checks": {}}
        result["stale"] = result["timestamp"] is None or time.time() - result["timestamp"] > 90
        result["healthy"] = result["healthy"] and not result["stale"]
        result["solar"] = solar_status()
        return result

    def history(self, start=None, end=None):
        end = int(time.time()) if end is None else end
        start = end - 3600 if start is None else start
        bucket = max(1, (end-start)//1500)
        with self.connect() as db:
            rows = db.execute("SELECT MIN(timestamp), payload FROM samples WHERE timestamp >= ? AND timestamp <= ? GROUP BY CAST((timestamp-?)/? AS INTEGER) ORDER BY timestamp", (start,end,start,bucket)).fetchall()
        result=[]
        for stamp,payload in rows:
            sample=json.loads(payload);sample["timestamp"]=stamp
            gps=sample.get("gps",{});metrics=sample.setdefault("metrics",{})
            metrics.update({"gps_used":gps.get("used"),"gps_visible":gps.get("visible"),"gps_mode":gps.get("fix_details",{}).get("mode"),"gps_pps":int(gps["pps"]) if "pps" in gps else None,"gps_hdop":gps.get("dop",{}).get("hdop"),"gps_tdop":gps.get("dop",{}).get("tdop")})
            result.append(sample)
        return result

    def export_history(self, start, end, after, limit):
        with self.connect() as db:
            rows=db.execute("SELECT timestamp,payload FROM samples WHERE timestamp>=? AND timestamp<=? AND timestamp>? ORDER BY timestamp LIMIT ?",(start,end,after,limit+1)).fetchall()
        more=len(rows)>limit;rows=rows[:limit]
        samples=[]
        for stamp,payload in rows:
            sample=json.loads(payload);sample["timestamp"]=stamp;samples.append(sample)
        return {"samples":samples,"next_after":rows[-1][0] if more else None}

    def history_bounds(self):
        with self.connect() as db:
            first,last = db.execute("SELECT MIN(timestamp), MAX(timestamp) FROM samples").fetchone()
        return {"first": first, "last": last}

    def get_settings(self):
        with self.connect() as db:
            version,payload=db.execute("SELECT version,payload FROM settings WHERE id=1").fetchone()
        return {"version":version,"settings":json.loads(payload)}

    def save_settings(self, version, changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current,payload=db.execute("SELECT version,payload FROM settings WHERE id=1").fetchone()
            if current != version:
                return None
            values=json.loads(payload);values.update(changes)
            db.execute("UPDATE settings SET version=?,payload=? WHERE id=1",(current+1,json.dumps(values)))
        return {"version":current+1,"settings":values}

    def run(self):
        # Each Uvicorn worker competes for this lock; one sampler owns the database.
        import fcntl
        with self.database.with_suffix(".lock").open("a") as lock:
            while not self.stop.is_set():
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    self.stop.wait(5)
                    continue
                try:
                    while not self.stop.is_set():
                        try:
                            self.sample()
                        except Exception:
                            # Staleness is exposed to clients rather than displaying old green status.
                            import logging
                            logging.getLogger(__name__).error("Dashboard sample could not be saved")
                        self.stop.wait(30)
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)
