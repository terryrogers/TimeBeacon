# TimeBeacon 5.9.2 Verification

## Interface

- Native single-selection dropdowns now allow room for their text and padding. Account Setup was checked at desktop and mobile widths in light and dark themes; screenshots confirm that the text is vertically centred and descenders are visible.
- Shared request handling displays Semantic UI inline loaders after 350 ms. Fast responses do not insert a visible indicator. Indicators use the current theme and accessible status text, with one indicator per region for overlapping requests.
- Coverage includes initial page loading, authentication, dashboard refreshes, graphs, administration/settings saves, service actions, location searches/detection, clock catalogues and changes, city-image preparation, photo updates and API-key requests. Existing Semantic UI assets are reused without a new dependency or CDN request.
- Loaders do not block interaction or modal close controls. Request/body errors, aborts and timeouts remove them through a shared cleanup path. City-image load/error events also clear their indicator, with a bounded fallback for unavailable images.
- Browser regression checks exercise slow sign-in and administration loading, both account-setup options, password-change workflows, existing-user photo editing, graph loading/errors, overlapping operations, timeout cleanup, dropdown sizing and modal header/footer visibility. All email and account data in tests is synthetic; no real email is sent.

## Publication

The complete regression suite passed: **64 tests** in 263.52 seconds, with two existing test-library deprecation warnings. Changed JavaScript files passed Node syntax checks.

Outgoing changes were reviewed for public disclosure and checked with local JavaScript syntax validation and detect-secrets scanning. Exact staged content receives a separate review before upload. Existing ignores exclude local data, credentials, backups, environments, screenshots and deployment records. Dependencies and the authentication backend are unchanged. This patch is not a full repository security audit, and checks do not guarantee security.

## Deployment

Dashboard **5.9.2** / API **4.1.0** is deployed. All **52 runtime files** match the local package by SHA-256, including the new shared loading module. Public static assets match, public health is healthy, and anonymous dashboard/data requests retain their authentication boundary.

Only the dashboard service restarted. Chrony and GPSD remained active with unchanged process IDs. Existing users, clocks and settings were preserved, and history retained its oldest sample. Pre/post backup archives, SQLite integrity checks and an identity-key encryption round trip passed; a full disaster-recovery restore was not performed.

The loader implementation follows [Semantic UI's loader documentation](https://semantic-ui.com/elements/loader.html).

To test: open Administration → Users → New User and inspect Account Setup. Open a history graph or settings page with browser network throttling enabled to see the delayed loader; restore normal network speed afterwards.

Repository: https://github.com/terryrogers/TimeBeacon. No associated OpenProject work package is recorded; no OpenProject records or time entries were created.
