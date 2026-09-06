# TimeBeacon 5.9.1 Verification

- New User defaults to Email Temporary Setup Link. Password and required-password-change fields are hidden until Set Password Now is selected. Existing-user editing retains its previous behavior.
- Four browser regression tests passed, covering both setup methods, default selection on reopening, required-password changes, account validation and existing-account editing. Two existing test-library deprecation warnings remain.
- All email delivery in tests was mocked; no real email was sent and no live test account was created.
- Dashboard 5.9.1 / API 4.1.0 deployed successfully. All 51 installed runtime file hashes and the checked public static assets match the local package; public health is healthy.
- Only the dashboard restarted; Chrony and GPSD process IDs remained unchanged. Existing accounts, clocks, settings and historic samples were preserved. Pre/post archive and SQLite integrity checks passed; a full restore was not performed.
- Outgoing files and history were reviewed for publication suitability, with a separate exact-staged-content review and local detect-secrets scan. The only scanner candidate is an existing synthetic test password. No actual credential or confirmed publication issue was found. Runtime dependencies and authentication backend are unchanged; dependency/security analysis was not repeated for this UI default change. These checks do not guarantee security.

To test: open Administration → Users → New User and confirm Account Setup reads Email Temporary Setup Link. Select Set Password Now to display the password controls.

Repository: https://github.com/terryrogers/TimeBeacon. No associated OpenProject work package is recorded; no OpenProject records or time entries were created.
