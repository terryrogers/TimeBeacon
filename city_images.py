"""Cached, attributed Wikimedia photographs for configured clock cities."""

import json
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "TimeBeacon/5.2 (https://github.com/terryrogers/TimeBeacon)"
TITLES = {
    "America/New_York": "New York City",
    "Asia/Kolkata": "Kolkata",
    "Asia/Calcutta": "Kolkata",
    "Asia/Ho_Chi_Minh": "Ho Chi Minh City",
    "Asia/Saigon": "Ho Chi Minh City",
    "America/St_Johns": "St. John's, Newfoundland and Labrador",
    "America/Port-au-Prince": "Port-au-Prince",
    "America/Mexico_City": "Mexico City",
    "America/Indiana/Indianapolis": "Indianapolis",
    "Pacific/Chatham": "Chatham Islands",
    "Asia/Tel_Aviv": "Tel Aviv",
    "Asia/Jerusalem": "Jerusalem",
}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def plain(value):
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def request_json(host, params):
    request = urllib.request.Request(
        "https://"
        + host
        + "/w/api.php?"
        + urllib.parse.urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                **params,
            }
        ),
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def fetch_city_image(zone, city=None):
    if "/" not in zone or zone.startswith(("Etc/", "US/", "Canada/")):
        return None
    title = TITLES.get(zone, zone.split("/")[-1].replace("_", " "))
    if city and city != zone.split("/")[-1].replace("_", " "):
        title = city[:120]
    result = request_json(
        "en.wikipedia.org",
        {
            "prop": "pageimages|coordinates|pageprops",
            "titles": title,
            "piprop": "name|thumbnail",
            "pithumbsize": 640,
            "redirects": 1,
        },
    )
    pages = result.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    filename = page.get("pageimage", "")
    image_url = page.get("thumbnail", {}).get("source", "")
    if (
        not page.get("coordinates")
        or "disambiguation" in page.get("pageprops", {})
        or not filename
    ):
        return None
    url = urllib.parse.urlsplit(image_url)
    if url.scheme != "https" or url.hostname not in (
        "upload.wikimedia.org",
        "thumb.wikimedia.org",
    ):
        return None
    metadata = request_json(
        "commons.wikimedia.org",
        {
            "prop": "imageinfo",
            "titles": "File:" + filename,
            "iiprop": "extmetadata|url",
        },
    )
    pages = metadata.get("query", {}).get("pages", [])
    info = pages[0].get("imageinfo", []) if pages else []
    if not info:
        return None
    meta = info[0].get("extmetadata", {})
    license_name = plain(meta.get("LicenseShortName", {}).get("value", ""))
    if not license_name.lower().startswith(("cc by", "cc0", "public domain")):
        return None
    artist = plain(meta.get("Artist", {}).get("value", ""))
    if not artist:
        return None
    return {
        "city": page.get("title", title),
        "image_url": urllib.parse.urlunsplit(url._replace(query="")),
        "artist": artist,
        "credit": plain(meta.get("Credit", {}).get("value", "")),
        "license": license_name,
        "source_url": "https://commons.wikimedia.org/wiki/File:"
        + urllib.parse.quote(filename, safe=""),
    }


def city_image(monitor, zone, city=None):
    now = time.time()
    cache_key = zone + "|" + (city or "")
    # Claim a short lease so multiple tabs/workers do not repeat external requests.
    with monitor.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload,expires FROM city_images WHERE zone=?", (cache_key,)
        ).fetchone()
        if row and row[1] > now:
            return json.loads(row[0])
        db.execute(
            "INSERT OR REPLACE INTO city_images VALUES (?,?,?)",
            (cache_key, "null", now + 30),
        )
    try:
        result = fetch_city_image(zone, city)
    except (OSError, ValueError, KeyError, TypeError):
        result = None
    with monitor.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO city_images VALUES (?,?,?)",
            (cache_key, json.dumps(result), now + (604800 if result else 21600)),
        )
    return result
