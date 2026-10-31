"""Weather risk heatmap along the trip corridor for 0-48 hours after departure."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings

from ..domain.geo import corridor_cells, simplify
from ..domain.numbers import floor_decimals
from ..domain.risk import classify_checkpoint
from ..domain.types import LatLon
from ..domain.weather_select import floor_hour, sample_at
from ..providers import open_meteo

logger = logging.getLogger("trips.services.corridor")

FORECAST_HOURS = 48
HALF_WIDTH_MILES = 25.0
MIN_SPACING_DEG = 0.1
ROUTE_SIMPLIFY_DEG = 0.02
UNKNOWN_RISK = -1


@dataclass(frozen=True, slots=True)
class CorridorForecast:
    hours: list[datetime]
    cell_size_deg: float
    cells: list[LatLon]
    risk: list[list[int]]  # [hour][cell]; UNKNOWN_RISK when the forecast is missing
    wind_mph: list[list[float | None]]
    rain_in_hr: list[list[float | None]]
    snow_in_hr: list[list[float | None]]


def corridor_grid(routes: Sequence[Sequence[LatLon]], max_cells: int) -> tuple[float, list[LatLon]]:
    """Corridor cells, coarsening the grid until there are at most `max_cells`."""
    spacing = MIN_SPACING_DEG
    cells = corridor_cells(routes, HALF_WIDTH_MILES, spacing)
    while len(cells) > max_cells:
        spacing *= max(1.1, math.sqrt(len(cells) / max_cells))
        cells = corridor_cells(routes, HALF_WIDTH_MILES, spacing)
    return spacing, cells


def build_corridor_forecast(
    route_lines: Sequence[Sequence[LatLon]], start: datetime, load_lbs: float
) -> CorridorForecast:
    routes = [simplify(line, ROUTE_SIMPLIFY_DEG) for line in route_lines]
    spacing, cells = corridor_grid(routes, settings.CORRIDOR_MAX_CELLS)

    first_hour = floor_hour(start)
    hours = [first_hour + timedelta(hours=h) for h in range(FORECAST_HOURS + 1)]
    # Precipitation for the last hour is stamped one hour later.
    series_list = open_meteo.fetch_hourly(cells, hours[0], hours[-1] + timedelta(hours=1))

    risk, wind, rain, snow = [], [], [], []
    for hour in hours:
        risk_row, wind_row, rain_row, snow_row = [], [], [], []
        for series in series_list:
            sample = sample_at(series, hour) if series is not None else None
            level = classify_checkpoint(sample, load_lbs).level
            risk_row.append(UNKNOWN_RISK if level is None else int(level))
            wind_row.append(floor_decimals(sample.wind_mph, 1) if sample else None)
            rain_row.append(floor_decimals(sample.rain_in_hr, 3) if sample else None)
            snow_row.append(floor_decimals(sample.snow_in_hr, 3) if sample else None)
        risk.append(risk_row)
        wind.append(wind_row)
        rain.append(rain_row)
        snow.append(snow_row)

    logger.info("Corridor forecast: %d cells at %.3f deg spacing", len(cells), spacing)
    return CorridorForecast(
        hours=hours,
        cell_size_deg=round(spacing, 5),
        cells=cells,
        risk=risk,
        wind_mph=wind,
        rain_in_hr=rain,
        snow_in_hr=snow,
    )
