"""Weather risk classification using the project's risk and load rules.

Threshold tables are half-open intervals: a value equal to a shared endpoint belongs to the
higher level (e.g. 35 mph wind is High, 0.25 in/hr rain is High). The No Travel thresholds
for rain and snow are strict (">"), so exactly 1.00 in/hr rain or 3.0 in/hr snow is Severe.
"""

from __future__ import annotations

from dataclasses import dataclass

from .types import CheckpointRisk, RiskLevel, WeatherSample


@dataclass(frozen=True, slots=True)
class Threshold:
    level: RiskLevel
    bound: float
    inclusive: bool  # True: value >= bound reaches the level; False: value > bound


# Ordered from most to least severe. Anything below every threshold is Low.
WIND_THRESHOLDS_MPH: tuple[Threshold, ...] = (
    Threshold(RiskLevel.NO_TRAVEL, 55.0, inclusive=True),
    Threshold(RiskLevel.SEVERE, 45.0, inclusive=True),
    Threshold(RiskLevel.HIGH, 35.0, inclusive=True),
    Threshold(RiskLevel.MODERATE, 25.0, inclusive=True),
)

RAIN_THRESHOLDS_IN_HR: tuple[Threshold, ...] = (
    Threshold(RiskLevel.NO_TRAVEL, 1.00, inclusive=False),
    Threshold(RiskLevel.SEVERE, 0.50, inclusive=True),
    Threshold(RiskLevel.HIGH, 0.25, inclusive=True),
    Threshold(RiskLevel.MODERATE, 0.10, inclusive=True),
)

SNOW_THRESHOLDS_IN_HR: tuple[Threshold, ...] = (
    Threshold(RiskLevel.NO_TRAVEL, 3.0, inclusive=False),
    Threshold(RiskLevel.SEVERE, 2.0, inclusive=True),
    Threshold(RiskLevel.HIGH, 1.0, inclusive=True),
    Threshold(RiskLevel.MODERATE, 0.5, inclusive=True),
)


@dataclass(frozen=True, slots=True)
class LoadRule:
    rule_id: str
    wind_min_mph: float  # inclusive
    wind_max_mph: float  # exclusive
    load_over_lbs: float  # strictly greater than
    level: RiskLevel


# Wind >= 55 mph is No Travel for any load; that is already covered by the wind table.
LOAD_RULES: tuple[LoadRule, ...] = (
    LoadRule("wind_45_54_load_over_30000", 45.0, 55.0, 30_000, RiskLevel.NO_TRAVEL),
    LoadRule("wind_35_44_load_over_40000", 35.0, 45.0, 40_000, RiskLevel.SEVERE),
)


def _classify(value: float, thresholds: tuple[Threshold, ...]) -> RiskLevel:
    for threshold in thresholds:
        if value > threshold.bound or (threshold.inclusive and value == threshold.bound):
            return threshold.level
    return RiskLevel.LOW


def classify_wind(wind_mph: float) -> RiskLevel:
    return _classify(wind_mph, WIND_THRESHOLDS_MPH)


def classify_rain(rain_in_hr: float) -> RiskLevel:
    return _classify(rain_in_hr, RAIN_THRESHOLDS_IN_HR)


def classify_snow(snow_in_hr: float) -> RiskLevel:
    return _classify(snow_in_hr, SNOW_THRESHOLDS_IN_HR)


def apply_load_rules(
    wind_mph: float, wind_level: RiskLevel, load_lbs: float
) -> tuple[RiskLevel, str | None]:
    """Raise the wind level when a load rule applies. Returns (level, applied rule id)."""
    for rule in LOAD_RULES:
        in_band = rule.wind_min_mph <= wind_mph < rule.wind_max_mph
        if in_band and load_lbs > rule.load_over_lbs and rule.level > wind_level:
            return rule.level, rule.rule_id
    return wind_level, None


def classify_checkpoint(sample: WeatherSample | None, load_lbs: float) -> CheckpointRisk:
    """Overall checkpoint risk = worst of (load-adjusted wind, rain, snow)."""
    if sample is None:
        return CheckpointRisk(level=None)
    wind, load_rule = apply_load_rules(sample.wind_mph, classify_wind(sample.wind_mph), load_lbs)
    rain = classify_rain(sample.rain_in_hr)
    snow = classify_snow(sample.snow_in_hr)
    return CheckpointRisk(
        level=max(wind, rain, snow),
        wind=wind,
        rain=rain,
        snow=snow,
        load_rule=load_rule,
    )
