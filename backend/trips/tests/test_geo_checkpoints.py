from datetime import UTC, datetime, timedelta

import pytest

from trips.domain.checkpoints import (
    checkpoint_miles,
    choose_interval,
    covered_miles,
    place_checkpoints,
)
from trips.domain.geo import (
    METERS_PER_MILE,
    corridor_cells,
    cumulative_miles,
    haversine_miles,
    simplify,
)
from trips.domain.types import LatLon, Route

DEPART = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def straight_route(miles: float, n_points: int, point_times=None) -> Route:
    """A due-north route of roughly `miles` length starting at (35, -100)."""
    deg = miles / 69.0
    points = tuple(LatLon(35 + deg * i / (n_points - 1), -100.0) for i in range(n_points))
    length = cumulative_miles(points)[-1]
    return Route(
        points=points,
        length_m=length * METERS_PER_MILE,
        travel_time_s=length * 60.0,  # 60 mph
        departure=DEPART,
        arrival=DEPART + timedelta(minutes=length),
        point_times_s=point_times,
    )


def test_haversine_known_distance():
    # Dallas, TX to Denver, CO is ~663 straight-line miles.
    d = haversine_miles(LatLon(32.7767, -96.7970), LatLon(39.7392, -104.9903))
    assert d == pytest.approx(663, abs=3)


@pytest.mark.parametrize(
    ("miles", "interval"),
    [(10, 10), (249.9, 10), (250, 25), (1000, 25), (1000.1, 50), (2800, 50)],
)
def test_choose_interval(miles, interval):
    assert choose_interval(miles) == interval


def test_checkpoint_miles_include_both_ends():
    assert checkpoint_miles(60, 25) == [0, 25, 50, 60]
    assert checkpoint_miles(50, 25) == [0, 25, 50]
    assert checkpoint_miles(5, 10) == [0, 5]
    # A mark within 10% of an interval of the destination merges into it.
    assert checkpoint_miles(101, 25) == [0, 25, 50, 75, 101]


def test_covered_miles_sum_to_route_length():
    marks = checkpoint_miles(60, 25)
    covered = covered_miles(marks)
    assert covered == [12.5, 25, 17.5, 5]
    assert sum(covered) == pytest.approx(60)


def test_place_checkpoints_spacing_and_uniform_eta():
    route = straight_route(100, 50)
    cps = place_checkpoints(route, 25)
    route_miles = route.length_m / METERS_PER_MILE
    assert [round(cp.mile, 3) for cp in cps] == [0, 25, 50, 75, round(route_miles, 3)]
    assert cps[0].location == route.points[0]
    assert cps[-1].location.lat == pytest.approx(route.points[-1].lat)
    # 60 mph uniform: 25 miles -> 25 minutes
    assert (cps[1].eta - DEPART).total_seconds() == pytest.approx(25 * 60, rel=1e-3)
    assert cps[-1].eta == DEPART + timedelta(seconds=route.travel_time_s)
    etas = [cp.eta for cp in cps]
    assert etas == sorted(etas)


def test_place_checkpoints_uses_provider_point_times():
    # 3 points, ~100 miles; first half driven slowly (3 h), second half fast (1 h).
    base = straight_route(100, 3)
    route = Route(
        points=base.points,
        length_m=base.length_m,
        travel_time_s=4 * 3600,
        departure=DEPART,
        arrival=DEPART + timedelta(hours=4),
        point_times_s=(0.0, 3 * 3600.0, 4 * 3600.0),
    )
    cps = place_checkpoints(route, 25)
    half_mile = route.length_m / METERS_PER_MILE / 2
    # Mile 25 is half of the first half -> 1.5 h
    assert (cps[1].eta - DEPART).total_seconds() == pytest.approx(25 / half_mile * 3 * 3600)
    # Mile 75 lies in the fast half
    expected = 3 * 3600 + (75 - half_mile) / half_mile * 3600
    assert (cps[3].eta - DEPART).total_seconds() == pytest.approx(expected)


def test_time_profile_fills_missing_point_times():
    base = straight_route(90, 4)
    route = Route(
        points=base.points,
        length_m=base.length_m,
        travel_time_s=3 * 3600,
        departure=DEPART,
        arrival=DEPART + timedelta(hours=3),
        point_times_s=(0.0, None, None, 3 * 3600.0),
    )
    cps = place_checkpoints(route, 30)
    route_miles = route.length_m / METERS_PER_MILE
    assert (cps[1].eta - DEPART).total_seconds() == pytest.approx(30 / route_miles * 3 * 3600)


def test_simplify_keeps_endpoints_and_drops_collinear_points():
    points = [LatLon(35, -100 + i * 0.01) for i in range(100)]
    simplified = simplify(points, 0.0001)
    assert simplified == [points[0], points[-1]]


def test_simplify_keeps_corners():
    points = [LatLon(35, -100), LatLon(35, -99), LatLon(36, -99)]
    assert simplify(points, 0.01) == points


def test_corridor_cells_stay_near_route():
    route = [LatLon(35, -100), LatLon(36, -100)]
    cells = corridor_cells([route], half_width_miles=10, spacing_deg=0.1)
    assert cells
    for cell in cells:
        # Within the half-width (plus sampling tolerance) of the north-south line.
        dist = haversine_miles(cell, LatLon(min(max(cell.lat, 35), 36), -100))
        assert dist <= 10.5
    # No cell far from the route
    assert all(-100.3 <= c.lon <= -99.7 for c in cells)
