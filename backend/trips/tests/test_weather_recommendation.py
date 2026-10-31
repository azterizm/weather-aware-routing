from datetime import UTC, datetime, timedelta

import pytest

from trips.domain.recommendation import (
    RouteScore,
    format_duration,
    rank_routes,
    recommendation_reason,
    summarize_route,
)
from trips.domain.types import Checkpoint, CheckpointRisk, LatLon, RiskLevel, RouteSummary
from trips.domain.weather_select import HourlySeries, sample_at

START = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)

SERIES = HourlySeries(
    start=START,
    wind_mph=(10.0, 20.0, 40.0, 30.0),
    rain_in=(0.0, 0.05, 0.30, 0.0),
    snow_in=(0.0, 0.0, 0.0, 1.5),
)


def test_wind_interpolated_and_precip_uses_hour_ending_after_eta():
    sample = sample_at(SERIES, START + timedelta(minutes=30))
    assert sample.wind_mph == pytest.approx(15.0)  # halfway between 10 and 20
    assert sample.rain_in_hr == pytest.approx(0.05)  # value stamped 01:00 covers 00:00-01:00


def test_eta_exactly_on_the_hour():
    sample = sample_at(SERIES, START + timedelta(hours=1))
    assert sample.wind_mph == pytest.approx(20.0)
    assert sample.rain_in_hr == pytest.approx(0.30)  # hour 01:00-02:00 is stamped 02:00


def test_non_utc_eta_is_normalised():
    from zoneinfo import ZoneInfo

    eta = datetime(2026, 10, 31, 20, 0, tzinfo=ZoneInfo("America/New_York"))  # 00:00 UTC
    assert sample_at(SERIES, eta).wind_mph == pytest.approx(10.0)


def test_sample_outside_series_is_none():
    assert sample_at(SERIES, START + timedelta(hours=3)) is None  # needs hour 04:00 precip
    assert sample_at(SERIES, START - timedelta(minutes=1)) is None


def test_missing_value_is_none():
    series = HourlySeries(START, (10.0, None), (0.0, 0.0), (0.0, 0.0))
    assert sample_at(series, START + timedelta(minutes=10)) is None


def checkpoint(level: RiskLevel | None, covered: float) -> Checkpoint:
    return Checkpoint(
        index=0,
        mile=0,
        location=LatLon(0, 0),
        eta=START,
        covered_miles=covered,
        risk=CheckpointRisk(level=level),
    )


def test_summarize_route_weights_by_covered_miles():
    summary = summarize_route(
        [
            checkpoint(RiskLevel.LOW, 10),
            checkpoint(RiskLevel.HIGH, 20),
            checkpoint(RiskLevel.SEVERE, 10),
            checkpoint(None, 5),
        ]
    )
    assert summary.miles_by_risk["LOW"] == 10
    assert summary.miles_by_risk["HIGH"] == 20
    assert summary.miles_by_risk["SEVERE"] == 10
    assert summary.unknown_miles == 5
    assert summary.average_risk == pytest.approx((0 * 10 + 2 * 20 + 3 * 10) / 40)
    assert summary.max_risk == RiskLevel.SEVERE


def score(route_id, no_travel=0.0, severe=0.0, high=0.0, avg=0.5, time_s=3600.0):
    miles = {"LOW": 0.0, "MODERATE": 0.0, "HIGH": high, "SEVERE": severe}
    miles |= {"NO_TRAVEL": no_travel, "UNKNOWN": 0.0}
    return RouteScore(
        route_id=route_id,
        label=f"Route {route_id}",
        summary=RouteSummary(miles, avg, RiskLevel.LOW, 0.0),
        travel_time_s=time_s,
    )


@pytest.mark.parametrize(
    ("better", "worse", "reason"),
    [
        (
            score("A", no_travel=0, severe=50),
            score("B", no_travel=5),
            "Route A has the fewest No Travel miles, 0 mi against 5 mi on Route B.",
        ),
        (
            score("A", severe=10, high=90),
            score("B", severe=20, high=0),
            "Route A has the fewest Severe miles, 10 mi against 20 mi on Route B.",
        ),
        (
            score("A", high=10, avg=2.0),
            score("B", high=30, avg=0.1),
            "Route A has the fewest High miles, 10 mi against 30 mi on Route B.",
        ),
        (
            score("A", avg=0.4, time_s=9000),
            score("B", avg=0.6, time_s=100),
            "Route A has the lowest average risk, 0.40 against 0.60 on Route B.",
        ),
        (
            score("A", time_s=3600),
            score("B", time_s=4000),
            "Route A has the shortest travel time, 1 h 00 min against 1 h 07 min on Route B.",
        ),
    ],
)
def test_ranking_criteria_in_order(better, worse, reason):
    ranked = rank_routes([worse, better])
    assert [r.route_id for r in ranked] == ["A", "B"]
    assert recommendation_reason(ranked) == reason


def test_float_noise_does_not_decide_ranking():
    a = score("A", severe=10.04, time_s=3600)
    b = score("B", severe=10.01, time_s=3000)
    assert rank_routes([a, b])[0].route_id == "B"  # severe miles tie at 0.1 precision


def test_full_tie_keeps_provider_order():
    ranked = rank_routes([score("A"), score("B")])
    assert ranked[0].route_id == "A"
    assert recommendation_reason(ranked).startswith("Route A ties Route B on every criterion")


@pytest.mark.parametrize(
    ("seconds", "text"), [(14_550, "4 h 03 min"), (14_549, "4 h 02 min"), (1_500, "25 min")]
)
def test_format_duration_rounds_half_up_like_the_frontend(seconds, text):
    assert format_duration(seconds) == text


def test_single_route_reason():
    assert recommendation_reason([score("A")]) == "Only 1 route option was available."
