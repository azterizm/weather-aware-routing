"""Checkpoint placement along a route and ETA estimation. Pure functions, no I/O."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from .geo import METERS_PER_MILE, cumulative_miles, locate_along, point_along
from .types import Checkpoint, Route

# Sampling interval (miles) by trip length; the same interval is used for every route option.
SHORT_TRIP_MAX_MILES = 250.0  # below this: 10 mi
MEDIUM_TRIP_MAX_MILES = 1000.0  # up to and including this: 25 mi; above: 50 mi


def choose_interval(shortest_route_miles: float) -> int:
    if shortest_route_miles < SHORT_TRIP_MAX_MILES:
        return 10
    if shortest_route_miles <= MEDIUM_TRIP_MAX_MILES:
        return 25
    return 50


# A regular mark this close to the destination (fraction of the interval) is merged into it.
END_MERGE_FRACTION = 0.1


def checkpoint_miles(route_miles: float, interval: float) -> list[float]:
    """Mile markers 0, N, 2N, ... plus the destination."""
    marks: list[float] = []
    mile = 0.0
    while mile == 0.0 or mile < route_miles - interval * END_MERGE_FRACTION:
        marks.append(mile)
        mile += interval
    marks.append(route_miles)
    return marks


def covered_miles(marks: Sequence[float]) -> list[float]:
    """Each checkpoint covers half the distance to each neighbour; the total equals the route."""
    if len(marks) == 1:
        return [0.0]
    covered = []
    for i in range(len(marks)):
        before = (marks[i] - marks[i - 1]) / 2 if i > 0 else 0.0
        after = (marks[i + 1] - marks[i]) / 2 if i < len(marks) - 1 else 0.0
        covered.append(before + after)
    return covered


def time_profile(route: Route, cum: Sequence[float]) -> list[float]:
    """Cumulative travel time (s) at each polyline point, monotonic non-decreasing.

    Uses provider per-point times where available and fills gaps by distance between the
    nearest known neighbours. Without per-point data it assumes a uniform speed.
    """
    n = len(cum)
    total = cum[-1] if n else 0.0
    known: list[float | None] = [None] * n
    if route.point_times_s is not None and len(route.point_times_s) == n:
        known = list(route.point_times_s)
    known[0] = 0.0
    known[-1] = route.travel_time_s

    times = [0.0] * n
    prev_i = 0
    for i in range(1, n):
        value = known[i]
        if value is None:
            continue
        span = cum[i] - cum[prev_i]
        start_t = times[prev_i]
        for k in range(prev_i + 1, i):
            frac = (cum[k] - cum[prev_i]) / span if span > 0 else 0.0
            times[k] = start_t + (value - start_t) * frac
        times[i] = value
        prev_i = i
    if total == 0:
        return [0.0] * n

    # Guard against provider noise: travel time can never decrease along the route.
    running = 0.0
    for i in range(n):
        running = max(running, times[i])
        times[i] = running
    return times


def place_checkpoints(route: Route, interval_miles: float) -> list[Checkpoint]:
    """Checkpoints every `interval_miles` (plus the destination) with ETAs; no weather yet."""
    points = route.points
    cum = cumulative_miles(points)
    poly_miles = cum[-1]
    route_miles = route.length_m / METERS_PER_MILE
    # Mile markers follow the provider's route length; the polyline length differs slightly.
    scale = poly_miles / route_miles if route_miles > 0 else 1.0
    times = time_profile(route, cum)

    marks = checkpoint_miles(route_miles, interval_miles)
    checkpoints = []
    for index, (mile, cover) in enumerate(zip(marks, covered_miles(marks), strict=True)):
        d = mile * scale
        elapsed = 0.0
        if len(points) > 1:
            i, fraction = locate_along(cum, d)
            elapsed = times[i] + (times[i + 1] - times[i]) * fraction
        checkpoints.append(
            Checkpoint(
                index=index,
                mile=mile,
                location=point_along(points, cum, d),
                eta=route.departure + timedelta(seconds=elapsed),
                covered_miles=cover,
            )
        )
    return checkpoints
