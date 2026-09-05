# TimeBeacon API 4.0

Use HTTPS. Authenticate with `Authorization: Bearer <your-user-api-key>` or sign in through the browser form and use its session cookie. HTTP Basic credentials are no longer accepted. Keys are created and revoked in User Settings, never in Administration on behalf of another user. Both methods require `api.view`, and all requests recheck account enablement and current role permissions. Browser sessions are also accepted for same-origin use with the same API permission checks. POST clock mutations accept JSON; session-cookie requests must include the matching Origin header.

Unauthorized requests return 401; missing permissions return 403; invalid input returns 422. Login has a bounded attempt limit. Disabled users and revoked keys lose access immediately. Password changes invalidate sessions and keys.

| Method / endpoint | Additional permission | Response |
| --- | --- | --- |
| GET /health | None; public | status (healthy/unhealthy), details link |
| GET /health/details | server.view | Array: name, startup, status, cpu (percent), ram (bytes) |
| GET /server/status | server.view | cpu_percent, ram_percent, disk_used {percent, bytes, gb, friendly}, cpu_temperature_c, uptime_seconds |
| GET /server/status/history | server.view + server.history | Array: timestamp, value |
| GET /time/status | time.view | stratum, reference, last_offset, rms_offset, leap_status, ntp_rtt, gps_fix, satellites {used, visible}, pps, time_acquisition |
| GET /time/history | time.view + time.history | Array: timestamp, value |
| GET /time/gps | time.view | time_utc, fix_mode, horizontal_error_m, vertical_error_m, time_error_s |
| GET /time/satellites | time.view | Array: id, gnss_id, elevation, azimuth, signal_strength, used_in_fix |
| GET /time/pps | time.view | real_sec, real_nsec, clock_sec, clock_nsec, precision |
| GET /time/acquisition | time.view | Selected source object, or null when none selected |
| GET /time/sources | time.view | Array of source objects |
| GET /clocks | clocks.view | Personal clocks: name, city, timezone_name, time, date, utc |
| POST /clocks/add | clocks.amend | JSON body {"timezone_name":"Europe/London"}; success and optional message |
| POST /clocks/remove | clocks.amend | Same JSON body; success and optional message |
| GET /time/clients | clients.summary | total_clients_seen, total_healthy, total_warning, total_critical, total_unknown |
| GET /time/clients/details | clients.view | Array: hostname, ip_address, ntp_packets, dropped_packets, command_packets, interval, last_seen |

Source fields: name, state, stratum, reach, last_rx, measured_offset (seconds). Current and historical last_offset, rms_offset and ntp_rtt are milliseconds. CPU and RAM are percentages; temperature is degrees Celsius; uptime is seconds. Satellite elevation and azimuth are degrees. PPS fields retain GPSD's numeric units. Client packet/interval/last_seen fields retain Chrony's representations; unresolved hostnames are null.

## History queries

`parameter` is required. Server choices: cpu, ram, storage (percent), storage_used (bytes), temperature, uptime. Time choices: stratum, last_offset, rms_offset, ntp_rtt.

Optional `from` and `to` are Unix timestamps in seconds or ISO 8601 dates with an explicit timezone, for example `2026-09-05T10:00:00Z`. Without dates, the endpoint selects the last 60 minutes; with only `to`, it selects the hour ending then. `from=0` selects from the beginning of recorded time.

`limit` defaults to 1000 and has a maximum of 5000. Each response is an array of {timestamp, value}. The headers X-History-From and X-History-To give the fixed period. If X-Next-After is present, request another page with that value as `after`, keeping the same from/to. Stop when X-Next-After is absent. No original samples are deleted or silently discarded by API pagination.

Example path: `/server/status/history?parameter=cpu&from=2026-09-05T10:00:00Z&to=2026-09-05T11:00:00Z&limit=1000`.

## Migration from API 2

Old /api/* paths and the single NTP_DASHBOARD_API_TOKEN no longer grant access. Create a user with the required roles, then use its credentials or a personal API key. The database migration preserves samples, moves the previous global clocks to the bootstrap administrator, and adds identity tables. New users' clocks are independent. Health-service selections and both last-seen and dropped-packet thresholds are edited in Administration.
