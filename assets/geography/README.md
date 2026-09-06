# Town and City Catalogue

Derived from GeoNames `cities1000.zip`, `countryInfo.txt` and `admin1CodesASCII.txt`, downloaded 6 September 2026.

Source: https://download.geonames.org/export/dump/

© GeoNames contributors, licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). This geographic dataset is separate from TimeBeacon's MIT-licensed code. GeoNames provides data without a guarantee of accuracy or completeness.

The compressed JSON retains settlement ID, local and ASCII names, country code/name, region, latitude/longitude, IANA time zone and population, ordered by population. It covers settlements above 1,000 inhabitants and administrative seats through PPLA3. Rebuild with `python scripts/build_places.py`.

Search runs locally. Device-location reference clocks use the nearest catalogued settlement's time zone; this is a town-based reference, not a political time-zone boundary lookup. Daylight calculations retain the device's actual coordinates.
