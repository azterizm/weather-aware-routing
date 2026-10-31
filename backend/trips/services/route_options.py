"""Obtain three route options: TomTom alternatives, topped up with via-point detours."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..domain.types import LatLon, Route
from ..providers import tomtom
from ..providers.http import NoRouteFound, ProviderError

logger = logging.getLogger("trips.services.route_options")

TARGET_ROUTES = 3
VIA_OFFSET_FRACTION = 0.12  # perpendicular offset of the via point, share of straight distance
MAX_DETOUR_RATIO = 1.5  # a detour may be at most this much longer than the primary route
MAX_OVERLAP = 0.8  # a detour must share less than this share of its path with any route
OVERLAP_GRID_DEG = 0.01
# Request budget: detours are skipped when the main routing call was already slow.
DETOUR_TIMEOUT = (3.05, 6.0)
DETOUR_SKIP_AFTER_S = 12.0


def via_point(origin: LatLon, destination: LatLon, side: int) -> LatLon:
    """Point offset perpendicular to the origin-destination line at its midpoint."""
    mid_lat = (origin.lat + destination.lat) / 2
    mid_lon = (origin.lon + destination.lon) / 2
    lon_scale = max(math.cos(math.radians(mid_lat)), 0.01)
    dx = (destination.lon - origin.lon) * lon_scale
    dy = destination.lat - origin.lat
    length = math.hypot(dx, dy)
    if length == 0:
        return LatLon(mid_lat, mid_lon)
    offset = VIA_OFFSET_FRACTION * length * side
    return LatLon(mid_lat + offset * (dx / length), mid_lon - offset * (dy / length) / lon_scale)


def _footprint(route: Route) -> set[tuple[int, int]]:
    return {
        (round(p.lat / OVERLAP_GRID_DEG), round(p.lon / OVERLAP_GRID_DEG)) for p in route.points
    }


def is_distinct(candidate: Route, existing: Sequence[Route]) -> bool:
    mine = _footprint(candidate)
    if not mine:
        return False
    return all(len(mine & _footprint(route)) / len(mine) < MAX_OVERLAP for route in existing)


def _detour(origin: LatLon, destination: LatLon, side: int, depart_at: datetime | None):
    try:
        via = via_point(origin, destination, side)
        return tomtom.calculate_routes(
            [origin, via, destination], depart_at, timeout=DETOUR_TIMEOUT
        )[0]
    except ProviderError as exc:
        logger.info("Detour route (side %d) unavailable: %s", side, exc.message)
        return None


def get_route_options(
    origin: LatLon, destination: LatLon, depart_at: datetime | None
) -> tuple[list[Route], list[str]]:
    """Up to three distinct truck routes (provider order first) plus user-facing warnings."""
    started = time.perf_counter()
    routes = tomtom.calculate_routes(
        [origin, destination], depart_at, max_alternatives=TARGET_ROUTES - 1
    )[:TARGET_ROUTES]
    if not routes:
        raise NoRouteFound("No truck route could be found between these locations.")

    elapsed = time.perf_counter() - started
    if len(routes) < TARGET_ROUTES and elapsed > DETOUR_SKIP_AFTER_S:
        logger.warning("Skipping detour routes: routing took %.1f s", elapsed)
    elif len(routes) < TARGET_ROUTES:
        with ThreadPoolExecutor(max_workers=2) as pool:
            detours = list(
                pool.map(lambda side: _detour(origin, destination, side, depart_at), (1, -1))
            )
        max_length = routes[0].length_m * MAX_DETOUR_RATIO
        for detour in detours:
            if len(routes) >= TARGET_ROUTES:
                break
            if detour and detour.length_m <= max_length and is_distinct(detour, routes):
                routes.append(detour)

    warnings = []
    if len(routes) < TARGET_ROUTES:
        found = len(routes)
        warnings.append(
            f"Only {found} distinct route {'option was' if found == 1 else 'options were'} "
            "found for this trip."
        )
    return routes, warnings
