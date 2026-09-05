"""Validated administration settings for client thresholds and appearance."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from fastapi import Request, HTTPException
from security import IdentityStore

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
            not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@:-]*\.service", unit)
            or len(unit) > 200
            for unit in self.services
        ):
            raise ValueError("Enter systemd .service names")
        return self


def install(app, backend):
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
