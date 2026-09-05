# TimeBeacon

Precision-time monitoring dashboard for Linux NTP/Chrony servers with GPSD reception, PPS, service health, system metrics, time clients and world clocks.

Dashboard 3.0.0 · API 2.1.0 · Copyright (c) 2026 Terry Rogers · MIT License.

## Run

Install requirements.txt in a Python virtual environment. Set NTP_DASHBOARD_API_TOKEN using a protected environment file, then run `uvicorn main:app --host 127.0.0.1 --port 8080`. The Linux collector uses chronyc, gpspipe, nslookup, systemd and psutil. Configure narrowly scoped sudo access for service inspection where necessary. Never expose an API token in source control.

SQLite defaults to data/history.sqlite3; NTP_DASHBOARD_HISTORY_DB can override it. Back up the database with SQLite online backup. Raw history is retained indefinitely, so monitor disk capacity. Settings are shared across browsers.

## API

Interactive OpenAPI documentation is at /docs. Existing /api/time and /api/chrony/* routes remain available. API requests require the configured Bearer token.

- GET /api/dashboard: all current status, GPS/satellites/PPS/acquisition, services, clients, NTP time, shared settings and solar state.
- GET /api/history: original collected samples, defaulting to the last 60 minutes. Optional start/end are Unix timestamps in seconds. start=0 selects all stored time. limit defaults to 1000, maximum 5000. Follow next_after as after, preserving returned start/end, until next_after is null.

Dashboard graphs use representative samples for long periods; the API history export preserves every original sample. GPS and acquisition fields are available wherever previously collected; older records may omit newer fields. World clock displays are calculated from NTP time and shared timezone settings.

## Development

Run `python -m pytest -q`. Tests require pytest, Playwright with Edge, httpx and the runtime requirements. Version constants are in version.py; changes are recorded in CHANGELOG.md. Deployment and publishing are separate from local test validation.
