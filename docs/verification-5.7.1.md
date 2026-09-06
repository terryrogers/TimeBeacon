# TimeBeacon 5.7.1 verification

- Local regression suite: 46 passed.
- Browser checks confirm top-right controls do not overlap the city title, the remove control sits left of the handle, and dashboard/Settings handles both use nine circles in a 12px SVG.
- Pointer movement changes the visible dragged card/row position in both views; dropping persists order, and Escape removes the preview without saving changes.
- Reset Clocks is absent from the dashboard and remains functional in Settings.
- Defaults and personal picker selections retain flag, timezone and location columns with UTC offset spacing. Saved values persist after reload.
- Deployed all 43 runtime files; installed and public static asset hashes match local source.
- Live Dashboard 5.7.1 / API 4.1.0 reports healthy. Only the dashboard restarted; Chrony and GPSD process IDs are unchanged.
- Both user accounts, clocks and global settings were preserved. History increased from 1790 to 1793 samples with the oldest sample preserved.
- Pre- and post-upgrade backups passed archive/SQLite checks; no production profile changes were used for testing. Full disaster recovery restore was not performed.
- User acceptance testing remains for Terry. Repository: https://github.com/terryrogers/TimeBeacon. No associated OpenProject work package is recorded.
