# TimeBeacon 5.9.0 Verification

- Complete regression suite: **63 passed**. A further 12 authentication/onboarding checks passed after adjusting reset-template name substitution. Two test-library deprecation warnings remain.
- Browser checks verify the reference flag, panel-sized background in both themes, photo-credit dialog, immediate background toggle, and the location picker remaining clickable above other panel content. Photographs in automated tests use synthetic fixtures; normal city lookup and attribution reuse the existing world-clock provider/cache.
- Browser checks verify persisted email format/footer/template fields, a single role dropdown defaulting to User, password-now setup with required change, and emailed-link setup through password selection and subsequent sign-in.
- Backend checks cover encrypted SMTP settings, plain and multipart HTML messages, escaped HTML/template values, clickable HTTPS links, footer inclusion, template link validation, invitation expiry/single use, account enablement/configuration requirements, required-password access restrictions, 2FA verification and subsequent mandatory enrollment.
- The added password-change state preserves existing 5.8 authentication/reset fingerprints for unchanged accounts. Existing accounts default to no forced password change.
- All email tests use mocks. No real invitation, reset or test email was sent. Actual inbox delivery remains user acceptance testing through the configured SMTP service.
- Deployed **51 runtime files**. Installed file hashes and public static assets match the local package. Dashboard **5.9.0** / API **4.1.0** reports healthy; the reference-image endpoint rejects anonymous requests.
- Only the dashboard restarted. Chrony and GPSD process IDs were unchanged. Both accounts, all prior user fields, personal clocks and global settings were preserved.
- History grew from **2,784 to 2,789 samples**, retaining the oldest sample. Pre/post backup archives and SQLite integrity checks passed; the identity-key encryption round trip passed. Full disaster recovery restoration was not performed.

## Publication Checks

The outgoing source, templates, styles, tests and documentation were reviewed for secrets, private data, unintended files and publication suitability, followed by a separate review of exact staged content. Backups, databases, deployment records, keys, local environments and diagnostic/test artifacts remain excluded. The outgoing history contains only this update.

Local detect-secrets scanning with network verification disabled found synthetic test values and false positives on email-template text/password-change schema names. Local Bandit scanning found five low-severity heuristic alerts: three existing non-security parsing assertions, an email template, and a column definition. No confirmed vulnerability or actual outgoing credential was identified. A fresh pip-audit of application requirements reported no known vulnerabilities. No code was uploaded to a scanning service and no paid tools were used. These checks do not guarantee security; this minor update was not a full-repository audit.

## User Acceptance

1. Open Settings, enable Show City Backgrounds, and confirm the reference-clock flag and faint city photograph across Daylight & Display. Disable it and confirm the photograph disappears. Open its information control to inspect attribution.
2. In Administration → Email, choose Plain Text or HTML, enter a footer, adjust New User/Password Reset templates, and save. Keep `{link}` in both bodies. Send a test to your chosen address and check its format/footer in the inbox.
3. In Administration → Users → New User, confirm User is selected in Roles. Choose Set Password Now and enable Require Password Change At Next Sign-In. Save an enabled test account and verify that it cannot enter the dashboard until its password changes.
4. Create another enabled test account using Email Temporary Setup Link. Verify receipt, password selection and subsequent normal sign-in. The link expires after 24 hours and cannot be reused. Forgotten Password can replace an expired/undelivered invitation.

Repository: https://github.com/terryrogers/TimeBeacon. No associated OpenProject work package is recorded, so no OpenProject records or time entries were created.
