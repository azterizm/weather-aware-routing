"""TomTom Search (geocoding) and Calculate Route (truck routing) clients."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache

from ..domain.types import LatLon, Place, Route
from . import http
from .http import NoRouteFound, ProviderError, UpstreamQuotaExceeded, UpstreamUnavailable

logger = logging.getLogger("trips.providers.tomtom")

PROVIDER = "TomTom"
GEOCODE_CACHE_SECONDS = 24 * 3600
NO_ROUTE_CODES = {"NO_ROUTE_FOUND", "MAP_MATCHING_FAILURE", "CANNOT_RESTORE_BASEROUTE"}
# Long-haul truck routing with alternatives takes ~6-8 s; leave headroom.
ROUTE_TIMEOUT = (3.05, 14.0)
SEARCH_TIMEOUT = (3.05, 5.0)


def _check_status(response, data: Any) -> None:
    if response.status_code == 200:
        return
    if response.status_code in (403, 429):
        logger.error("TomTom rejected the request with %s", response.status_code)
        raise UpstreamQuotaExceeded(
            "The routing provider rejected the request. The daily quota is used up "
            "or the API key is invalid."
        )
    if response.status_code >= 500:
        raise UpstreamUnavailable("The routing provider is unavailable. Please try again.")
    detail = data.get("detailedError", {}) if isinstance(data, dict) else {}
    if detail.get("code") in NO_ROUTE_CODES:
        raise NoRouteFound("No truck route could be found between these locations.")
    logger.error("TomTom error %s: %s", response.status_code, detail or data)
    raise ProviderError("The routing provider could not process the request.")


def _get(url: str, params: list[tuple[str, str]], timeout: tuple[float, float]) -> Any:
    response = http.get(PROVIDER, url, [("key", settings.TOMTOM_API_KEY), *params], timeout)
    try:
        data = response.json()
    except ValueError:
        data = None
    _check_status(response, data)
    if data is None:
        raise UpstreamUnavailable("The routing provider returned an invalid response.")
    return data


# --- Geocoding ---------------------------------------------------------------------------


def _place_label(result: dict) -> str:
    address = result.get("address", {}).get("freeformAddress", "")
    poi_name = result.get("poi", {}).get("name")
    return f"{poi_name}, {address}" if poi_name and address else (poi_name or address)


def search_places(query: str, limit: int = 5) -> list[Place]:
    """Typeahead place search for the trip form."""
    normalized = " ".join(query.lower().split())
    digest = hashlib.sha256(f"{settings.GEOCODE_COUNTRY_SET}|{normalized}".encode()).hexdigest()
    cache_key = f"geocode:v1:{digest}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{settings.TOMTOM_BASE_URL}/search/2/search/{quote(normalized, safe='')}.json"
    data = _get(
        url,
        [
            ("typeahead", "true"),
            ("limit", str(limit)),
            ("countrySet", settings.GEOCODE_COUNTRY_SET),
        ],
        SEARCH_TIMEOUT,
    )
    places = []
    for result in data.get("results", []):
        position = result.get("position") or {}
        label = _place_label(result)
        if label and "lat" in position and "lon" in position:
            places.append(Place(label=label, location=LatLon(position["lat"], position["lon"])))
    cache.set(cache_key, places, GEOCODE_CACHE_SECONDS)
    return places


# --- Routing -----------------------------------------------------------------------------


def _parse_route(raw: dict) -> Route:
    # Legs are concatenated as-is: progress pointIndex counts across all legs, including the
    # duplicated junction point between legs.
    points = tuple(
        LatLon(p["latitude"], p["longitude"]) for leg in raw["legs"] for p in leg["points"]
    )
    point_times: list[float | None] = [None] * len(points)
    for entry in raw.get("progress", []):
        index = entry.get("pointIndex")
        seconds = entry.get("travelTimeInSeconds")
        if isinstance(index, int) and 0 <= index < len(points) and seconds is not None:
            point_times[index] = float(seconds)
    summary = raw["summary"]
    return Route(
        points=points,
        length_m=float(summary["lengthInMeters"]),
        travel_time_s=float(summary["travelTimeInSeconds"]),
        departure=datetime.fromisoformat(summary["departureTime"]).astimezone(UTC),
        arrival=datetime.fromisoformat(summary["arrivalTime"]).astimezone(UTC),
        point_times_s=tuple(point_times),
    )


def calculate_routes(
    locations: Sequence[LatLon],
    depart_at: datetime | None,
    max_alternatives: int = 0,
    timeout: tuple[float, float] = ROUTE_TIMEOUT,
) -> list[Route]:
    """Truck routes through `locations` (origin, optional vias, destination).

    `depart_at=None` departs now. Alternatives come back best-first and may be fewer than
    requested.
    """
    path = ":".join(f"{p.lat:.6f},{p.lon:.6f}" for p in locations)
    url = f"{settings.TOMTOM_BASE_URL}/routing/1/calculateRoute/{path}/json"
    params = [
        ("travelMode", "truck"),
        ("vehicleCommercial", "true"),
        ("traffic", "true"),
        ("routeType", "fastest"),
        ("maxAlternatives", str(max_alternatives)),
        ("departAt", depart_at.isoformat(timespec="seconds") if depart_at else "now"),
        ("routeRepresentation", "polyline"),
        ("extendedRouteRepresentation", "travelTime"),
    ]
    if max_alternatives:
        params.append(("alternativeType", "anyRoute"))
    data = _get(url, params, timeout)
    try:
        routes = [_parse_route(raw) for raw in data.get("routes", [])]
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Unexpected TomTom route payload: %s", type(exc).__name__)
        raise UpstreamUnavailable("The routing provider returned an invalid response.") from None
    routes = [route for route in routes if len(route.points) >= 2]
    if not routes:
        raise NoRouteFound("No truck route could be found between these locations.")
    return routes


# --- Map tiles ---------------------------------------------------------------------------

TILE_TIMEOUT = (3.05, 5.0)
MAX_TILE_ZOOM = 18


def fetch_tile(zoom: int, x: int, y: int) -> bytes:
    """A 256 px PNG map tile. The API key stays on the server."""
    url = f"{settings.TOMTOM_BASE_URL}/map/1/tile/basic/main/{zoom}/{x}/{y}.png"
    response = http.get(
        PROVIDER, url, [("key", settings.TOMTOM_API_KEY), ("tileSize", "256")], TILE_TIMEOUT
    )
    if response.status_code != 200 or not response.headers.get("Content-Type", "").startswith(
        "image/"
    ):
        _check_status(response, None)
        raise UpstreamUnavailable("The map tile provider returned an invalid response.")
    return response.content
