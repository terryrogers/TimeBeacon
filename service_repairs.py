"""Administrator-initiated repair of explicitly monitored systemd services."""

import re
import subprocess
import time
from typing import Literal

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from security import IdentityStore
from telemetry import REQUIRED_SERVICES


class RepairInput(BaseModel):
    unit: str = Field(
        pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.@:-]*\.service$", max_length=200
    )
    action: Literal["start", "remove_check"]
    config_version: int


def inspect_service(unit):
    if (
        not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@:-]*\.service", unit)
        or len(unit) > 200
    ):
        raise HTTPException(422, "Invalid service name")
    try:
        output = subprocess.run(
            [
                "/usr/bin/systemctl",
                "show",
                unit,
                "-p",
                "LoadState,ActiveState,SubState,Result",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    except (OSError, subprocess.SubprocessError):
        raise HTTPException(503, "Unable to inspect this service. Try again later.")


def preview(monitor, unit):
    config = monitor.get_settings()
    if unit not in config["settings"].get("services", REQUIRED_SERVICES):
        raise HTTPException(404, "This service is not included in health monitoring")
    state = inspect_service(unit)
    action, label = None, "No action needed"
    if state.get("ActiveState") == "active":
        message = "This service is already running. Health will refresh on the next collection."
    elif state.get("LoadState") in ("not-found", "masked"):
        action, label = "remove_check", "Remove health check"
        reason = (
            "is not installed"
            if state["LoadState"] == "not-found"
            else "has been deliberately masked"
        )
        message = (
            f"{unit} {reason} and cannot be started. Remove its health check only if this service is no longer required. "
            "This changes monitoring; it does not install, unmask or repair the service itself."
        )
    elif state.get("LoadState") == "loaded" and state.get("ActiveState") in (
        "inactive",
        "failed",
    ):
        action, label = "start", "Start service"
        message = f"Start {unit} and check that it becomes active. Its startup configuration will stay unchanged."
    else:
        message = "This service is changing state or its configuration cannot be loaded. Inspect its configuration before trying again."
    return dict(
        unit=unit,
        action=action,
        label=label,
        message=message,
        state=state.get("ActiveState", "unknown"),
        load_state=state.get("LoadState", "unknown"),
        config_version=config["version"],
    )


def install(app, backend):
    def administrator(request, mutation=False):
        store = IdentityStore(backend.monitor)
        user = store.authenticate(request)
        store.require(user, "admin", "server.view")
        if mutation:
            store.same_origin(request)
        return user

    @app.get("/administration/services/repair", include_in_schema=False)
    def repair_preview(request: Request, unit: str):
        administrator(request)
        return preview(backend.monitor, unit)

    @app.post("/administration/services/repair", include_in_schema=False)
    def repair(request: Request, body: RepairInput):
        user = administrator(request, True)
        proposed = preview(backend.monitor, body.unit)
        if (
            body.action != proposed["action"]
            or body.config_version != proposed["config_version"]
        ):
            raise HTTPException(
                409,
                "Service state or monitoring settings changed. Close this window and review Fix again.",
            )
        with backend.monitor.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute(
                "SELECT max(stamp) FROM service_actions WHERE unit=?", (body.unit,)
            ).fetchone()[0]
            if last and time.time() - last < 20:
                raise HTTPException(
                    429,
                    "A repair was recently requested. Wait 20 seconds before trying again.",
                )
            audit = db.execute(
                "INSERT INTO service_actions(stamp,user_id,unit,action,result) VALUES (?,?,?,?,?)",
                (time.time(), user["id"], body.unit, body.action, "requested"),
            ).lastrowid
        outcome = "failed"
        try:
            if body.action == "remove_check":
                settings = backend.monitor.get_settings()
                services = [
                    s
                    for s in settings["settings"].get("services", REQUIRED_SERVICES)
                    if s != body.unit
                ]
                if not services:
                    raise HTTPException(
                        422,
                        "Keep at least one monitored service. Review Administration first.",
                    )
                if (
                    backend.monitor.save_settings(
                        body.config_version, {"services": services}
                    )
                    is None
                ):
                    raise HTTPException(
                        409, "Monitoring settings changed. Review Fix again."
                    )
                outcome = "removed"
                message = "Health check removed. The status indicator will refresh within 35 seconds."
            else:
                try:
                    # An argv list and a validated, selected unit: never accept shell commands.
                    subprocess.run(
                        ["sudo", "-n", "/usr/bin/systemctl", "start", body.unit],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                except subprocess.TimeoutExpired:
                    outcome = "pending"
                    return {
                        "success": False,
                        "message": "The start request is taking longer than expected. Check the service status before retrying.",
                    }
                except (OSError, subprocess.CalledProcessError):
                    raise HTTPException(
                        503,
                        "The service could not be started. Check its configuration or service-control permissions.",
                    )
                active = inspect_service(body.unit).get("ActiveState") == "active"
                if not active:
                    raise HTTPException(
                        503,
                        "The service did not remain active. Check its configuration before retrying.",
                    )
                outcome = "started"
                message = "Service started. The status indicator will refresh within 35 seconds."
            try:
                fresh = backend.monitor.sample()
                service = next(
                    (s for s in fresh.get("services", []) if s["name"] == body.unit),
                    None,
                )
                resolved = (
                    service is None
                    if body.action == "remove_check"
                    else bool(service and service.get("running"))
                )
                healthy = bool(fresh.get("healthy"))
                remaining = [
                    name.replace("_", " ")
                    for name, ok in fresh.get("checks", {}).items()
                    if not ok
                ]
                message = (
                    "Health check removed."
                    if body.action == "remove_check"
                    else "Service started."
                )
                message += (
                    " Verified: the service issue is resolved."
                    if resolved
                    else " Verification: the service still needs attention."
                )
                message += (
                    " Server health is healthy."
                    if healthy
                    else " Server health remains degraded"
                    + (": " + ", ".join(remaining) if remaining else "")
                    + "."
                )
                return {
                    "success": True,
                    "resolved": resolved,
                    "healthy": healthy,
                    "timestamp": fresh["timestamp"],
                    "message": message,
                }
            except Exception:
                return {
                    "success": True,
                    "resolved": None,
                    "healthy": None,
                    "message": "The service action completed, but a fresh health check could not be collected. Resolution is not yet confirmed; review the service status.",
                }
        finally:
            with backend.monitor.connect() as db:
                db.execute(
                    "UPDATE service_actions SET result=? WHERE id=?", (outcome, audit)
                )
