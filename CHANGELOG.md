# Changelog

## Dashboard 5.4.0 / API 4.1.0 — 6 September 2026

- Align World Clocks Manage at the right edge and centre the GitHub icon with footer text.
- Keep administration menu text readable on hover in both themes; use title case for Roles & Permissions, Configured Roles, Role Permissions, Service Health and Monitored Services.
- Replace service-name entry with Available Services and Monitored Services lists, transfer arrows and an administrator-only system service inventory.
- Require Name, Username and Email Address for new accounts, enforce one selected role, and default Account Enabled to off. Preserve existing accounts during deployment.

## Dashboard 5.3.0 / API 4.1.0 — 6 September 2026

- Service Fix now collects and stores a fresh health sample before confirming resolution, distinguishes a repaired service from other remaining health problems, and immediately refreshes the dashboard. Scheduled and requested sampling share a process lock.
- Dedicated Time Clients administration page for thresholds, foreground/background status colours, and a light/dark palette selector with automatic alternate colours.
- Searchable Semantic UI clock picker with timezone IDs, location descriptions and country flags from the requested reference list; bundled scripts and flags work without external CDN requests.
- Centre popup close controls; add dashboard branding links, a GitHub footer link and a World Clocks Manage shortcut. Move the personal photo toggle to the bottom of the clock settings pane.
- Deployed after 33 local tests. All 37 runtime files and public assets verified; an on-demand server health collection completed in approximately four seconds and persisted successfully. Live health is healthy. Accounts, settings and history were preserved; Chrony and GPSD continued running without restart.

## Dashboard 5.2.0 / API 4.1.0 — 5 September 2026

- Administrator Fix controls for degraded monitored services, with a fresh state check and explicit action confirmation. Stopped services can be started; missing or masked services can have an obsolete health check removed without installing or unmasking them. Actions are recorded in SQLite and protected by role checks, same-origin validation and a cooldown.
- Operating System and Hardware now occupy separate side-by-side panels, stacked on narrow screens.
- Optional faint city photographs on world clocks, controlled per account in User Settings. Wikimedia Commons attribution is available on each photo tile; unavailable images leave a plain clock.
- Additive account preference and photo-cache migrations preserve existing account and monitoring data. Public API contracts remain at 4.1.0.
- Deployed after 29 local tests. All 28 installed runtime files and public assets verified; server-side photo retrieval succeeded for all six configured cities. Account data and history were preserved, with only the dashboard restarted. The existing missing-service warning remains for administrator review.

## Dashboard 5.1.0 / API 4.1.0 — 5 September 2026

- Add detected operating system and hardware details above Server Status.
- Include the same structured inventory in server-status API responses, restricted by Server Status viewing permission. Hardware summaries show maximum CPU frequency, physical cores, nominal RAM and the capacity/type of disks backing the operating system.
- Deployed after 21 local tests. Installed detector output and served assets verified; accounts, configuration and historical samples preserved.


## Dashboard 5.0.0 / API 4.0.0 — 5 September 2026

- Semantic UI components with new Daylight and Midnight themes, bundled styles and icon fonts.
- Dedicated form sign-in with server-side page protection; HTTP Basic removed.
- Administration overview, user directory, role management and service health pages.
- Personal profiles with name, email and Gravatar/custom HTTPS photo, plus encrypted authenticator registration and single-use recovery codes.
- Personal daylight location detection with nearest town/city lookup and hidden coordinates.
- Fixed title and status bars on every popup, with independent content scrolling.
- Additive identity migration preserves existing accounts, clocks and historic samples.
- Deployed and verified: 18 local tests passed; live HTTPS/browser checks covered private sign-in, Administration, API access, graph controls and mobile layout. Existing identities and history were retained; monitoring services remained running. Authenticator enrollment was validated locally without enrolling a production account.


## Dashboard 4.0.0 / API 3.0.0 — 5 September 2026

- Server-enforced roles, accounts, personal API keys and HTTPS browser sessions.
- Administration for users, roles, health services, client thresholds and daylight location.
- Personal world clocks and User Settings, replacing global clocks.
- Rebuilt permission-scoped API routes; retired the old environment token and API paths.
- Desktop-style history title bar, close X, centred controls and conditional gap status footer.
- Browser session probes use the sign-in form; HTTP Basic challenges are limited to API requests.
- Existing samples preserved; previous clocks migrate to the initial administrator.

## Dashboard 3.0.0 / API 2.1.0 (prepared)

- TimeBeacon identity, logo, MIT license and Terry Rogers copyright.
- Automatic custom graph periods and explicit custom-range selection.
- GPS graphs and sampled GPS/time-acquisition state history.
- Authenticated full dashboard snapshot and paginated original history exports.
- New samples also include time-client and NTP response snapshots.
- Existing API paths remain compatible; history defaults to 60 minutes.
