"""Route summaries and recommendation ranking. Pure functions, no I/O.

Routes are ranked lexicographically by:
  1. fewest No Travel miles (strictly worse than Severe, so it is compared first)
  2. fewest Severe miles
  3. fewest High miles
  4. lowest average risk (mile-weighted)
  5. shortest travel time
Miles are rounded to 0.1 and average risk to 0.01 so float noise cannot decide a ranking.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .types import Checkpoint, RiskLevel, RouteSummary

UNKNOWN = "UNKNOWN"
RISK_KEYS = [level.name for level in RiskLevel] + [UNKNOWN]


def summarize_route(checkpoints: Sequence[Checkpoint]) -> RouteSummary:
    miles = dict.fromkeys(RISK_KEYS, 0.0)
    weighted = 0.0
    known_miles = 0.0
    max_risk: RiskLevel | None = None
    for cp in checkpoints:
        level = cp.risk.level
        if level is None:
            miles[UNKNOWN] += cp.covered_miles
            continue
        miles[level.name] += cp.covered_miles
        weighted += int(level) * cp.covered_miles
        known_miles += cp.covered_miles
        max_risk = level if max_risk is None else max(max_risk, level)
    average = weighted / known_miles if known_miles > 0 else None
    return RouteSummary(
        miles_by_risk={key: round(value, 1) for key, value in miles.items()},
        average_risk=round(average, 2) if average is not None else None,
        max_risk=max_risk,
        unknown_miles=round(miles[UNKNOWN], 1),
    )


@dataclass(frozen=True, slots=True)
class RouteScore:
    route_id: str
    label: str
    summary: RouteSummary
    travel_time_s: float


def ranking_key(score: RouteScore) -> tuple[float, float, float, float, float]:
    miles = score.summary.miles_by_risk
    average = score.summary.average_risk
    return (
        round(miles[RiskLevel.NO_TRAVEL.name], 1),
        round(miles[RiskLevel.SEVERE.name], 1),
        round(miles[RiskLevel.HIGH.name], 1),
        round(average, 2) if average is not None else math.inf,
        score.travel_time_s,
    )


def rank_routes(scores: Sequence[RouteScore]) -> list[RouteScore]:
    """Best route first. The sort is stable, so full ties keep the provider's order."""
    return sorted(scores, key=ranking_key)


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"


def recommendation_reason(ranked: Sequence[RouteScore]) -> str:
    """One sentence naming the first criterion on which the winner beats the runner-up."""
    if not ranked:
        return ""
    if len(ranked) == 1:
        return "Only one route option was available."
    best, other = ranked[0], ranked[1]
    best_key, other_key = ranking_key(best), ranking_key(other)
    labels = (
        "Fewest No Travel miles",
        "Fewest Severe miles",
        "Fewest High miles",
        "Lowest average risk",
        "Shortest travel time",
    )
    for criterion, (mine, theirs) in enumerate(zip(best_key, other_key, strict=True)):
        if mine == theirs:
            continue
        if criterion < 3:
            values = f"{mine:g} mi vs {theirs:g} mi"
        elif criterion == 3:
            values = f"{mine:.2f} vs {theirs:.2f}"
        else:
            values = f"{format_duration(mine)} vs {format_duration(theirs)}"
        return f"{labels[criterion]}: {values} on {other.label}."
    return f"Tied with {other.label} on every criterion; listed first by the routing provider."
