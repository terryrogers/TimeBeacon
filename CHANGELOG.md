# Changelog

## Dashboard 5.9.1 / API 4.1.0 — 6 September 2026

- Default new-account setup to Email Temporary Setup Link. Set Password Now remains available; existing account editing is unchanged.

## Dashboard 5.9.0 / API 4.1.0 — 6 September 2026

- Add the reference-clock flag and a matching optional city photograph across Daylight & Display, with attribution and immediate background-preference updates.
- Add plain-text/HTML message selection, a common email footer, and New User/Password Reset template editors.
- Add new-account setup choices: set a password with an optional mandatory change at next sign-in, or email a single-use 24-hour password setup link.
- Require password changes before full session/API access while retaining authenticator verification and mandatory enrollment.
- Replace account role checkboxes with a single-selection dropdown defaulting to User.

## Dashboard 5.8.0 / API 4.1.0 — 6 September 2026

- Separate password sign-in from authenticator verification, with a dedicated recovery-code or administrator assistance screen.
- Add expiring, single-use emailed password reset links, retaining 2FA and revoking existing sessions/API keys after reset.
- Add Administration → Security for 2FA enforcement, recovery administrator selection and verified recovery approvals requiring new enrollment.
- Add Administration → Email with SMTP encryption, encrypted password storage, sender details and a test-recipient control.
- Keep email unconfigured and 2FA enforcement off until explicitly configured.
- Search a bundled worldwide town/city catalogue beside Get My Location, with country flags, regions and time zones. Show a live reference clock below the chosen location.
- Clear personal location to select a persistent manual Light/Dark theme; selecting a location restores automatic daylight mode.

## Dashboard 5.7.1 / API 4.1.0 — 6 September 2026

- Move the smaller 3×3 drag handle to the top right of each clock card, with the remove × immediately to its left and space above the city name. Use the same handle in Settings.
- Show the dragged card or Settings row following the pointer, with a placeholder and destination highlight. Support cancellation without saving a reorder.
- Keep Reset Clocks only in Settings.
- Show flags, timezone names and right-aligned location descriptions in selected Defaults and personal clock pickers, matching their menus. Display UTC with a space before +/- in place of GMT.

## Dashboard 5.7.0 / API 4.1.0 — 6 September 2026

- Add Administration → Defaults with six searchable city selectors and conflict-safe SQLite persistence. Existing user clocks remain unchanged.
- Add Reset Clocks in both views, restoring the configured defaults only for the signed-in user.
- Add drag handles and keyboard arrow reordering to dashboard cards and Settings rows, with immediate profile persistence and conflict feedback. Restore the top-right remove × on dashboard cards.
- Apply visible themed scrollbars to World Clocks and its dropdown menus.

## Dashboard 5.6.1 / API 4.1.0 — 6 September 2026

- Limit desktop World Clocks to six cards per row; wrap additional clocks onto subsequent rows. Use three, two or one column on smaller screens.
- Preload city-photo metadata and image bytes when adding a clock in Settings with backgrounds enabled, warming the server and browser caches before returning to the dashboard. Show preparation and ready feedback; photo failures leave the clock saved.
- Five focused tests passed, including image preload completion and cached metadata; verified eight-clock layouts from 390px through 1920px. Installed files and public assets match the source, live health is healthy, and accounts/settings/history were preserved.

## Dashboard 5.6.0 / API 4.1.0 — 6 September 2026

- Replace the administrator user editor's photo URL field with the same hover Edit workflow as Settings: Gravatar toggle, upload and clear custom image.
- Share the photo dialog and editor, enforce administrator permission for edits to another account, and preserve photos when saving unrelated user details. Photo changes save immediately; new users must be saved before photo editing.
- Validated account permissions, upload/clear/Gravatar behaviour, photo preservation and unsaved form edits. Deployed all 42 runtime files and verified public assets and healthy service status; accounts, settings and history were preserved, with only the dashboard restarted.

## Dashboard 5.5.3 / API 4.1.0 — 6 September 2026

- Give service lists visible theme-aware scrollbars. Place sticky column headings inside the same scroll area as the rows so Startup and Status remain aligned when scrollbars appear.
- Browser checks passed with overflowing lists in both themes at desktop and mobile widths. Verified column alignment, sticky headings and service transfers. Deployed files and public assets match; live health is healthy and accounts/settings/history were preserved.

## Dashboard 5.5.2 / API 4.1.0 — 6 September 2026

- Add a country flag before each world clock country name using the bundled Semantic UI flags and existing timezone country mapping.
- Align UTC offsets with the city, time and date text while retaining space for photo credits.
- Verified six country flags and rendered text alignment in the browser. Installed files and public assets match the tested source; live health is healthy, with accounts/settings/history preserved and only the dashboard restarted.

## Dashboard 5.5.1 / API 4.1.0 — 6 September 2026

- Shorten the API key clipboard countdown to 30 seconds, retaining conditional clearance and blocked-access retry.
- Fix the profile photo Edit control remaining transparent on hover: hover and keyboard-focus styles now override its hidden state.
- Reproduced the defect with an opacity assertion, then verified visible hover and keyboard focus in both themes and that the photo editor opens.
- Four focused browser tests passed. Deployed and verified all runtime files and public assets; live health is healthy, with accounts/settings/history preserved and only the dashboard restarted.

## Dashboard 5.5.0 / API 4.1.0 — 6 September 2026

- Style World Clocks Manage as a button aligned to the final tile, rename User Settings to Settings, and apply title case across interface headings, labels and buttons.
- Show startup type and current systemd status in both service-selection columns. Mark required new-user fields with an asterisk.
- Display personal clocks with flags, timezone IDs and matching reference descriptions; align Add Clock beside the narrower picker.
- Copy newly created API keys directly to the clipboard without displaying them. Show a 60-second countdown, clear only an unchanged key, and explain blocked clipboard access with retry behaviour.
- Add a photo hover editor for Gravatar preferences, custom-photo removal and bounded PNG/JPEG/WebP uploads. Store sanitized thumbnails in SQLite with owner/admin access checks; preserve existing profiles through additive migrations.
- Deployed after 42 local tests. Verified all 41 installed runtime files, public assets, 273 service inventory entries and the photo encoder as the application user. Health is healthy; accounts, clocks, settings and history were preserved. Only the dashboard restarted.

## Dashboard 5.4.0 / API 4.1.0 — 6 September 2026

- Align World Clocks Manage at the right edge and centre the GitHub icon with footer text.
- Keep administration menu text readable on hover in both themes; use title case for Roles & Permissions, Configured Roles, Role Permissions, Service Health and Monitored Services.
- Replace service-name entry with Available Services and Monitored Services lists, transfer arrows and an administrator-only system service inventory.
- Require Name, Username and Email Address for new accounts, enforce one selected role, and default Account Enabled to off. Preserve existing accounts during deployment.
- Deployed after 36 local tests. Verified installed files, public assets and live service inventory as the application user. Health remains healthy; accounts, settings and history were preserved. Only the dashboard restarted.

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
