# TimeBeacon 5.8.0 Verification

## Automated and Browser Checks

- Final complete local regression run: **57 passed**, with two test-library deprecation warnings. Tests use temporary databases and synthetic accounts. SMTP delivery is mocked.
- Password-first sign-in, restricted factor challenges, recovery-code consumption, challenge expiry, TOTP replay protection, mandatory enrollment, and existing session/API-key enforcement were verified.
- Password resets were checked for generic account responses, hashed single-use tokens, expiry, credential/email changes, disabled accounts, session/key revocation and retained TOTP. Reset fragments are removed from browser URLs, including links opened in the same login tab.
- Email configuration checks cover encrypted password storage, password omission from reads, blank-password preservation, SMTP/STARTTLS/SSL transports, permission and origin checks, and generic delivery failures.
- Browser checks cover Security and Email administration, staged login, forced enrollment, world clocks, profile photos, graphs, service controls and existing dashboard features.
- Location search, flags, right-aligned time zones, reference clocks, reload persistence, personal-account isolation, clearing location and manual Light/Dark preferences were verified. Screenshots were inspected in light and dark modes.
- The bundled GeoNames catalogue contains 170,942 places and 392 valid IANA zones. Search and reference lookup were also checked using the deployed Linux runtime. Device coordinates remain the basis of daylight calculations; the reference zone comes from the nearest catalogue town.

## Deployment Checks

- Installed 51 runtime files. Remote file hashes and public static assets match the local package.
- Live Dashboard **5.8.0** / API **4.1.0** reports healthy. Only the dashboard service restarted; Chrony and GPSD process IDs were unchanged.
- Both user accounts, all existing account fields, clocks and global settings were preserved. No production profile was edited for testing.
- History increased from 2,693 to 2,699 samples; the oldest sample was preserved. SQLite integrity checks passed and additive authentication tables were verified.
- Pre- and post-upgrade application/database/key backups passed archive, SQLite and encryption-key round-trip checks. Full disaster-recovery restoration was not performed.
- Public requests to personal location/profile and Security/Email APIs are denied without authentication. Administration pages redirect anonymous visitors to sign-in.
- SMTP remains unconfigured, the recovery administrator is unset and global 2FA enforcement remains off. No real test email was sent; SMTP acceptance and inbox delivery require user testing after configuration.

## Publication Review

- Reviewed outgoing source, templates, scripts, documentation, tests and the expanded geographic dataset for credentials, private infrastructure details, unintended files and publication suitability. Reviewed the exact outgoing content again before publication. Deployment records, backups, local keys, databases, virtual environments, screenshots and scanner logs remain ignored.
- Local detect-secrets 1.5.0 scan with network verification disabled identified only intentional synthetic test values. No actual credential was found in outgoing content.
- Local pip-audit 2.10.1 checks of application requirements and the deployed environment's 35 installed packages reported no known vulnerabilities.
- Local Bandit 1.9.4 scan found no issues in the new authentication, mail-delivery or location endpoint modules. Seven heuristic findings were reviewed: three pre-existing parsing assertions, the existing fixed-origin reverse geocoder, subprocess import/fixed internal chronyc arguments, and the catalogue builder's fixed HTTPS downloads. These do not provide a user-controlled command or URL scheme in the inspected paths. No confirmed finding remains from these scans; they do not guarantee absence of vulnerabilities.
- This is a minor update, not a full-repository security audit. The outgoing history contains this update only. No code was uploaded to a scanning service and no paid scanner was used.
- Geographic data retains its separate GeoNames CC BY 4.0 attribution; the application code remains MIT licensed.

## User Acceptance

1. Open Settings → Daylight & Display. Search for a city and choose a result. Confirm its flag/time zone in the picker, its saved location and the reference clock below.
2. Select Clear Location, switch Light/Dark, and reload. Confirm the preference persists. Select a city again to restore automatic daylight mode.
3. Open Administration → Email, enter SMTP and sender details, save, enter a Test To Email Address and select Send Test Email. Check both the on-screen submission result and the recipient inbox.
4. Open Administration → Security and choose a recovery administrator with a saved email address. Register your own authenticator before enabling Enforce 2FA if desired.
5. Sign out and sign in with an enrolled account: the authenticator screen should appear only after the password succeeds. Test Forgotten Password and No Authenticator Code using a suitable test account.

Repository: https://github.com/terryrogers/TimeBeacon. No associated OpenProject project or work package is recorded; no OpenProject records or time entries were created.
