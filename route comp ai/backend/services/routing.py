"""
routing.py
- road_distance_km(): real driving-network distance/duration from OSRM's free
  public demo server (router.project-osrm.org). This is real routing data,
  not a guess — it follows actual roads.
- great_circle_km(): straight-line distance via the haversine formula, used
  as the flight leg distance (planes don't follow roads).

OSRM's public demo server only serves the "driving" profile, so walking/
cycling/bus/train/car estimates in services/compare.py all derive their time
and cost from this same road distance, scaled by mode-specific speeds. This
keeps every non-flight estimate anchored to a real road network distance
instead of a pure straight line, which tends to under-count actual travel
distance by 20-40%.
"""

import math
import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"


class RoutingError(Exception):
    pass


def great_circle_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def road_distance_km(lat1, lon1, lat2, lon2) -> float:
    """Falls back to great-circle * 1.3 (typical road/straight-line ratio) if OSRM
    has no drivable route (e.g. the two points are on different islands/continents)."""
    url = OSRM_URL.format(lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2)
    try:
        resp = requests.get(url, params={"overview": "false"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "Ok" and data.get("routes"):
            return data["routes"][0]["distance"] / 1000.0
    except requests.RequestException:
        pass
    # No usable road route — fall back to a straight-line estimate
    return great_circle_km(lat1, lon1, lat2, lon2) * 1.3
