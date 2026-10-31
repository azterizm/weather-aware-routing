"""Shared test helpers: fixtures on disk and a fake Open-Meteo endpoint."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

FIXTURES = Path(__file__).parent / "fixtures"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TOMTOM_ROUTE_URL_PREFIX = "https://api.tomtom.com/routing/1/calculateRoute/"
TOMTOM_SEARCH_URL_PREFIX = "https://api.tomtom.com/search/2/search/"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def open_meteo_callback(
    wind_mph=5.0, rain_in=0.0, showers_in=0.0, snow=0.0, units=None, calls=None
):
    """A `responses` callback returning constant hourly weather for each requested location."""
    unit_map = {
        "time": "iso8601",
        "wind_speed_10m": "mp/h",
        "rain": "inch",
        "showers": "inch",
        "snowfall": "inch",
    }
    unit_map |= units or {}

    def callback(request):
        query = parse_qs(urlparse(request.url).query)
        lats = query["latitude"][0].split(",")
        lons = query["longitude"][0].split(",")
        start = datetime.fromisoformat(query["start_hour"][0])
        end = datetime.fromisoformat(query["end_hour"][0])
        count = int((end - start) / timedelta(hours=1)) + 1
        times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(count)]
        if calls is not None:
            calls.append(len(lats))
        body = [
            {
                "latitude": float(lat),
                "longitude": float(lon),
                "hourly_units": unit_map,
                "hourly": {
                    "time": times,
                    "wind_speed_10m": [wind_mph] * count,
                    "rain": [rain_in] * count,
                    "showers": [showers_in] * count,
                    "snowfall": [snow] * count,
                },
            }
            for lat, lon in zip(lats, lons, strict=True)
        ]
        payload = body if len(body) > 1 else body[0]
        return 200, {"Content-Type": "application/json"}, json.dumps(payload)

    return callback
