from __future__ import annotations

from version import DASHBOARD_VERSION, API_VERSION
import asyncio
import hashlib
from contextlib import asynccontextmanager
from telemetry import Monitor, pretty_hostname, solar_status, client_hostname
import csv
import io
import ipaddress
import socket
import struct
import subprocess
import threading
import time
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.templating import Jinja2Templates
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ASSET_VERSION = hashlib.sha256(b"".join((BASE_DIR / name).read_bytes() for name in ("static/app.js", "static/dashboard.js", "static/app.css"))).hexdigest()[:12]

CHRONYC = "/usr/bin/chronyc"

CHRONYC_TIMEOUT = 5
NTP_TIMEOUT = 2

CLIENT_CACHE_SECONDS = 5
TRACKING_CACHE_SECONDS = 5
SOURCES_CACHE_SECONDS = 5

NTP_SERVER = "127.0.0.1"
NTP_PORT = 123

NTP_UNIX_EPOCH_OFFSET = 2208988800


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

limiter = Limiter(
    key_func=get_remote_address
)

@asynccontextmanager
async def lifespan(app):
    monitor.initialise()
    worker = threading.Thread(target=monitor.run, daemon=True)
    worker.start()
    try:
        yield
    finally:
        monitor.stop.set()
        await asyncio.to_thread(worker.join, 10)


