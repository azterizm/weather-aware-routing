import pytest

from trips.domain.numbers import floor_decimals
from trips.domain.risk import (
    apply_load_rules,
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
)
from trips.domain.types import RiskLevel, WeatherSample

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0, L),
        (24.9, L),
        (25, M),
        (34.9, M),
        (35, H),
        (44.9, H),
        (45, S),
        (54.9, S),
        (55, N),
        (80, N),
    ],
)
def test_wind_thresholds(mph, expected):
    assert classify_wind(mph) == expected


@pytest.mark.parametrize(
    ("in_hr", "expected"),
    [
        (0, L),
        (0.09, L),
        (0.10, M),
        (0.24, M),
        (0.25, H),
        (0.49, H),
        (0.50, S),
        (1.00, S),
        (1.01, N),
    ],
)
def test_rain_thresholds(in_hr, expected):
    assert classify_rain(in_hr) == expected


@pytest.mark.parametrize(
    ("in_hr", "expected"),
    [
        (0, L),
        (0.49, L),
        (0.5, M),
        (0.99, M),
        (1.0, H),
        (1.99, H),
        (2.0, S),
        (3.0, S),
        (3.01, N),
    ],
)
def test_snow_thresholds(in_hr, expected):
    assert classify_snow(in_hr) == expected


@pytest.mark.parametrize(
    ("mph", "load", "expected_level", "expected_rule"),
    [
        # 45-54 mph: No Travel only when the load is strictly over 30,000 lb
        (45, 30_000, S, None),
        (45, 30_001, N, "wind_45_54_load_over_30000"),
        (54.9, 45_000, N, "wind_45_54_load_over_30000"),
        # 35-44 mph: Severe only when the load is strictly over 40,000 lb
        (40, 40_000, H, None),
        (40, 40_001, S, "wind_35_44_load_over_40000"),
        (35, 80_000, S, "wind_35_44_load_over_40000"),
        (44.9, 40_001, S, "wind_35_44_load_over_40000"),
        # Outside the bands the load has no effect
        (34.9, 80_000, M, None),
        # >= 55 mph is No Travel for any load (from the wind table itself)
        (55, 1, N, None),
    ],
)
def test_load_rules(mph, load, expected_level, expected_rule):
    level, rule = apply_load_rules(mph, classify_wind(mph), load)
    assert level == expected_level
    assert rule == expected_rule


def test_checkpoint_takes_worst_factor():
    risk = classify_checkpoint(WeatherSample(wind_mph=30, rain_in_hr=0.3, snow_in_hr=0.0), 10_000)
    assert (risk.wind, risk.rain, risk.snow) == (M, H, L)
    assert risk.level == H


def test_checkpoint_load_adjusted_wind_dominates():
    risk = classify_checkpoint(WeatherSample(wind_mph=38, rain_in_hr=0.0, snow_in_hr=1.2), 42_000)
    assert risk.wind == S
    assert risk.snow == H
    assert risk.level == S
    assert risk.load_rule == "wind_35_44_load_over_40000"


def test_checkpoint_without_weather_is_unknown():
    assert classify_checkpoint(None, 10_000).level is None


@pytest.mark.parametrize(
    ("value", "digits", "expected"),
    [(34.96, 1, 34.9), (0.0999, 3, 0.099), (0.29, 2, 0.29), (0.1, 3, 0.1), (55.0, 1, 55.0)],
)
def test_floor_decimals_never_rounds_up(value, digits, expected):
    assert floor_decimals(value, digits) == expected
