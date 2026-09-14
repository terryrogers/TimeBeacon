# TimeBeacon 5.7.0 deployment verification

- Local regression suite: 46 passed. Focused reset/reorder/defaults checks repeated after final cleanup: 2 passed.
- Browser checks: searchable Administration Defaults, saved defaults after reload, personal-clock preservation before reset, reset in both views, real pointer dragging in both views, dashboard keyboard arrows, remove persistence, and themed scrollbar colours.
- Backend checks: exact six valid unique time zones, stale-version conflict, same-origin checks, administrator restriction, clock amendment permission and profile isolation.
- Installed 43 runtime files; deployed hashes and public static assets match local source.
- Public health: healthy. Dashboard 5.7.0 / API 4.1.0.
- Both user accounts, personal clocks and all global settings preserved. History samples increased from 1752 to 1754; oldest sample preserved.
- Only dashboard restarted. Chrony and GPSD process IDs unchanged.
- Application and SQLite backups validated before and after deployment; backup identity key round-trip checked. Full disaster recovery restore was not performed.
- Existing production profiles were not reset or edited for testing. Interactive user acceptance testing remains for Terry.
- GitHub repository: https://github.com/terryrogers/TimeBeacon. No OpenProject work package is associated in the project records.
