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
ASSET_VERSION = hashlib.sha256(b"".join((BASE_DIR / name).read_bytes() for name in ("static/app.js", "static/dashboard.js", "static/app.css", "static/access.js", "static/theme.css", "static/pages.js", "static/clock-picker.js", "static/client-colours.js", "static/timezones.json"))).hexdigest()[:12]

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
    from security import IdentityStore
    IdentityStore(monitor).initialise()
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

    from security import IdentityStore
    from fastapi.responses import RedirectResponse
    try:
        user = IdentityStore(monitor).authenticate(request)
    except HTTPException:
        return RedirectResponse('/login', status_code=303)
    IdentityStore.require(user, 'dashboard.view')
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"hostname": "", "asset_version": ASSET_VERSION, "dashboard_version": DASHBOARD_VERSION, "api_version": API_VERSION},
        headers={"Cache-Control": "no-cache"},
    )


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

monitor = Monitor(get_tracking, query_ntp_server, sources=get_sources, clients=get_clients)


# Retire the previous unscoped endpoints; no legacy path may bypass RBAC.
app.router.routes[:] = [route for route in app.router.routes if not getattr(route,"path","").startswith(("/api/","/dashboard/")) and getattr(route,"path","") != "/health"]
import sys
from access_api import install
install(app,sys.modules[__name__])
from fastapi.openapi.utils import get_openapi
def secured_openapi():
    if app.openapi_schema:return app.openapi_schema
    schema=get_openapi(title="TimeBeacon API",version=API_VERSION,description="Role-scoped monitoring API. Authenticate using the sign-in form (session cookie) or a Bearer API key created in User Settings. HTTP Basic is not supported. Both require API Access and each endpoint's view permission. History defaults to 60 minutes; from/to accept Unix seconds or ISO 8601 dates with timezone. Page arrays using X-Next-After and the returned X-History-From/To headers. CPU/RAM/disk are percent; offset and RTT values are milliseconds. Only /health is public.",routes=app.routes)
    schema.setdefault("components",{})["securitySchemes"]={"UserSession":{"type":"apiKey","in":"cookie","name":"timebeacon_session"},"UserAPIKey":{"type":"http","scheme":"bearer"}}
    for path,operations in schema["paths"].items():
        for operation in operations.values():
            if path!="/health":operation["security"]=[{"UserSession":[]},{"UserAPIKey":[]}]
    app.openapi_schema=schema;return schema
app.openapi=secured_openapi


@app.middleware("http")
async def private_responses(request,call_next):
    if request.url.path in ("/docs","/redoc","/openapi.json"):
        from security import IdentityStore
        from fastapi.responses import JSONResponse
        try:
            IdentityStore(monitor).authenticate(request,api=True)
        except HTTPException as error:
            return JSONResponse({"detail":error.detail},status_code=error.status_code,headers={**(error.headers or {}),"Cache-Control":"no-store"})
    response=await call_next(request)
    if not request.url.path.startswith("/static/"):
        response.headers["Cache-Control"]="no-store"
    return response

from account_api import install as install_accounts
install_accounts(app, sys.modules[__name__])
from service_repairs import install as install_service_repairs
install_service_repairs(app, sys.modules[__name__])
from client_settings import install as install_client_settings
install_client_settings(app, sys.modules[__name__])

@app.get('/login', include_in_schema=False)
@app.get('/admin', include_in_schema=False)
@app.get('/admin/users', include_in_schema=False)
@app.get('/admin/roles', include_in_schema=False)
@app.get('/admin/services', include_in_schema=False)
@app.get('/admin/clients', include_in_schema=False)
@app.get('/user-settings', include_in_schema=False)
def account_page(request: Request):
    from security import IdentityStore
    from fastapi.responses import RedirectResponse
    page = request.url.path
    if page != '/login':
        try:
            user = IdentityStore(monitor).authenticate(request)
        except HTTPException:
            return RedirectResponse('/login', status_code=303)
        if page.startswith('/admin'):
            IdentityStore.require(user, 'admin')
    return templates.TemplateResponse(request=request, name='account.html', context={
        'page':page, 'asset_version':ASSET_VERSION, 'dashboard_version':DASHBOARD_VERSION,
        'api_version':API_VERSION})
