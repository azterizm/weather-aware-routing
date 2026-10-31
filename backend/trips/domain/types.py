"""Domain value types. Pure data, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class RiskLevel(IntEnum):
    """Ordered risk levels. The integer value is the risk score used for averaging."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


@dataclass(frozen=True, slots=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class Place:
    label: str
    location: LatLon


@dataclass(frozen=True, slots=True)
class Route:
    """A drivable route as returned by the routing provider.

    `point_times_s` holds the cumulative travel time (seconds from departure) for each
    polyline point when the provider supplies it; `None` entries are unknown and are
    interpolated by distance.
    """

    points: tuple[LatLon, ...]
    length_m: float
    travel_time_s: float
    departure: datetime
    arrival: datetime
    point_times_s: tuple[float | None, ...] | None = None


@dataclass(frozen=True, slots=True)
class WeatherSample:
    """Weather conditions the truck experiences at a checkpoint."""

    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class CheckpointRisk:
    level: RiskLevel | None  # None means the weather is unknown
    wind: RiskLevel | None = None
    rain: RiskLevel | None = None
    snow: RiskLevel | None = None
    load_rule: str | None = None  # identifier of the load rule that raised the wind level


@dataclass(frozen=True, slots=True)
class Checkpoint:
    index: int
    mile: float
    location: LatLon
    eta: datetime
    covered_miles: float
    weather: WeatherSample | None = None
    risk: CheckpointRisk = field(default_factory=lambda: CheckpointRisk(level=None))


@dataclass(frozen=True, slots=True)
class RouteSummary:
    miles_by_risk: dict[str, float]
    average_risk: float | None
    max_risk: RiskLevel | None
    unknown_miles: float
