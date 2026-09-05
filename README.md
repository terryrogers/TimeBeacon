# TimeBeacon

Precision-time monitoring for Linux NTP/Chrony servers: system metrics, service health, GPS/PPS reception, time acquisition, time clients and personal world clocks.

Dashboard **5.0.0** · API **4.0.0** · Copyright (c) 2026 Terry Rogers · MIT License.

## Setup

Install requirements.txt in a Python virtual environment and run `uvicorn main:app --host 127.0.0.1 --port 8080` behind an HTTPS reverse proxy. Browser sessions use Secure, HttpOnly, SameSite cookies and require HTTPS. The Linux collector uses chronyc, gpspipe, nslookup, systemd and psutil. Service queries only read state; changing the health-check list never starts or stops services.

On a new identity database, the requested bootstrap account is admin with password admin. Change its password in User Settings. New account passwords must contain at least eight characters. Passwords are salted PBKDF2 hashes; API keys and session tokens are stored as hashes. Password changes revoke that user's sessions and API keys.

SQLite defaults to data/history.sqlite3; NTP_DASHBOARD_HISTORY_DB can override it. Back up SQLite using its online backup interface. Raw samples are retained indefinitely. Upgrades migrate existing shared world clocks into the initial administrator's personal settings; new users start with no clocks. Existing daylight locations are copied into each account during upgrade; subsequent location changes are personal. Health checks and client thresholds remain administration settings.

## Access control

Administration creates/updates users and roles, assigns multiple roles to users, disables accounts, resets passwords, and configures health checks and client thresholds. Permissions are the union of the user's roles and are evaluated on each request. At least one enabled administrator must remain. User Settings manages name, email, profile photo (Gravatar by default), daylight location, personal clocks, password, authenticator registration and API keys. Keys inherit current account permissions and can be revoked individually.

The built-in User role grants dashboard, server/time status and history, world-clock viewing and time-client summaries. It cannot access Administration, individual clients, clock amendments or the API unless a configured role grants those permissions. Controls are hidden in the UI and the server independently denies unauthorized requests.

## API

See [API reference](docs/API.md) and the instance's /docs OpenAPI interface. Sign in through the dedicated form or authenticate API requests with a Bearer API key created in User Settings. HTTP Basic authentication is rejected. Unauthenticated page requests redirect to the sign-in page without returning dashboard markup. Every protected API endpoint requires API Access plus its listed view/amend permission. The old environment-token authentication and /api/* endpoints are retired. Only /health exposes unauthenticated monitoring data; /docs and /openapi.json also require API Access.

History defaults to the last 60 minutes. Dates accept Unix seconds or ISO 8601 with an explicit timezone. API arrays contain original samples with bounded pagination; graph displays select representative samples for long periods. Null values and gaps represent unavailable measurements.

## Appearance and account security

Semantic UI 2.5.0 styles and icon fonts are bundled locally under `static/vendor/semantic` with their MIT license. Daylight and Midnight themes follow each signed-in user's sunrise and sunset. The anonymous sign-in page uses the browser's colour preference. Administration has dedicated overview, user directory, role and service-health pages. Dialog titles and status bars remain outside their scrolling content area.

Profile photos accept an HTTPS image URL; leaving it empty uses the email's SHA-256 Gravatar URL. Gravatar loads in the browser. Get my location requests browser permission, reverse-geocodes rounded coordinates using OpenStreetMap Nominatim, and stores the nearest town/city and coordinates in that user's SQLite settings. Coordinates are not displayed as editable fields. Geocoding is cached for 30 days and rate-limited across workers.

Two-factor registration uses a locally generated QR code and TOTP-compatible authenticator apps. Setup must be confirmed before activation. Eight single-use recovery codes are displayed once; only hashes are retained. Login is throttled and accepted TOTP steps cannot be reused. Secrets are encrypted with a generated `identity.key` alongside the SQLite database. **Back up this key together with the database** and protect both; losing the key prevents verification of registered authenticators. Account passwords, API keys and QR secrets must never be committed. Existing accounts and historic samples are preserved by additive migrations.

## Development

Run `python -m pytest -q`. Tests require pytest, Playwright with Edge, httpx and runtime dependencies. Version constants are in version.py; changes are recorded in CHANGELOG.md. Source control excludes databases, credentials, local deployment records and generated test evidence. Local tests, deployed service checks and user acceptance are separate verification stages.
