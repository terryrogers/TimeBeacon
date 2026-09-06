# TimeBeacon 5.9.4 Verification

- City/town loading uses a small, icon-only Semantic UI spinner inside the dropdown, left of its arrow. The arrow stays visible, the input reserves space for both icons, and an accessible label describes progress without visible wording.
- Country preparation, worldwide searches and location saving share that indicator. Cached country matches remain selectable while worldwide results load; cancellation, failures and successful completion clear the indicator.
- Other shared loaders use a centred Semantic UI text loader inside a dimmer over the affected content. User Directory shows Getting Users from its initial HTML and during subsequent refreshes. Colours follow the active light/dark theme. Popup headers, close buttons and status footers remain outside the dimmed content.
- Shared loaders retain the short delay and overlapping-request counting. Error and timeout paths restore the region's previous busy state and remove the overlay.

Implementation follows the [Semantic UI loader documentation](https://semantic-ui.com/elements/loader.html), using the existing bundled assets. No dependency or API contract changes were required.

The full local suite passed **66 tests** in 272.05 seconds, including held-request loader checks, success/error/timeout cleanup, cached-country search and existing authentication, administration, clock and graph flows. Browser screenshots were inspected in both themes. Two existing test-library deprecation warnings remain. No real email was sent and no live account was changed by testing.

JavaScript syntax checks and the outgoing detect-secrets scan passed. The outgoing diff was manually reviewed for public disclosure, with a separate exact staged-content review and scan before pushing. Dependencies are unchanged; no additional dependency audit or full repository security audit was performed. These checks do not guarantee security. Local deployment records, archives, databases and screenshots remain ignored.

Dashboard **5.9.4** / API **4.1.0** is deployed and its public health response is healthy. All **52 runtime files** and checked public static assets match the tested package. Only the dashboard restarted; Chrony and GPSD retained their process IDs. Pre/post backup archives and SQLite integrity were verified; accounts, clocks and settings were preserved and history retained its oldest sample. A full restore was not performed.

To test:

1. In Settings, type in Search Cities and Towns. While a request is pending, check for a small spinner immediately left of the dropdown arrow, with no loading wording.
2. Open Administration → Users. While the directory loads, confirm the centred spinner and Getting Users text. Check both themes.
3. Open a history graph. During loading, confirm its header, close button and status footer remain accessible; the loader disappears once results or an error arrive.

Fast or cached requests can complete before the delayed shared loader is shown. Tests deliberately hold requests to inspect loading states.

Repository: https://github.com/terryrogers/TimeBeacon. No associated OpenProject work package is recorded; no OpenProject records or time entries were created.
