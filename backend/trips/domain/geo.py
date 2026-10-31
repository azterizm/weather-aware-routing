"""Geometry helpers on WGS84 coordinates. Pure functions, no I/O."""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence

from .types import LatLon

EARTH_RADIUS_MI = 3958.7613
MILES_PER_DEG_LAT = 69.0
METERS_PER_MILE = 1609.344


def haversine_miles(a: LatLon, b: LatLon) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def cumulative_miles(points: Sequence[LatLon]) -> list[float]:
    """Cumulative distance (miles) from the first point to each point."""
    cum = [0.0] * len(points)
    for i in range(1, len(points)):
        cum[i] = cum[i - 1] + haversine_miles(points[i - 1], points[i])
    return cum


def locate_along(cum: Sequence[float], distance: float) -> tuple[int, float]:
    """Find the segment containing `distance`.

    Returns (i, fraction) such that the position lies on segment points[i] -> points[i + 1]
    at `fraction` of its length. Distances outside the line are clamped to its ends.
    """
    if len(cum) < 2:
        return 0, 0.0
    if distance <= 0:
        return 0, 0.0
    if distance >= cum[-1]:
        return len(cum) - 2, 1.0
    i = bisect_right(cum, distance) - 1
    i = min(max(i, 0), len(cum) - 2)
    seg = cum[i + 1] - cum[i]
    fraction = (distance - cum[i]) / seg if seg > 0 else 0.0
    return i, fraction


def interpolate_point(a: LatLon, b: LatLon, fraction: float) -> LatLon:
    # Linear interpolation is accurate enough over the short segments of a route polyline.
    return LatLon(a.lat + (b.lat - a.lat) * fraction, a.lon + (b.lon - a.lon) * fraction)


def point_along(points: Sequence[LatLon], cum: Sequence[float], distance: float) -> LatLon:
    if len(points) == 1:
        return points[0]
    i, fraction = locate_along(cum, distance)
    return interpolate_point(points[i], points[i + 1], fraction)


def _perpendicular_distance_deg(p: LatLon, a: LatLon, b: LatLon, lon_scale: float) -> float:
    """Distance from p to segment a-b in latitude-degrees (equirectangular projection)."""
    ax, ay = a.lon * lon_scale, a.lat
    bx, by = b.lon * lon_scale, b.lat
    px, py = p.lon * lon_scale, p.lat
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(points: Sequence[LatLon], tolerance_deg: float) -> list[LatLon]:
    """Ramer-Douglas-Peucker simplification (iterative). Always keeps both endpoints."""
    n = len(points)
    if n <= 2:
        return list(points)
    mean_lat = sum(p.lat for p in points) / n
    lon_scale = math.cos(math.radians(mean_lat))
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        max_dist, index = 0.0, -1
        for i in range(start + 1, end):
            d = _perpendicular_distance_deg(points[i], points[start], points[end], lon_scale)
            if d > max_dist:
                max_dist, index = d, i
        if index != -1 and max_dist > tolerance_deg:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [p for p, k in zip(points, keep, strict=True) if k]


def corridor_cells(
    routes: Sequence[Sequence[LatLon]],
    half_width_miles: float,
    spacing_deg: float,
) -> list[LatLon]:
    """Centres of a global lat/lon grid (cell size `spacing_deg`) within the route corridor.

    A cell is included when its centre lies within `half_width_miles` of a point sampled
    along any route. Sampling every half cell keeps the error below the cell size.
    """
    step_miles = max(0.5, min(spacing_deg * MILES_PER_DEG_LAT, half_width_miles) / 2)
    hw_lat_deg = half_width_miles / MILES_PER_DEG_LAT
    cells: set[tuple[int, int]] = set()
    for route in routes:
        if not route:
            continue
        cum = cumulative_miles(route)
        total = cum[-1]
        samples = max(1, math.ceil(total / step_miles))
        for k in range(samples + 1):
            p = point_along(route, cum, total * k / samples)
            lon_scale = max(math.cos(math.radians(p.lat)), 0.01)
            hw_lon_deg = hw_lat_deg / lon_scale
            i_min = math.floor((p.lat - hw_lat_deg) / spacing_deg)
            i_max = math.ceil((p.lat + hw_lat_deg) / spacing_deg)
            j_min = math.floor((p.lon - hw_lon_deg) / spacing_deg)
            j_max = math.ceil((p.lon + hw_lon_deg) / spacing_deg)
            for i in range(i_min, i_max + 1):
                dlat_mi = (i * spacing_deg - p.lat) * MILES_PER_DEG_LAT
                for j in range(j_min, j_max + 1):
                    dlon_mi = (j * spacing_deg - p.lon) * MILES_PER_DEG_LAT * lon_scale
                    if dlat_mi * dlat_mi + dlon_mi * dlon_mi <= half_width_miles**2:
                        cells.add((i, j))
    return [LatLon(round(i * spacing_deg, 5), round(j * spacing_deg, 5)) for i, j in sorted(cells)]
