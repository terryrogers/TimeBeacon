"""Validated administration settings for client thresholds and appearance."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from fastapi import Request, HTTPException
from security import IdentityStore
import subprocess
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_CLOCKS = [
    {'name': 'Los Angeles', 'zone': 'America/Los_Angeles'},
    {'name': 'New York', 'zone': 'America/New_York'},
    {'name': 'London', 'zone': 'Europe/London'},
    {'name': 'Dubai', 'zone': 'Asia/Dubai'},
    {'name': 'Singapore', 'zone': 'Asia/Singapore'},
    {'name': 'Sydney', 'zone': 'Australia/Sydney'},
]

class ClockDefaults(BaseModel):
    version: int
    clocks: list[str] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def valid_clocks(self):
        if len(set(self.clocks)) != 6:
            raise ValueError("Choose six different time zones")
        for zone in self.clocks:
            try:
                ZoneInfo(zone)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Choose a valid time zone")
        return self


def system_services(details=False):
    names = {}
    try:
        for command in ("list-unit-files", "list-units"):
            result = subprocess.run(
                [
                    "/usr/bin/systemctl",
                    command,
                    "--type=service",
                    "--all",
                    "--no-legend",
                    "--no-pager",
                    "--plain",
                    "--full",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.splitlines():
                fields = line.split()
                if fields and re.fullmatch(
                    r"[A-Za-z0-9_][A-Za-z0-9_.@:\\-]*\.service", fields[0]
                ):
                    entry=names.setdefault(fields[0], {'name':fields[0], 'startup':'transient', 'status':'inactive'})
                    if command=='list-unit-files':entry['startup']=fields[1] if len(fields)>1 else 'unknown'
                    else:entry['status']=' / '.join(fields[2:4]) if len(fields)>3 else 'unknown'
    except (OSError, subprocess.SubprocessError):
        raise HTTPException(
            503, "Unable to load system services. Reload and try again."
        )
    ordered=sorted(names,key=str.casefold)
    return [names[name] for name in ordered] if details else ordered


DEFAULT_COLOURS = {
    "mode": "light",
    "healthy": {"background": "#d9f2e6", "foreground": "#155b3c"},
    "warning": {"background": "#fff1c2", "foreground": "#634500"},
    "critical": {"background": "#fce0e4", "foreground": "#851b2a"},
    "unknown": {"background": "#e7ebf0", "foreground": "#39465a"},
}


class Colours(BaseModel):
    background: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    foreground: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class Palette(BaseModel):
    mode: Literal["light", "dark"]
    healthy: Colours
    warning: Colours
    critical: Colours
    unknown: Colours


class ClientSettings(BaseModel):
    warning_seconds: int = Field(ge=1, le=31536000)
    critical_seconds: int = Field(ge=2, le=31536000)
    warning_drops: int = Field(ge=1)
    critical_drops: int = Field(ge=2)
    client_colours: Palette

    @model_validator(mode="after")
    def thresholds(self):
        if (
            self.warning_seconds >= self.critical_seconds
            or self.warning_drops >= self.critical_drops
        ):
            raise ValueError("Warning threshold must be below critical threshold")
        return self


class Services(BaseModel):
    services: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def units(self):
        import re
        if any(
            not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@:\\-]*\.service", unit)
            or len(unit) > 200
            for unit in self.services
        ):
            raise ValueError("Enter systemd .service names")
        return self


def install(app, backend):
    @app.get("/administration/defaults", include_in_schema=False)
    def defaults(request: Request):
        store = IdentityStore(backend.monitor)
        store.require(store.authenticate(request), "admin")
        result = backend.monitor.get_settings()
        return {"version": result["version"], "clocks": result["settings"].get("default_clocks", DEFAULT_CLOCKS)}

    @app.put("/administration/defaults", include_in_schema=False)
    def save_defaults(request: Request, body: ClockDefaults):
        store = IdentityStore(backend.monitor)
        store.require(store.authenticate(request), "admin")
        store.same_origin(request)
        clocks = [{"zone": zone, "name": zone.split("/")[-1].replace("_", " ")} for zone in body.clocks]
        result = backend.monitor.save_settings(body.version, {"default_clocks": clocks})
        if result is None:
            raise HTTPException(409, "Defaults changed. Reload and retry.")
        return {"version": result["version"], "clocks": clocks}

    @app.get("/administration/services", include_in_schema=False)
    def inventory(request: Request):
        store = IdentityStore(backend.monitor)
        store.require(store.authenticate(request), "admin")
        from telemetry import REQUIRED_SERVICES

        inventory=system_services(details=True)
        inventory=[row if isinstance(row,dict) else {'name':row,'startup':'unknown','status':'unknown'} for row in inventory]
        return {
            "services": [row['name'] for row in inventory],
            "details": inventory,
            "monitored": backend.monitor.get_settings()["settings"].get(
                "services", list(REQUIRED_SERVICES)
            ),
        }

    def save(request, values):
        store = IdentityStore(backend.monitor)
        store.require(store.authenticate(request), "admin")
        store.same_origin(request)
        settings = backend.monitor.get_settings()
        if backend.monitor.save_settings(settings["version"], values) is None:
            raise HTTPException(409, "Configuration changed. Reload and retry.")
        return {"success": True, "message": "Configuration saved."}

    @app.put("/administration/clients", include_in_schema=False)
    def clients(request: Request, body: ClientSettings):
        return save(request, body.model_dump())

    @app.put("/administration/services", include_in_schema=False)
    def services(request: Request, body: Services):
        return save(request, {"services": list(dict.fromkeys(body.services))})
