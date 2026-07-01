"""Geospatial helpers.

Proximity uses a bounding-box prefilter plus haversine refinement on the
drivers' denormalized lat/lng, which is adequate at small scale. Hot-path
proximity runs through Redis GEO; PostGIS would be the next step for heavy
spatial querying.
"""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088
_KM_PER_DEG_LAT = 111.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(
    lat: float, lng: float, radius_km: float
) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lng, max_lng) enclosing the radius.

    Used as a cheap, index-friendly SQL prefilter before exact haversine.
    """
    d_lat = radius_km / _KM_PER_DEG_LAT
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)  # guard near the poles
    d_lng = radius_km / (_KM_PER_DEG_LAT * cos_lat)
    return (lat - d_lat, lat + d_lat, lng - d_lng, lng + d_lng)
