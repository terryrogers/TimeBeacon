"""Permission-scoped dashboard, administration and version 3 API routes."""

import asyncio
import json
import math
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, ConfigDict
from security import IdentityStore, PERMISSIONS, digest, password_hash, password_ok
from telemetry import REQUIRED_SERVICES, solar_status
from account_api import ProfileInput, profile
from server_info import system_information


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)

    code: str = Field(default="", max_length=80)


class RoleInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    permissions: list[str]


class UserInput(ProfileInput):
    id: int | None = None
    username: str = Field(pattern=r"^[A-Za-z0-9_.@-]{1,80}$")
    password: str | None = Field(default=None, min_length=8, max_length=256)
    roles: list[str] = Field(max_length=32)
    enabled: bool = True


class PasswordInput(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=256)


class KeyInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ClockInput(BaseModel):
    timezone_name: str

    @field_validator("timezone_name")
    @classmethod
    def valid(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown timezone")
        return value


class ConfigInput(BaseModel):
    services: list[str] = Field(min_length=1, max_length=100)
    warning_seconds: int = Field(ge=1, le=31536000)
    critical_seconds: int = Field(ge=2, le=31536000)
    warning_drops: int = Field(default=1, ge=1)
    critical_drops: int = Field(default=10, ge=2)

    @field_validator("services")
    @classmethod
    def units(cls, values):
        if any(not re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service", v) for v in values):
            raise ValueError("Enter systemd .service names")
        return list(dict.fromkeys(values))


class Preferences(BaseModel):
    version: int
    clocks: list[dict] = Field(max_length=64)


SERVER_METRICS = {"cpu", "ram", "storage", "storage_used", "temperature", "uptime"}
TIME_METRICS = {"stratum", "last_offset", "rms_offset", "ntp_rtt"}
GPS_METRICS = {"gps_used", "gps_visible", "gps_mode", "gps_pps", "gps_hdop", "gps_tdop"}


def period(start, end):
    def parse(value):
        if value is None:
            return None
        try:
            if str(value).isdigit():
                return int(value)
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                raise ValueError()
            return int(dt.timestamp())
        except (ValueError, OverflowError):
            raise HTTPException(
                422, "Dates must be Unix seconds or ISO 8601 with timezone"
            )

    end = parse(end) if end is not None else int(time.time())
    start = parse(start) if start is not None else max(0, end - 3600)
    if start < 0 or start >= end:
        raise HTTPException(422, "From must precede to")
    return start, end


def install(app, backend):
    def store():
        return IdentityStore(backend.monitor)

    def who(request, *permissions, api=False):
        user = store().authenticate(request, api)
        store().require(user, *permissions)
        return user

    def current():
        return backend.monitor.latest()

    def config():
        result = backend.monitor.get_settings()["settings"].copy()
        result.setdefault("services", list(REQUIRED_SERVICES))
        result.setdefault("warning_seconds", 300)
        result.setdefault("critical_seconds", 900)
        result.setdefault("warning_drops", 1)
        result.setdefault("critical_drops", 10)
        result.pop("clocks", None)
        return result

    def summary(clients):
        settings = config()
        counts = {
            "total_clients_seen": len(clients),
            "total_healthy": 0,
            "total_warning": 0,
            "total_critical": 0,
            "total_unknown": 0,
        }
        for client in clients:
            try:
                raw = str(client.get("Last", "")).strip().lower()
                match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([a-z]*)", raw)
                assert match
                unit = match[2]
                scale = (
                    1
                    if unit in ("", "s", "sec", "secs", "second", "seconds")
                    else (
                        60
                        if unit in ("m", "min", "mins", "minute", "minutes")
                        else (
                            3600
                            if unit in ("h", "hr", "hrs", "hour", "hours")
                            else 86400 if unit in ("d", "day", "days") else None
                        )
                    )
                )
                assert scale is not None
                age = float(match[1]) * scale
                drop = float(client.get("Drop", ""))
                assert (
                    math.isfinite(age)
                    and age >= 0
                    and math.isfinite(drop)
                    and drop >= 0
                )
            except (ValueError, TypeError, AssertionError):
                state = "unknown"
            else:
                state = (
                    "critical"
                    if age >= settings["critical_seconds"]
                    or drop >= settings["critical_drops"]
                    else (
                        "warning"
                        if age >= settings["warning_seconds"]
                        or drop >= settings["warning_drops"]
                        else "healthy"
                    )
                )
            counts["total_" + state] += 1
        return counts

    def clock_settings(user):
        c = config()
        return {
            "version": user["version"],
            "config_version": backend.monitor.get_settings()["version"],
            "settings": {
                **user["location"],
                "clocks": (
                    user["clocks"]
                    if "clocks.view" in user["permissions"]
                    or "clocks.amend" in user["permissions"]
                    else []
                ),
            },
        }

    def filtered_status(user):
        data = current()
        out = {k: data.get(k) for k in ("healthy", "stale", "timestamp", "hostname")}
        out["metrics"] = {}
        out["checks"] = {}
        if "server.view" in user["permissions"]:
            out["system_information"] = system_information()
            out.update(
                {
                    k: data.get(k)
                    for k in ("services", "checks", "errors", "failed_services")
                }
            )
            out["metrics"].update(
                {
                    k: v
                    for k, v in data.get("metrics", {}).items()
                    if k in SERVER_METRICS
                }
            )
        if "time.view" in user["permissions"]:
            out.update(
                {
                    k: data.get(k)
                    for k in ("time_daemon", "gps", "acquisition", "tracking")
                }
            )
            out["metrics"].update(
                {k: v for k, v in data.get("metrics", {}).items() if k in TIME_METRICS}
            )
        return out

    @app.post("/auth/login", include_in_schema=False)
    def login(request: Request, body: Login):
        store().same_origin(request)
        user = store().credential(
            body.username,
            body.password,
            request.client.host if request.client else "unknown",
            body.code,
        )
        token = secrets.token_urlsafe(32)
        with backend.monitor.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?)",
                (digest(token), user["id"], int(time.time()) + 28800),
            )
        response = JSONResponse({"success": True})
        response.set_cookie(
            "timebeacon_session",
            token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=28800,
            path="/",
        )
        return response

    @app.post("/auth/logout", include_in_schema=False)
    def logout(request: Request):
        store().same_origin(request)
        with backend.monitor.connect() as db:
            db.execute(
                "DELETE FROM sessions WHERE token=?",
                (digest(request.cookies.get("timebeacon_session", "")),),
            )
        response = JSONResponse({"success": True})
        response.delete_cookie("timebeacon_session")
        return response

    @app.get("/auth/me", include_in_schema=False)
    def me(request: Request):
        user = who(request)
        return {k: user[k] for k in ("id", "username", "roles", "permissions")}

    @app.post("/user/password", include_in_schema=False)
    def change_password(request: Request, body: PasswordInput):
        user = who(request)
        store().mutation(request)
        with backend.monitor.connect() as db:
            hashed = db.execute(
                "SELECT password FROM users WHERE id=?", (user["id"],)
            ).fetchone()[0]
            if not password_ok(body.current_password, hashed):
                raise HTTPException(403, "Current password incorrect")
            db.execute(
                "UPDATE users SET password=? WHERE id=?",
                (password_hash(body.new_password), user["id"]),
            )
            db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
            db.execute("DELETE FROM api_keys WHERE user_id=?", (user["id"],))
        return {
            "success": True,
            "message": "Password changed. Sign in again. Existing sessions and API keys revoked.",
        }

    @app.get("/user/keys", include_in_schema=False)
    def keys(request: Request):
        user = who(request, "api.view")
        with backend.monitor.connect() as db:
            return [
                dict(zip(("id", "name", "created"), row))
                for row in db.execute(
                    "SELECT id,name,created FROM api_keys WHERE user_id=?",
                    (user["id"],),
                )
            ]

    @app.post("/user/keys", include_in_schema=False)
    def create_key(request: Request, body: KeyInput):
        user = who(request, "api.view")
        store().mutation(request)
        token = secrets.token_urlsafe(40)
        with backend.monitor.connect() as db:
            if (
                db.execute(
                    "SELECT COUNT(*) FROM api_keys WHERE user_id=?", (user["id"],)
                ).fetchone()[0]
                >= 20
            ):
                raise HTTPException(422, "Maximum 20 API keys")
            db.execute(
                "INSERT INTO api_keys(user_id,name,token,created) VALUES (?,?,?,?)",
                (user["id"], body.name, digest(token), int(time.time())),
            )
        return {"key": token, "message": "Copy now. This key is shown only once."}

    @app.delete("/user/keys/{key_id}", include_in_schema=False)
    def revoke_key(request: Request, key_id: int):
        user = who(request, "api.view")
        store().mutation(request)
        with backend.monitor.connect() as db:
            db.execute(
                "DELETE FROM api_keys WHERE id=? AND user_id=?", (key_id, user["id"])
            )
        return {"success": True}

    @app.get("/administration", include_in_schema=False)
    def administration(request: Request):
        who(request, "admin")
        with backend.monitor.connect() as db:
            users = [
                {
                    "id": r[0],
                    "username": r[1],
                    "roles": json.loads(r[2]),
                    "enabled": bool(r[3]),
                    **profile(db, r[0]),
                }
                for r in db.execute("SELECT id,username,roles,enabled FROM users")
            ]
            roles = [
                {"name": r[0], "permissions": json.loads(r[1])}
                for r in db.execute("SELECT name,permissions FROM roles")
            ]
        return {
            "users": users,
            "roles": roles,
            "permissions": PERMISSIONS,
            "config": config(),
        }

    @app.put("/administration/roles", include_in_schema=False)
    def save_role(request: Request, body: RoleInput):
        who(request, "admin")
        store().mutation(request)
        if body.name == "Administrator":
            raise HTTPException(
                422, "The built-in Administrator role cannot be changed"
            )
        if set(body.permissions) - PERMISSIONS.keys():
            raise HTTPException(422, "Unknown permission")
        with backend.monitor.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT OR REPLACE INTO roles VALUES (?,?)",
                (body.name, json.dumps(sorted(set(body.permissions)))),
            )
            store().keep_admin(db)
        return {"success": True}

    @app.put("/administration/users", include_in_schema=False)
    def save_user(request: Request, body: UserInput):
        who(request, "admin")
        store().mutation(request)
        with backend.monitor.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            known = {r[0] for r in db.execute("SELECT name FROM roles")}
            if set(body.roles) - known:
                raise HTTPException(422, "Unknown role")
            duplicate = db.execute(
                "SELECT id FROM users WHERE username=?", (body.username,)
            ).fetchone()
            if duplicate and duplicate[0] != body.id:
                raise HTTPException(409, "Username already exists")
            if body.id is None:
                if not body.password:
                    raise HTTPException(422, "A password is required for a new account")
                db.execute(
                    "INSERT INTO users(username,password,roles,enabled,clocks) VALUES (?,?,?,?,?)",
                    (
                        body.username,
                        password_hash(body.password),
                        json.dumps(body.roles),
                        body.enabled,
                        "[]",
                    ),
                )
            else:
                if not db.execute(
                    "SELECT id FROM users WHERE id=?", (body.id,)
                ).fetchone():
                    raise HTTPException(404, "User not found")
                db.execute(
                    "UPDATE users SET username=?,roles=?,enabled=? WHERE id=?",
                    (body.username, json.dumps(body.roles), body.enabled, body.id),
                )
                if body.password:
                    db.execute(
                        "UPDATE users SET password=? WHERE id=?",
                        (password_hash(body.password), body.id),
                    )
                    db.execute("DELETE FROM sessions WHERE user_id=?", (body.id,))
                    db.execute("DELETE FROM api_keys WHERE user_id=?", (body.id,))
            user_id = (
                body.id
                or db.execute(
                    "SELECT id FROM users WHERE username=?", (body.username,)
                ).fetchone()[0]
            )
            db.execute(
                "UPDATE users SET name=?,email=?,photo=? WHERE id=?",
                (body.name, body.email, body.photo, user_id),
            )
            if body.id is None:
                db.execute(
                    "UPDATE users SET location=? WHERE id=?",
                    (
                        json.dumps(
                            dict(location="London", latitude=51.5074, longitude=-0.1278)
                        ),
                        user_id,
                    ),
                )
            store().keep_admin(db)
        return {"success": True}

    @app.put("/administration/config", include_in_schema=False)
    def save_config(request: Request, body: ConfigInput):
        who(request, "admin")
        store().mutation(request)
        if (
            body.warning_seconds >= body.critical_seconds
            or body.warning_drops >= body.critical_drops
        ):
            raise HTTPException(
                422, "Warning threshold must be below critical threshold"
            )
        settings = backend.monitor.get_settings()
        saved = backend.monitor.save_settings(settings["version"], body.model_dump())
        if saved is None:
            raise HTTPException(409, "Configuration changed. Reload and retry.")
        return {
            "success": True,
            "message": "Health service selection takes effect on the next collection cycle.",
        }

    @app.get("/dashboard/settings", include_in_schema=False)
    def settings(request: Request):
        return clock_settings(who(request))

    @app.patch("/dashboard/settings", include_in_schema=False)
    def save_preferences(request: Request, body: Preferences):
        user = who(request, "clocks.amend")
        store().mutation(request)
        clocks = []
        for c in body.clocks:
            try:
                zone = ClockInput(timezone_name=c.get("zone", "")).timezone_name
            except ValueError:
                raise HTTPException(422, "Unknown timezone")
            if any(x["zone"] == zone for x in clocks):
                raise HTTPException(422, "Duplicate clock")
            clocks.append({"zone": zone, "name": zone.split("/")[-1].replace("_", " ")})
        return clock_settings(store().save_clocks(user, clocks, body.version))

    @app.get("/dashboard/status", include_in_schema=False)
    def status(request: Request):
        return filtered_status(who(request, "dashboard.view"))

    @app.get("/dashboard/solar", include_in_schema=False)
    def solar(request: Request):
        c = who(request)["location"]
        return solar_status(latitude=c["latitude"], longitude=c["longitude"])

    @app.get("/dashboard/time", include_in_schema=False)
    def ntp_time(request: Request):
        user = who(request, "dashboard.view")
        if not set(user["permissions"]) & {"time.view", "clocks.view", "clocks.amend"}:
            raise HTTPException(403, "Permission denied")
        try:
            data = backend.query_ntp_server()
        except Exception:
            raise HTTPException(503, "NTP time unavailable")
        return {
            "status": "ok",
            "timestamp": data["timestamp"],
            **(
                {"round_trip_ms": data.get("round_trip_ms")}
                if "time.view" in user["permissions"]
                else {}
            ),
        }

    @app.get("/dashboard/tracking", include_in_schema=False)
    def tracking(request: Request):
        who(request, "dashboard.view", "time.view")
        return {"status": "ok", "tracking": current().get("tracking", {})}

    @app.get("/dashboard/clients", include_in_schema=False)
    def clients(request: Request):
        user = who(request, "dashboard.view")
        data = current().get("clients", [])
        out = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thresholds": {
                k: config()[k]
                for k in (
                    "warning_seconds",
                    "critical_seconds",
                    "warning_drops",
                    "critical_drops",
                )
            },
        }
        if "clients.summary" in user["permissions"]:
            out["summary"] = summary(data)
        if "clients.view" in user["permissions"]:
            out["clients"] = data
        return out

    @app.get("/dashboard/history", include_in_schema=False)
    def history(
        request: Request, metric: str, start: int | None = None, end: int | None = None
    ):
        user = who(request, "dashboard.view")
        permission = "server.history" if metric in SERVER_METRICS else "time.history"
        if metric not in SERVER_METRICS | TIME_METRICS | GPS_METRICS:
            raise HTTPException(422, "Unknown metric")
        store().require(
            user, permission, "server.view" if metric in SERVER_METRICS else "time.view"
        )
        start, end = period(start, end)
        samples = backend.monitor.history(start, end)
        out = []
        for s in samples:
            point = {
                "timestamp": s["timestamp"],
                "metrics": {metric: s.get("metrics", {}).get(metric)},
            }
            if metric in TIME_METRICS | GPS_METRICS:
                point.update({k: s.get(k, {}) for k in ("gps", "acquisition")})
            out.append(point)
        return {"samples": out, "bounds": backend.monitor.history_bounds()}

    @app.get("/health", tags=["Health"])
    def health():
        return {
            "status": "healthy" if current().get("healthy") else "unhealthy",
            "details": "/health/details",
        }

    @app.get("/health/details", tags=["Health"])
    def health_details(request: Request):
        who(request, "server.view", api=True)
        return [
            {
                "name": s["name"],
                "startup": s.get("startup"),
                "status": s.get("status"),
                "cpu": s.get("cpu"),
                "ram": s.get("ram"),
            }
            for s in current().get("services", [])
        ]

    @app.get("/server/status", tags=["Server"])
    def server_status(request: Request):
        who(request, "server.view", api=True)
        m = current().get("metrics", {})
        used = m.get("storage_used")
        return {
            "cpu_percent": m.get("cpu"),
            "system_information": system_information(),
            "ram_percent": m.get("ram"),
            "disk_used": {
                "percent": m.get("storage"),
                "bytes": used,
                "gb": round(used / 1e9, 2) if used is not None else None,
                "friendly": f"{used/1e9:.2f} GB" if used is not None else None,
            },
            "cpu_temperature_c": m.get("temperature"),
            "uptime_seconds": m.get("uptime"),
        }

    def metric_history(
        request, metric, from_date, to_date, allowed, permission, after, limit
    ):
        who(request, permission, permission.replace(".history", ".view"), api=True)
        if metric not in allowed:
            raise HTTPException(422, "Unsupported metric")
        start, end = period(from_date, to_date)
        result = backend.monitor.export_history(start, end, after, limit)
        response = JSONResponse(
            [
                {"timestamp": s["timestamp"], "value": s.get("metrics", {}).get(metric)}
                for s in result["samples"]
            ]
        )
        response.headers["X-History-From"] = str(start)
        response.headers["X-History-To"] = str(end)
        if result["next_after"] is not None:
            response.headers["X-Next-After"] = str(result["next_after"])
        return response

    @app.get("/server/status/history", tags=["Server"])
    def server_history(
        request: Request,
        parameter: Literal[
            "cpu", "ram", "storage", "storage_used", "temperature", "uptime"
        ],
        from_date: str | None = Query(None, alias="from"),
        to_date: str | None = Query(None, alias="to"),
        after: int = Query(-1, ge=-1),
        limit: int = Query(1000, ge=1, le=5000),
    ):
        return metric_history(
            request,
            parameter,
            from_date,
            to_date,
            SERVER_METRICS,
            "server.history",
            after,
            limit,
        )

    @app.get("/time/history", tags=["Time"])
    def time_history(
        request: Request,
        parameter: Literal["stratum", "last_offset", "rms_offset", "ntp_rtt"],
        from_date: str | None = Query(None, alias="from"),
        to_date: str | None = Query(None, alias="to"),
        after: int = Query(-1, ge=-1),
        limit: int = Query(1000, ge=1, le=5000),
    ):
        return metric_history(
            request,
            parameter,
            from_date,
            to_date,
            TIME_METRICS,
            "time.history",
            after,
            limit,
        )

    @app.get("/time/status", tags=["Time"])
    def time_status(request: Request):
        who(request, "time.view", api=True)
        s = current()
        m = s.get("metrics", {})
        t = s.get("tracking", {})
        g = s.get("gps", {})
        return {
            **{k: m.get(k) for k in TIME_METRICS},
            "reference": t.get("Reference ID"),
            "leap_status": t.get("Leap status"),
            "gps_fix": g.get("fix"),
            "satellites": {"used": g.get("used"), "visible": g.get("visible")},
            "pps": g.get("pps"),
            "time_acquisition": s.get("acquisition", {}).get("selected"),
        }

    @app.get("/time/gps", tags=["Time"])
    def gps(request: Request):
        who(request, "time.view", api=True)
        g = current().get("gps", {}).get("fix_details", {})
        return {
            name: g.get(key)
            for name, key in [
                ("time_utc", "time"),
                ("fix_mode", "mode"),
                ("horizontal_error_m", "eph"),
                ("vertical_error_m", "epv"),
                ("time_error_s", "ept"),
            ]
        }

    @app.get("/time/satellites", tags=["Time"])
    def satellites(request: Request):
        who(request, "time.view", api=True)
        return [
            {
                "id": s.get("svid", s.get("PRN")),
                "gnss_id": s.get("gnssid"),
                "elevation": s.get("el"),
                "azimuth": s.get("az"),
                "signal_strength": s.get("ss"),
                "used_in_fix": s.get("used"),
            }
            for s in current().get("gps", {}).get("satellites", [])
        ]

    @app.get("/time/pps", tags=["Time"])
    def pps(request: Request):
        who(request, "time.view", api=True)
        s = current().get("gps", {}).get("pps_details", {})
        return {
            k: s.get(k)
            for k in ("real_sec", "real_nsec", "clock_sec", "clock_nsec", "precision")
        }

    def sources_data():
        return [
            {
                k: s.get(k)
                for k in (
                    "name",
                    "state",
                    "stratum",
                    "reach",
                    "last_rx",
                    "measured_offset",
                )
            }
            for s in current().get("acquisition", {}).get("sources", [])
        ]

    @app.get("/time/sources", tags=["Time"])
    def sources(request: Request):
        who(request, "time.view", api=True)
        return sources_data()

    @app.get("/time/acquisition", tags=["Time"])
    def acquisition(request: Request):
        who(request, "time.view", api=True)
        return next((s for s in sources_data() if s["state"] == "*"), None)

    @app.get("/clocks", tags=["Clocks"])
    def clocks(request: Request):
        user = who(request, "clocks.view", api=True)
        try:
            stamp = backend.query_ntp_server()["timestamp"]
        except Exception:
            raise HTTPException(503, "NTP time unavailable")
        result = []
        for c in user["clocks"]:
            dt = datetime.fromtimestamp(stamp, ZoneInfo(c["zone"]))
            offset = dt.strftime("%z")
            result.append(
                {
                    "name": c["name"],
                    "city": c["zone"].split("/")[-1].replace("_", " "),
                    "timezone_name": c["zone"],
                    "time": dt.strftime("%H:%M:%S"),
                    "date": dt.date().isoformat(),
                    "utc": "UTC " + offset[:3] + ":" + offset[3:],
                }
            )
        return result

    @app.post("/clocks/add", tags=["Clocks"])
    def add_clock(request: Request, body: ClockInput):
        user = who(request, "clocks.amend", api=True)
        store().mutation(request)
        if any(c["zone"] == body.timezone_name for c in user["clocks"]):
            return {"success": False, "message": "Clock already exists"}
        if len(user["clocks"]) >= 64:
            raise HTTPException(422, "Maximum 64 clocks")
        store().save_clocks(
            user,
            user["clocks"]
            + [
                {
                    "zone": body.timezone_name,
                    "name": body.timezone_name.split("/")[-1].replace("_", " "),
                }
            ],
            user["version"],
        )
        return {"success": True}

    @app.post("/clocks/remove", tags=["Clocks"])
    def remove_clock(request: Request, body: ClockInput):
        user = who(request, "clocks.amend", api=True)
        store().mutation(request)
        clocks = [c for c in user["clocks"] if c["zone"] != body.timezone_name]
        if len(clocks) == len(user["clocks"]):
            return {"success": False, "message": "Clock not found"}
        store().save_clocks(user, clocks, user["version"])
        return {"success": True}

    @app.get("/time/clients", tags=["Clients"])
    def client_summary(request: Request):
        who(request, "clients.summary", api=True)
        return summary(current().get("clients", []))

    @app.get("/time/clients/details", tags=["Clients"])
    def client_details(request: Request):
        who(request, "clients.view", api=True)
        return [
            {
                "hostname": c.get("hostname"),
                "ip_address": c.get("addr"),
                "ntp_packets": c.get("NTP"),
                "dropped_packets": c.get("Drop"),
                "command_packets": c.get("Cmd"),
                "interval": c.get("Int"),
                "last_seen": c.get("Last"),
            }
            for c in current().get("clients", [])
        ]
