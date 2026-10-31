"""Open-Meteo hourly forecast client with batching, deduplication, caching and unit checks."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.cache import cache

from ..domain.types import LatLon
from ..domain.weather_select import HourlySeries, floor_hour
from . import http
from .http import ProviderError, UpstreamQuotaExceeded, UpstreamUnavailable

logger = logging.getLogger("trips.providers.open_meteo")

PROVIDER = "Open-Meteo"
HOURLY_VARIABLES = "wind_speed_10m,rain,showers,snowfall"
# Locations are snapped to this grid (~3.5 mi), close to the forecast model resolution, so
# overlapping routes and repeated requests share lookups.
QUANTIZE_DEG = 0.05
BATCH_SIZE = 100
MAX_PARALLEL_BATCHES = 4
CACHE_SECONDS = 30 * 60
TIMEOUT = (3.05, 8.0)
# Open-Meteo serves up to 16 forecast days; stay safely inside that horizon.
FORECAST_HORIZON = timedelta(days=15)

WIND_TO_MPH = {"mp/h": 1.0, "mph": 1.0, "km/h": 1 / 1.609344, "m/s": 2.2369363, "kn": 1.1507794}
PRECIP_TO_IN = {"inch": 1.0, "mm": 1 / 25.4}
SNOW_TO_IN = {"inch": 1.0, "cm": 1 / 2.54}


def quantize(point: LatLon) -> LatLon:
    return LatLon(
        round(round(point.lat / QUANTIZE_DEG) * QUANTIZE_DEG, 4),
        round(round(point.lon / QUANTIZE_DEG) * QUANTIZE_DEG, 4),
    )


def _cache_key(point: LatLon, start: datetime, end: datetime) -> str:
    return f"om:v1:{point.lat:.4f}:{point.lon:.4f}:{start:%Y%m%d%H}:{end:%Y%m%d%H}"


def _factor(units: dict, variable: str, table: dict[str, float]) -> float:
    unit = units.get(variable)
    if unit not in table:
        logger.error("Unexpected Open-Meteo unit for %s: %r", variable, unit)
        raise UpstreamUnavailable("The weather provider returned unexpected units.")
    return table[unit]


def _scaled(values: list, factor: float) -> tuple[float | None, ...]:
    return tuple(None if v is None else float(v) * factor for v in values)


def _parse_location(raw: dict) -> HourlySeries:
    units = raw["hourly_units"]
    hourly = raw["hourly"]
    wind = _scaled(hourly["wind_speed_10m"], _factor(units, "wind_speed_10m", WIND_TO_MPH))
    rain = _scaled(hourly["rain"], _factor(units, "rain", PRECIP_TO_IN))
    showers = _scaled(hourly["showers"], _factor(units, "showers", PRECIP_TO_IN))
    snow = _scaled(hourly["snowfall"], _factor(units, "snowfall", SNOW_TO_IN))
    liquid = tuple(
        None if r is None or s is None else r + s for r, s in zip(rain, showers, strict=True)
    )
    start = datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=UTC)
    return HourlySeries(start=start, wind_mph=wind, rain_in=liquid, snow_in=snow)


def _fetch_batch(points: Sequence[LatLon], start: datetime, end: datetime) -> list[HourlySeries]:
    params = {
        "latitude": ",".join(f"{p.lat:.4f}" for p in points),
        "longitude": ",".join(f"{p.lon:.4f}" for p in points),
        "hourly": HOURLY_VARIABLES,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "start_hour": start.strftime("%Y-%m-%dT%H:%M"),
        "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
    }
    if settings.OPEN_METEO_API_KEY:
        params["apikey"] = settings.OPEN_METEO_API_KEY
    response = http.get(PROVIDER, f"{settings.OPEN_METEO_BASE_URL}/v1/forecast", params, TIMEOUT)
    data = http.parse_json(PROVIDER, response)
    if response.status_code == 429:
        raise UpstreamQuotaExceeded(
            "The weather provider's rate limit was reached. Try again later."
        )
    if response.status_code >= 500:
        raise UpstreamUnavailable("The weather provider is unavailable. Please try again.")
    if response.status_code != 200:
        reason = data.get("reason") if isinstance(data, dict) else None
        logger.error("Open-Meteo error %s: %s", response.status_code, reason)
        raise ProviderError("The weather provider could not process the request.")

    locations = data if isinstance(data, list) else [data]
    if len(locations) != len(points):
        raise UpstreamUnavailable("The weather provider returned an incomplete response.")
    try:
        return [_parse_location(raw) for raw in locations]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.error("Unexpected Open-Meteo payload: %s", type(exc).__name__)
        raise UpstreamUnavailable("The weather provider returned an invalid response.") from None


def fetch_hourly(
    points: Sequence[LatLon], start: datetime, end: datetime
) -> list[HourlySeries | None]:
    """Hourly series covering [floor(start), floor(end)] for each point (in input order).

    Returns None for a point when the window lies entirely beyond the forecast horizon.
    """
    start_hour = floor_hour(start)
    end_hour = min(floor_hour(end), floor_hour(datetime.now(UTC)) + FORECAST_HORIZON)
    if end_hour < start_hour:
        return [None] * len(points)

    keys = [quantize(p) for p in points]
    unique = list(dict.fromkeys(keys))
    cache_keys = {p: _cache_key(p, start_hour, end_hour) for p in unique}
    found: dict[LatLon, HourlySeries] = {}
    cached = cache.get_many(list(cache_keys.values()))
    for p, key in cache_keys.items():
        if key in cached:
            found[p] = cached[key]

    missing = [p for p in unique if p not in found]
    if missing:
        batches = [missing[i : i + BATCH_SIZE] for i in range(0, len(missing), BATCH_SIZE)]
        workers = min(MAX_PARALLEL_BATCHES, len(batches))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda b: _fetch_batch(b, start_hour, end_hour), batches))
        fresh = {}
        for batch, series_list in zip(batches, results, strict=True):
            for p, series in zip(batch, series_list, strict=True):
                found[p] = series
                fresh[cache_keys[p]] = series
        cache.set_many(fresh, CACHE_SECONDS)
        logger.info(
            "Open-Meteo: %d points, %d unique, %d fetched in %d batches",
            len(points),
            len(unique),
            len(missing),
            len(batches),
        )
    return [found.get(k) for k in keys]
