"""JSON representations of service results. Times are UTC ISO 8601 with a `Z` suffix."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ..domain.geo import METERS_PER_MILE
from ..domain.numbers import floor_decimals
from ..domain.recommendation import UNKNOWN
from ..domain.types import Checkpoint, Place
from ..services.corridor import CorridorForecast
from ..services.trip_planner import PlannedRoute, TripPlan


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def place_json(place: Place) -> dict:
    return {"label": place.label, "lat": place.location.lat, "lon": place.location.lon}


def checkpoint_json(cp: Checkpoint) -> dict:
    weather = cp.weather
    risk = cp.risk
    return {
        "index": cp.index,
        "mile": round(cp.mile, 1),
        "lat": round(cp.location.lat, 5),
        "lon": round(cp.location.lon, 5),
        "eta": iso(cp.eta),
        "weather": None
        if weather is None
        else {
            "wind_mph": floor_decimals(weather.wind_mph, 1),
            "rain_in_hr": floor_decimals(weather.rain_in_hr, 3),
            "snow_in_hr": floor_decimals(weather.snow_in_hr, 3),
        },
        "risk": risk.level.name if risk.level is not None else UNKNOWN,
        "factors": None
        if risk.level is None
        else {
            "wind": risk.wind.name,
            "rain": risk.rain.name,
            "snow": risk.snow.name,
            "load_rule": risk.load_rule,
        },
    }


def route_json(planned: PlannedRoute) -> dict:
    route = planned.route
    summary = planned.summary
    return {
        "id": planned.route_id,
        "label": planned.label,
        "distance_miles": round(route.length_m / METERS_PER_MILE, 1),
        "duration_seconds": round(route.travel_time_s),
        "departure_time": iso(route.departure),
        "arrival_time": iso(route.departure + timedelta(seconds=route.travel_time_s)),
        "geometry": planned.geometry,
        "summary": {
            "miles_by_risk": summary.miles_by_risk,
            "average_risk": summary.average_risk,
            "max_risk": summary.max_risk.name if summary.max_risk is not None else None,
        },
        "checkpoints": [checkpoint_json(cp) for cp in planned.checkpoints],
    }


def plan_json(plan: TripPlan) -> dict:
    return {
        "departure_time": iso(plan.departure),
        "load_weight_lbs": plan.load_lbs,
        "checkpoint_interval_miles": plan.interval_miles,
        "recommended_route_id": plan.recommended_route_id,
        "recommendation_reason": plan.recommendation_reason,
        "warnings": plan.warnings,
        "routes": [route_json(r) for r in plan.routes],
    }


def corridor_json(forecast: CorridorForecast) -> dict:
    return {
        "hours": [iso(h) for h in forecast.hours],
        "cell_size_deg": forecast.cell_size_deg,
        "cells": [[c.lat, c.lon] for c in forecast.cells],
        "risk": forecast.risk,
        "wind_mph": forecast.wind_mph,
        "rain_in_hr": forecast.rain_in_hr,
        "snow_in_hr": forecast.snow_in_hr,
    }
