"""Selecting the weather a truck experiences at a given time from an hourly forecast.

Open-Meteo hourly semantics:
- wind_speed_10m is an instantaneous value at the timestamp, so it is linearly interpolated
  between the two surrounding hours.
- rain, showers and snowfall are totals for the *preceding* hour, so the value stamped
  floor_hour(t) + 1h covers the hour the truck is driving through; that total is the rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .types import WeatherSample

ONE_HOUR = timedelta(hours=1)


def floor_hour(t: datetime) -> datetime:
    return t.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """Hourly forecast for one location. `start` is the UTC time of the first value."""

    start: datetime
    wind_mph: tuple[float | None, ...]
    rain_in: tuple[float | None, ...]  # rain + showers, preceding-hour total (inches)
    snow_in: tuple[float | None, ...]  # snowfall, preceding-hour total (inches)

    def value_at(self, values: tuple[float | None, ...], t: datetime) -> float | None:
        offset = (t - self.start) / ONE_HOUR
        index = round(offset)
        if abs(offset - index) > 1e-9 or not 0 <= index < len(values):
            return None
        return values[index]


def sample_at(series: HourlySeries, t: datetime) -> WeatherSample | None:
    """Weather at time `t`, or None when the forecast does not cover it."""
    t = t.astimezone(UTC)
    hour = floor_hour(t)
    fraction = (t - hour) / ONE_HOUR

    wind_start = series.value_at(series.wind_mph, hour)
    wind_end = series.value_at(series.wind_mph, hour + ONE_HOUR) if fraction > 0 else wind_start
    rain = series.value_at(series.rain_in, hour + ONE_HOUR)
    snow = series.value_at(series.snow_in, hour + ONE_HOUR)
    if wind_start is None or wind_end is None or rain is None or snow is None:
        return None

    wind = wind_start + (wind_end - wind_start) * fraction
    return WeatherSample(
        wind_mph=max(0.0, wind),
        rain_in_hr=max(0.0, rain),
        snow_in_hr=max(0.0, snow),
    )