app = FastAPI(
    lifespan=lifespan,
    title="TimeBeacon API",
    description="Precision time, server health, GPS reception, services, clients and historical telemetry. Authenticated history exports default to the last 60 minutes; start and end accept Unix timestamps in seconds. Original samples are retained indefinitely. Historical fields reflect what was collected at the time.",
    version=API_VERSION,
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.mount(
    "/static",
    StaticFiles(
        directory=BASE_DIR / "static"
    ),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

# ---------------------------------------------------------------------------
# Authentication Handler
# ---------------------------------------------------------------------------

API_TOKEN = os.environ.get(
    "NTP_DASHBOARD_API_TOKEN"
)

if not API_TOKEN:
    raise RuntimeError(
        "NTP_DASHBOARD_API_TOKEN is not configured"
    )

bearer_scheme = HTTPBearer(
    auto_error=False
)


def require_api_token(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
):
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not secrets.compare_digest(
            credentials.credentials,
            API_TOKEN,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

cache_lock = threading.Lock()

cache: dict[str, dict[str, Any]] = {
    "clients": {
        "timestamp": 0.0,
        "value": None,
    },
    "tracking": {
        "timestamp": 0.0,
        "value": None,
    },
    "sources": {
        "timestamp": 0.0,
        "value": None,
    },
}


def cached_value(
    name: str,
    lifetime: int,
    callback,
):
    """
    Return a cached value when sufficiently recent.

    The cache prevents every browser/API client from spawning its own
    chronyc process on every request.
    """

    now = time.monotonic()

    with cache_lock:
        entry = cache[name]

        if (
            entry["value"] is not None
            and now - entry["timestamp"] < lifetime
        ):
            return entry["value"]

    value = callback()

    with cache_lock:
        cache[name]["timestamp"] = now
        cache[name]["value"] = value

    return value


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def run_chronyc(
    *args: str,
    sudo: bool = False,
) -> str:
    """
    Execute chronyc.

    The clients command requires privileged access to the chronyd Unix
    socket on this server, so only that command is run through sudo.
    """

    if sudo:
        command = [
            "/usr/bin/sudo",
            "-n",
            CHRONYC,
            *args,
        ]
    else:
        command = [
            CHRONYC,
            *args,
        ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=CHRONYC_TIMEOUT,
            check=True,
        )

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"chronyc {' '.join(args)} timed out"
        ) from exc

    except subprocess.CalledProcessError as exc:
        message = (
            exc.stderr
            or exc.stdout
            or f"chronyc {' '.join(args)} failed"
        ).strip()

        raise RuntimeError(message) from exc

    return result.stdout


# ---------------------------------------------------------------------------
# NTP
# ---------------------------------------------------------------------------

def query_ntp_server(
    address: str = NTP_SERVER,
) -> dict[str, Any]:
    """
    Query the local NTP server directly using UDP/123.

    Returns the transmit timestamp supplied by the NTP server.
    """

    packet = bytearray(48)

    # LI = 0
    # VN = 4
    # Mode = 3 (client)
    packet[0] = 0x23

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    ) as client:

        client.settimeout(
            NTP_TIMEOUT
        )

        started = time.monotonic()

        client.sendto(
            packet,
            (
                address,
                NTP_PORT,
            ),
        )

        response, remote = client.recvfrom(
            512
        )

        elapsed = time.monotonic() - started

    if len(response) < 48:
        raise RuntimeError(
            "Invalid NTP response length"
        )

    if remote[0] != address or remote[1] != NTP_PORT:
        raise RuntimeError("Unexpected NTP responder")
    if response[0] & 7 != 4 or response[0] >> 6 == 3 or not 0 < response[1] < 16:
        raise RuntimeError("NTP server is not synchronised")
    if response[40:48] == bytes(8):
        raise RuntimeError("NTP transmit timestamp is missing")

    values = struct.unpack(
        "!12I",
        response[:48],
    )

    seconds = values[10]
    fraction = values[11]

    unix_timestamp = (
        seconds
        - NTP_UNIX_EPOCH_OFFSET
        + fraction / 2**32
    )

    utc_datetime = datetime.fromtimestamp(
        unix_timestamp,
        tz=timezone.utc,
    )

    local_datetime = utc_datetime.astimezone()

    return {
        "server": address,
        "remote_address": remote[0],
        "timestamp": unix_timestamp,
        "utc": utc_datetime.isoformat(
            timespec="microseconds"
        ),
        "local": local_datetime.isoformat(
            timespec="microseconds"
        ),
        "round_trip_ms": round(
            elapsed * 1000,
            3,
        ),
    }


# ---------------------------------------------------------------------------
# Chrony tracking
# ---------------------------------------------------------------------------

def fetch_tracking() -> dict[str, str]:
    output = run_chronyc(
        "tracking"
    )

    result: dict[str, str] = {}

    for line in output.splitlines():

        if ":" not in line:
            continue

        key, value = line.split(
            ":",
            1,
        )

        result[
            key.strip()
        ] = value.strip()

    return result


def get_tracking():
    return cached_value(
        "tracking",
        TRACKING_CACHE_SECONDS,
        fetch_tracking,
    )


# ---------------------------------------------------------------------------
# Chrony sources
# ---------------------------------------------------------------------------

SOURCE_FIELDS = [
    "mode",
    "state",
    "name",
    "stratum",
    "poll",
    "reach",
    "last_rx",
    "adjusted_offset",
    "measured_offset",
    "estimated_error",
]


def fetch_sources() -> list[dict[str, str]]:
    """Return machine-readable Chrony source information."""

    output = run_chronyc(
        "-c",
        "sources",
    )

    reader = csv.reader(
        io.StringIO(output)
    )

    sources = []

    for row in reader:
        if not row:
            continue

        if len(row) < len(SOURCE_FIELDS):
            continue

        source = dict(
            zip(
                SOURCE_FIELDS,
                row[:len(SOURCE_FIELDS)],
            )
        )

        sources.append(source)

    return sources


def get_sources():
    return cached_value(
        "sources",
        SOURCES_CACHE_SECONDS,
        fetch_sources,
    )


# ---------------------------------------------------------------------------
# Chrony clients
# ---------------------------------------------------------------------------

def parse_client_line(
    line: str,
) -> dict[str, str] | None:

    parts = line.split()

    if not parts:
        return None

    address = parts[0]
    fields = parts[1:]

    def value(index: int) -> str:
        if index < len(fields):
            return fields[index]

        return ""

    return {
        "addr": address,
        "NTP": value(0),
        "Drop": value(1),
        "Int": value(2),
        "IntL": value(3),
        "Last": value(4),
        "Cmd": value(5),
        "CmdDrop": value(6),
        "CmdInt": value(7),
        "CmdLast": value(8),
    }


def client_sort_key(
    client: dict[str, str],
):
    address = client["addr"]

    try:
        ip = ipaddress.ip_address(
            address
        )

        if ip.version == 4:
            return (
                1,
                int(ip),
            )

        return (
            2,
            int(ip),
        )

    except ValueError:
        return (
            0,
            address.lower(),
        )


def fetch_clients() -> list[dict[str, str]]:
    """
    Fetch Chrony clients.

    This command requires sudo because /run/chrony is accessible only
    to the chronyd account/root on this server.
    """

    output = run_chronyc(
        "-n", "clients",
        sudo=True,
    )

    lines = output.splitlines()

    if len(lines) < 3:
        return []

    clients = []

    for line in lines[2:]:

        if not line.strip():
            continue

        client = parse_client_line(
            line
        )

        if client:
            client["hostname"] = client_hostname(client["addr"])
            clients.append(
                client
            )

    clients.sort(
        key=client_sort_key
    )

    return clients


def get_clients():
    return cached_value(
        "clients",
        CLIENT_CACHE_SECONDS,
        fetch_clients,
    )


# ---------------------------------------------------------------------------
# Web UI
# ---------------------------------------------------------------------------

@app.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def dashboard(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"hostname": pretty_hostname(), "asset_version": ASSET_VERSION, "dashboard_version": DASHBOARD_VERSION, "api_version": API_VERSION},
        headers={"Cache-Control": "no-cache"},
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get(
    "/api/time",
    dependencies=[
        Depends(require_api_token)
    ],
)
@limiter.limit("10/second")
async def api_time(
    request: Request,
):

    try:
        result = await asyncio.to_thread(
            query_ntp_server
        )

        return {
            "status": "ok",
            **result,
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "timestamp": current_timestamp(),
        }

@app.get(
    "/dashboard/time",
    include_in_schema=False,
)
async def dashboard_time():

    try:
        result = await asyncio.to_thread(
            query_ntp_server
        )

        return {
            "status": "ok",
            **result,
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "timestamp": current_timestamp(),
        }

@app.get(
    "/api/chrony/tracking",
    dependencies=[
        Depends(require_api_token)
    ],
)
@limiter.limit("10/second")
async def api_time(
    request: Request,
):

    try:
        tracking = await asyncio.to_thread(
            get_tracking
        )

        return {
            "status": "ok",
            "timestamp": current_timestamp(),
            "tracking": tracking,
        }

    except Exception as exc:
        return {
            "status": "error",
            "timestamp": current_timestamp(),
            "error": str(exc),
        }

@app.get(
    "/dashboard/tracking",
    include_in_schema=False,
)
async def dashboard_tracking():

    try:
        tracking = await asyncio.to_thread(
            get_tracking
        )

        return {
            "status": "ok",
            "timestamp": current_timestamp(),
            "tracking": tracking,
        }

    except Exception as exc:
        return {
            "status": "error",
            "timestamp": current_timestamp(),
            "error": str(exc),
        }

@app.get(
    "/api/chrony/sources",
    dependencies=[
        Depends(require_api_token)
    ],
)
@limiter.limit("10/second")
async def api_time(
    request: Request,
):

    try:
        sources = await asyncio.to_thread(
            get_sources
        )

        return {
            "status": "ok",
            "timestamp": current_timestamp(),
            "sources": sources,
        }

    except Exception as exc:
        return {
            "status": "error",
            "timestamp": current_timestamp(),
            "error": str(exc),
        }

@app.get(
    "/dashboard/sources",
    include_in_schema=False,
)
async def dashboard_sources():

    try:
        sources = await asyncio.to_thread(
            get_sources
        )

        return {
            "status": "ok",
            "timestamp": current_timestamp(),
            "sources": sources,
        }

    except Exception as exc:
        return {
            "status": "error",
            "timestamp": current_timestamp(),
            "error": str(exc),
        }

@app.get(
    "/api/chrony/clients",
    dependencies=[
        Depends(require_api_token)
    ],
)
@limiter.limit("10/second")
async def api_time(
    request: Request,
):

    try:
        clients = await asyncio.to_thread(
            get_clients
        )

        return {
            "status": "ok",
            "timestamp": current_timestamp(),
            "count": len(clients),
            "clients": clients,
        }

    except Exception as exc:
        return {
            "status": "error",
            "timestamp": current_timestamp(),
            "count": 0,
            "clients": [],
            "error": str(exc),
        }

@app.get(
    "/dashboard/clients",
    include_in_schema=False,
)
async def dashboard_clients():

    try:
        clients = await asyncio.to_thread(
            get_clients
        )

        return {
            "status": "ok",
            "timestamp": current_timestamp(),
            "count": len(clients),
            "clients": clients,
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }

@app.get("/health")
async def health():

    checks = {
        "chrony": False,
        "ntp": False,
    }

    errors = {}

    try:
        tracking = await asyncio.to_thread(
            get_tracking
        )

        checks["chrony"] = True

    except Exception as exc:
        tracking = {}

        errors["chrony"] = str(
            exc
        )

    try:
        ntp = await asyncio.to_thread(
            query_ntp_server
        )

        checks["ntp"] = True

    except Exception as exc:
        ntp = {}

        errors["ntp"] = str(
            exc
        )

    healthy = all(
        checks.values()
    )

    result = {
        "status": (
            "ok"
            if healthy
            else "error"
        ),
        "timestamp": current_timestamp(),
        "checks": checks,
        "chrony": {
            "stratum": tracking.get(
                "Stratum"
            ),
            "reference_id": tracking.get(
                "Reference ID"
            ),
            "leap_status": tracking.get(
                "Leap status"
            ),
        },
        "ntp": {
            "round_trip_ms": ntp.get(
                "round_trip_ms"
            ),
        },
    }

    if errors:
        result["errors"] = errors

    return result


monitor = Monitor(get_tracking, query_ntp_server, sources=get_sources, clients=get_clients)


@app.get("/dashboard/status", include_in_schema=False)
async def dashboard_status():
    return await asyncio.to_thread(monitor.latest)


@app.get("/dashboard/history", include_in_schema=False)
async def dashboard_history(start: int | None = Query(default=None, ge=0), end: int | None = Query(default=None, ge=0)):
    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="Start must precede end")
    return {"samples": await asyncio.to_thread(monitor.history, start, end), "bounds": await asyncio.to_thread(monitor.history_bounds)}


