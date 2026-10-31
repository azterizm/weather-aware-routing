"""Plan a trip: routes -> checkpoints with ETAs -> weather -> risk -> summaries -> ranking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import polyline

from ..domain.checkpoints import choose_interval, place_checkpoints
from ..domain.geo import METERS_PER_MILE, simplify
from ..domain.recommendation import (
    RouteScore,
    rank_routes,
    recommendation_reason,
    summarize_route,
)
from ..domain.risk import classify_checkpoint
from ..domain.types import Checkpoint, Place, RiskLevel, Route, RouteSummary
from ..domain.weather_select import sample_at
from ..providers import open_meteo
from .route_options import get_route_options

logger = logging.getLogger("trips.services.trip_planner")

# Display geometry tolerance (~30 m). Checkpoints are always computed on the full geometry.
DISPLAY_SIMPLIFY_DEG = 0.0003
ROUTE_LABELS = ("Route A", "Route B", "Route C")


@dataclass(frozen=True, slots=True)
class PlannedRoute:
    route_id: str
    label: str
    route: Route
    geometry: str  # encoded polyline (precision 5) of the simplified geometry
    checkpoints: list[Checkpoint]
    summary: RouteSummary


@dataclass(frozen=True, slots=True)
class TripPlan:
    departure: datetime
    load_lbs: float
    interval_miles: int
    routes: list[PlannedRoute]
    recommended_route_id: str
    recommendation_reason: str
    warnings: list[str]


def _with_weather(
    checkpoints: list[Checkpoint], series_list: list, load_lbs: float
) -> list[Checkpoint]:
    result = []
    for cp, series in zip(checkpoints, series_list, strict=True):
        sample = sample_at(series, cp.eta) if series is not None else None
        result.append(replace(cp, weather=sample, risk=classify_checkpoint(sample, load_lbs)))
    return result


def plan_trip(origin: Place, destination: Place, departure: datetime, load_lbs: float) -> TripPlan:
    now = datetime.now(UTC)
    effective_departure = max(departure.astimezone(UTC), now)
    # TomTom computes traffic for "now" itself; explicit times are only needed in the future.
    depart_param = effective_departure if effective_departure - now > timedelta(minutes=1) else None

    routes, warnings = get_route_options(origin.location, destination.location, depart_param)
    interval = choose_interval(min(r.length_m for r in routes) / METERS_PER_MILE)
    per_route = [place_checkpoints(route, interval) for route in routes]

    # One batched weather lookup for every checkpoint of every route.
    flat = [cp for cps in per_route for cp in cps]
    etas = [cp.eta for cp in flat]
    series = open_meteo.fetch_hourly(
        [cp.location for cp in flat], min(etas), max(etas) + timedelta(hours=1)
    )

    planned: list[PlannedRoute] = []
    offset = 0
    for index, (route, cps) in enumerate(zip(routes, per_route, strict=True)):
        enriched = _with_weather(cps, series[offset : offset + len(cps)], load_lbs)
        offset += len(cps)
        simplified = simplify(route.points, DISPLAY_SIMPLIFY_DEG)
        planned.append(
            PlannedRoute(
                route_id=f"route-{index + 1}",
                label=ROUTE_LABELS[index],
                route=route,
                geometry=polyline.encode([(p.lat, p.lon) for p in simplified], 5),
                checkpoints=enriched,
                summary=summarize_route(enriched),
            )
        )

    ranked = rank_routes(
        [RouteScore(p.route_id, p.label, p.summary, p.route.travel_time_s) for p in planned]
    )
    best = next(p for p in planned if p.route_id == ranked[0].route_id)

    unknown = sum(1 for p in planned for cp in p.checkpoints if cp.risk.level is None)
    if unknown:
        warnings.append(
            f"Weather was unavailable for {unknown} checkpoint(s); they are shown as Unknown "
            "and excluded from average risk."
        )
    no_travel_miles = best.summary.miles_by_risk[RiskLevel.NO_TRAVEL.name]
    if no_travel_miles > 0:
        warnings.append(
            f"Even the recommended route has {no_travel_miles:g} mi of No Travel conditions."
        )

    logger.info(
        "Planned trip: %d routes, %d-mile interval, %d checkpoints",
        len(planned),
        interval,
        len(flat),
    )
    return TripPlan(
        departure=effective_departure,
        load_lbs=load_lbs,
        interval_miles=interval,
        routes=planned,
        recommended_route_id=best.route_id,
        recommendation_reason=recommendation_reason(ranked),
        warnings=warnings,
    )
