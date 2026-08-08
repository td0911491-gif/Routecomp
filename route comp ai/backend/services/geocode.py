"""
geocode.py
Turns a place name into (lat, lon) using OpenStreetMap's free Nominatim API.

Nominatim's usage policy requires a real User-Agent identifying the app and
a max of ~1 request/second — both respected here.
https://operations.osmfoundation.org/policies/nominatim/
"""

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "route-compare-app/1.0 (portfolio project)"}


class GeocodeError(Exception):
    pass


def geocode(place: str) -> dict:
    """Returns {"lat": float, "lon": float, "display_name": str} or raises GeocodeError."""
    params = {"q": place, "format": "json", "limit": 1}
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise GeocodeError(f"Could not reach geocoding service: {e}")

    results = resp.json()
    if not results:
        raise GeocodeError(f'No location found for "{place}". Try a more specific name.')

    top = results[0]
    return {
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name", place),
    }