@app.get("/dashboard/solar", include_in_schema=False)
async def dashboard_solar(latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180)):
    return solar_status(latitude=latitude, longitude=longitude)


from pydantic import BaseModel, Field, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import urlsplit


class ClockSetting(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    zone: str = Field(min_length=1, max_length=100)

    @field_validator("zone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown time zone")
        return value


class DashboardSettingsUpdate(BaseModel):
    version: int = Field(ge=1)
    location: str | None = Field(default=None, min_length=1, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    clocks: list[ClockSetting] | None = Field(default=None, max_length=64)


@app.get("/dashboard/settings", include_in_schema=False)
async def dashboard_settings():
    return await asyncio.to_thread(monitor.get_settings)


@app.patch("/dashboard/settings", include_in_schema=False)
async def update_dashboard_settings(request: Request, changes: DashboardSettingsUpdate):
    origin = urlsplit(request.headers.get("origin", ""))
    if request.headers.get("x-dashboard-settings") != "1" or origin.netloc != request.headers.get("host") or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Settings changes must originate from this dashboard")
    values = changes.model_dump(exclude={"version"}, exclude_none=True)
    if "clocks" in values and len({clock["zone"] for clock in values["clocks"]}) != len(values["clocks"]):
        raise HTTPException(status_code=422, detail="Duplicate clocks")
    saved = await asyncio.to_thread(monitor.save_settings, changes.version, values)
    if saved is None:
        raise HTTPException(status_code=409, detail="Settings changed in another browser. Reload and try again.")
    return saved


@app.get("/api/dashboard", dependencies=[Depends(require_api_token)], tags=["Dashboard"])
async def api_dashboard():
    """All current dashboard data, shared clock/location settings and daylight state."""
    status,settings,clients,ntp=await asyncio.gather(dashboard_status(),dashboard_settings(),dashboard_clients(),dashboard_time())
    preferences=settings["settings"]
    return {"dashboard_version":DASHBOARD_VERSION,"api_version":API_VERSION,"status":status,"settings":settings,"clients":clients,"time":ntp,"solar":solar_status(latitude=preferences["latitude"],longitude=preferences["longitude"])}


@app.get("/api/history", dependencies=[Depends(require_api_token)], tags=["History"])
async def api_history(start: int | None=Query(None,ge=0),end: int | None=Query(None,ge=0),after: int=Query(-1,ge=-1),limit: int=Query(1000,ge=1,le=5000)):
    """Export unmodified stored telemetry including GPS, satellites, PPS, acquisition, services and metrics.

    Defaults to the last 60 minutes. Use start=0 for all recorded time.
    Follow next_after with the returned start/end to page through the same fixed period.
    Older records may omit fields that were not yet collected; no values are invented.
    """
    end=int(time.time()) if end is None else end
    start=max(0,end-3600) if start is None else start
    if start>=end:raise HTTPException(422,"Start must precede end")
    result=await asyncio.to_thread(monitor.export_history,start,end,after,limit)
    return {"start":start,"end":end,"bounds":await asyncio.to_thread(monitor.history_bounds),**result}
