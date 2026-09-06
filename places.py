"""Local town search and personal daylight/manual display preferences."""
from datetime import datetime
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import unicodedata
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import HTTPException, Query, Request
from pydantic import BaseModel
from security import IdentityStore
from city_images import city_image


def normalise(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def catalogue():
    with gzip.open(Path(__file__).parent / 'assets/geography/places.json.gz', 'rt', encoding='utf-8') as stream:
        rows = json.load(stream)
    return [(r, normalise(' '.join(str(v) for v in r[1:6])), normalise(r[1])) for r in rows]


def describe(row):
    return dict(id=row[0], city=row[1], country_code=row[3], country=row[4], region=row[5],
                latitude=row[6], longitude=row[7], timezone=row[8])


@lru_cache(maxsize=32)
def country_places(code):
    return [{**describe(row), 'search': text, 'city_search': city}
            for row, text, city in catalogue() if row[3] == code]


@lru_cache(maxsize=512)
def nearest(latitude, longitude):
    lat = math.radians(latitude)
    def distance(entry):
        r = entry[0]
        return (math.sin(math.radians(r[6] - latitude) / 2) ** 2
                + math.cos(lat) * math.cos(math.radians(r[6])) * math.sin(math.radians(r[7] - longitude) / 2) ** 2)
    return describe(min(catalogue(), key=distance)[0])


def location_from(place, latitude=None, longitude=None):
    return dict(location=place['city'], country=place['country'], country_code=place['country_code'],
                region=place['region'], timezone=place['timezone'], reference_city=place['city'],
                latitude=place['latitude'] if latitude is None else latitude,
                longitude=place['longitude'] if longitude is None else longitude)


def reference(location):
    if location.get('latitude') is None or location.get('longitude') is None:
        return None
    zone = location.get('timezone')
    city = location.get('reference_city', location.get('location', ''))
    if not zone:
        place = nearest(location['latitude'], location['longitude'])
        zone, city = place['timezone'], place['city']
    try:
        now = datetime.now(ZoneInfo(zone))
    except (KeyError, ValueError):
        return None
    offset = now.strftime('%z')
    country = location.get('country_code') or nearest(location['latitude'], location['longitude'])['country_code']
    return dict(city=city, country_code=country, timezone=zone, utc='UTC ' + offset[:3] + ':' + offset[3:])


class PlaceChoice(BaseModel):
    id: int


class ThemeChoice(BaseModel):
    theme: Literal['light', 'dark']


def install(app, backend):
    def identity(request, mutate=False):
        store = IdentityStore(backend.monitor)
        user = store.authenticate(request)
        if mutate:
            store.same_origin(request)
        return user

    @app.get('/user/location/image', include_in_schema=False)
    def location_image(request: Request):
        user = identity(request)
        clock = reference(user['location'])
        if not user['clock_backgrounds'] or not clock:
            return {'image': None}
        return {'image': city_image(backend.monitor, clock['timezone'], clock['city'])}

    @app.get('/user/locations/search', include_in_schema=False)
    def search(request: Request, q: str = Query(min_length=2, max_length=100)):
        identity(request)
        tokens = normalise(q).split()
        if not tokens:
            return {'places': []}
        hits = [entry for entry in catalogue() if all(token in entry[1] for token in tokens)]
        hits.sort(key=lambda entry: (entry[2] != normalise(q), not entry[2].startswith(tokens[0])))
        return {'places': [describe(entry[0]) for entry in hits[:30]]}

    @app.get('/user/locations/country', include_in_schema=False)
    def country(request: Request, code: str = Query(pattern=r'^[A-Za-z]{2}$')):
        identity(request)
        code = code.lower()
        return {'country_code': code, 'places': country_places(code)}

    @app.put('/user/location', include_in_schema=False)
    def select(request: Request, body: PlaceChoice):
        user = identity(request, True)
        row = next((entry[0] for entry in catalogue() if entry[0][0] == body.id), None)
        if row is None:
            raise HTTPException(404, 'Choose a town or city from the search results')
        location = location_from(describe(row))
        with backend.monitor.connect() as db:
            db.execute('UPDATE users SET location=?,version=version+1 WHERE id=?', (json.dumps(location), user['id']))
        return location

    @app.delete('/user/location', include_in_schema=False)
    def clear(request: Request):
        user = identity(request, True)
        from telemetry import solar_status
        old = user['location']
        theme = old.get('theme', 'light')
        if old.get('latitude') is not None and old.get('longitude') is not None:
            theme = solar_status(latitude=old['latitude'], longitude=old['longitude'])['theme']
        location = dict(location='', latitude=None, longitude=None, theme=theme)
        with backend.monitor.connect() as db:
            db.execute('UPDATE users SET location=?,version=version+1 WHERE id=?', (json.dumps(location), user['id']))
        return location

    @app.put('/user/theme', include_in_schema=False)
    def save_theme(request: Request, body: ThemeChoice):
        user = identity(request, True)
        with backend.monitor.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            location = json.loads(db.execute('SELECT location FROM users WHERE id=?', (user['id'],)).fetchone()[0])
            if location.get('latitude') is not None and location.get('longitude') is not None:
                raise HTTPException(409, 'Clear your location to choose a manual theme')
            location['theme'] = body.theme
            db.execute('UPDATE users SET location=?,version=version+1 WHERE id=?', (json.dumps(location), user['id']))
        return {'success': True, 'theme': body.theme}
