# TimeBeacon

Precision-time monitoring for Linux NTP/Chrony servers: system metrics, service health, GPS/PPS reception, time acquisition, time clients and personal world clocks.

Dashboard **5.6.0** · API **4.1.0** · Copyright (c) 2026 Terry Rogers · MIT License.

## Setup

Install requirements.txt in a Python virtual environment and run `uvicorn main:app --host 127.0.0.1 --port 8080` behind an HTTPS reverse proxy. Browser sessions use Secure, HttpOnly, SameSite cookies and require HTTPS. The Linux collector uses chronyc, gpspipe, nslookup, systemd and psutil. Service queries only read state; changing the health-check list never starts or stops services.

On a new identity database, the requested bootstrap account is admin with password admin. Change its password in Settings. New account passwords must contain at least eight characters. Passwords are salted PBKDF2 hashes; API keys and session tokens are stored as hashes. Password changes revoke that user's sessions and API keys.

SQLite defaults to data/history.sqlite3; NTP_DASHBOARD_HISTORY_DB can override it. Back up SQLite using its online backup interface. Raw samples are retained indefinitely. Upgrades migrate existing shared world clocks into the initial administrator's personal settings; new users start with no clocks. Existing daylight locations are copied into each account during upgrade; subsequent location changes are personal. Health checks and client thresholds remain administration settings.

## Access control

Administration creates/updates users and roles, assigns one role per account, disables accounts, resets passwords, and configures health checks and client thresholds. New accounts require Name, Username and Email Address, and Account Enabled is off by default. Selecting another role deselects the previous one. Existing account assignments are preserved until edited; permissions are evaluated on every request and at least one enabled administrator must remain. Settings manages name, email, profile photo (Gravatar by default), daylight location, personal clocks, password, authenticator registration and API keys. Keys inherit current account permissions and can be revoked individually. New keys are copied directly to the clipboard and never rendered in the page. A 30-second countdown precedes conditional clearance: replacement clipboard content is preserved. Keep the page open and allow clipboard access; denied or unfocused access shows a pending status and retries on return. Closing the page prevents its timer from running.

Service Health lists installed service units and loaded/transient services under Available Services, excluding those already selected under Monitored Services. Select one or more entries, use the arrow buttons to move them, then Save Services. This changes health monitoring without starting or stopping services. At least one service must remain monitored. Both lists show startup type and current systemd status in aligned columns. Inventory access requires administrator permission.

The built-in User role grants dashboard, server/time status and history, world-clock viewing and time-client summaries. It cannot access Administration, individual clients, clock amendments or the API unless a configured role grants those permissions. Controls are hidden in the UI and the server independently denies unauthorized requests.

## API

See [API reference](docs/API.md) and the instance's /docs OpenAPI interface. Sign in through the dedicated form or authenticate API requests with a Bearer API key created in Settings. HTTP Basic authentication is rejected. Unauthenticated page requests redirect to the sign-in page without returning dashboard markup. Every protected API endpoint requires API Access plus its listed view/amend permission. The old environment-token authentication and /api/* endpoints are retired. Only /health exposes unauthenticated monitoring data; /docs and /openapi.json also require API Access.

History defaults to the last 60 minutes. Dates accept Unix seconds or ISO 8601 with an explicit timezone. API arrays contain original samples with bounded pagination; graph displays select representative samples for long periods. Null values and gaps represent unavailable measurements.

## Appearance and account security

Semantic UI 2.5.0 styles and icon fonts are bundled locally under `static/vendor/semantic` with their MIT license. Daylight and Midnight themes follow each signed-in user's sunrise and sunset. The anonymous sign-in page uses the browser's colour preference. Administration has dedicated overview, user directory, role and service-health pages. Dialog titles and status bars remain outside their scrolling content area.

Hover over your photo in Settings and select Edit to toggle Gravatar, upload a PNG/JPEG/WebP image, or clear a custom image. Uploads are limited to 4 MB and 16 megapixels, resized to at most 512 pixels, re-encoded as PNG without metadata using Pillow, and stored in the user's SQLite profile. Photo reads require the owning account or administrator permission. Administration → Users → Edit uses the same photo controls for the selected account; photo changes save immediately and do not discard unsaved user details. Save new users before editing their photo. Existing HTTPS photos are preserved until cleared or replaced. When enabled and no custom image is present, Gravatar uses the email's SHA-256 URL and loads in the browser. Get my location requests browser permission, reverse-geocodes rounded coordinates using OpenStreetMap Nominatim, and stores the nearest town/city and coordinates in that user's SQLite settings. Coordinates are not displayed as editable fields. Geocoding is cached for 30 days and rate-limited across workers.

Two-factor registration uses a locally generated QR code and TOTP-compatible authenticator apps. Setup must be confirmed before activation. Eight single-use recovery codes are displayed once; only hashes are retained. Login is throttled and accepted TOTP steps cannot be reused. Secrets are encrypted with a generated `identity.key` alongside the SQLite database. **Back up this key together with the database** and protect both; losing the key prevents verification of registered authenticators. Account passwords, API keys and QR secrets must never be committed. Existing accounts and historic samples are preserved by additive migrations.

## Development

**Administration → Time Clients** contains warning/critical thresholds and Healthy, Warning, Critical and Unknown background/text colours. Choose whether the entered palette is for light or dark mode; the other mode reflects its lightness while preserving hue and saturation. Both summary tiles and individual client headers use the saved global palette. Service selection is managed separately under Service Health.

The clock picker bundles Semantic UI's search dropdown and flags with jQuery 3.7.1, each under its upstream license. Timezone IDs and location descriptions are from the [Thales timezone reference](https://docs.sentinel.thalesgroup.com/softwareandservices/ems/EMSdocs/WSG/Content/TimeZone.htm). Its fixed GMT descriptions are reference labels; actual clock times and UTC offsets continue to follow current IANA timezone and daylight-saving rules. UTC/fixed-offset zones use a globe where there is no associated national flag.

After a service repair, TimeBeacon immediately collects and stores a new health sample and reports both service resolution and overall health. Other failed checks are listed explicitly. If collection fails, resolution is reported as unconfirmed. A short-lived file lock serialises requested and scheduled samples across workers.

Administrators can select **Details → Fix** beside a degraded monitored service. The confirmation window checks current systemd state: it can start a loaded inactive/failed service, or explicitly remove the health check for a missing/masked service that is no longer required. Removing a check changes monitoring, not the service. Startup configuration is unchanged. Actions are audited in SQLite and rate-limited per service; service starts require the application account's existing non-interactive sudo permission for `systemctl start`. Active services are never restarted by this control. Additional Chrony/NTP health checks may still require diagnosis after all services are running.

**Settings → My World Clocks → Show City Backgrounds** controls optional photographs for that account (enabled by default). Metadata comes from Wikipedia and Wikimedia Commons and is cached in SQLite for seven days; unavailable results are cached for six hours. Browser images load directly from Wikimedia with no referrer. Only attributed freely licensed images are displayed, with an on-tile photo-credit control; the application's MIT license does not replace each photo's license. UTC and cities without a suitable photograph retain plain tiles.

Run `python -m pytest -q`. Tests require pytest, Playwright with Edge, httpx and runtime dependencies. Version constants are in version.py; changes are recorded in CHANGELOG.md. Source control excludes databases, credentials, local deployment records and generated test evidence. Local tests, deployed service checks and user acceptance are separate verification stages.
