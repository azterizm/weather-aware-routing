import math


def floor_decimals(value: float, digits: int) -> float:
    """Round down for display, so a shown value never crosses a risk threshold upward
    (e.g. 34.96 mph is Moderate and must not display as 35.0)."""
    scale = 10**digits
    return math.floor(value * scale + 1e-6) / scale
