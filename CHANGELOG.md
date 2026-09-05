# Changelog

## Dashboard 5.2.0 / API 4.1.0 — 5 September 2026

- Administrator Fix controls for degraded monitored services, with a fresh state check and explicit action confirmation. Stopped services can be started; missing or masked services can have an obsolete health check removed without installing or unmasking them. Actions are recorded in SQLite and protected by role checks, same-origin validation and a cooldown.
- Operating System and Hardware now occupy separate side-by-side panels, stacked on narrow screens.
- Optional faint city photographs on world clocks, controlled per account in User Settings. Wikimedia Commons attribution is available on each photo tile; unavailable images leave a plain clock.
- Additive account preference and photo-cache migrations preserve existing account and monitoring data. Public API contracts remain at 4.1.0.

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
