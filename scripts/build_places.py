"""Build the bundled CC BY 4.0 GeoNames settlement catalogue."""
import gzip
import io
import json
from pathlib import Path
import urllib.request
import zipfile

BASE = 'https://download.geonames.org/export/dump/'


def download(name):
    with urllib.request.urlopen(BASE + name, timeout=90) as response:
        return response.read()


if __name__ == '__main__':
    countries = {r[0]: r[4] for line in download('countryInfo.txt').decode().splitlines()
                 if line and not line.startswith('#') for r in [line.split('\t')]}
    regions = {r[0]: r[1] for line in download('admin1CodesASCII.txt').decode().splitlines()
               for r in [line.split('\t')]}
    places = []
    with zipfile.ZipFile(io.BytesIO(download('cities1000.zip'))) as archive:
        for line in archive.read('cities1000.txt').decode().splitlines():
            r = line.split('\t')
            if not r[17] or len(r[8]) != 2:
                continue
            places.append([int(r[0]), r[1], r[2], r[8].lower(), countries.get(r[8], r[8]),
                           regions.get(r[8] + '.' + r[10], ''), float(r[4]), float(r[5]), r[17], int(r[14])])
    places.sort(key=lambda p: -p[9])
    target = Path(__file__).resolve().parents[1] / 'assets/geography/places.json.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(json.dumps(places, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    print(f'{len(places)} places; {target.stat().st_size} bytes')
