import re
from datetime import UTC, datetime, timedelta

import polyline
import pytest
import responses
from rest_framework.test import APIClient

from trips.domain.types import LatLon, Route
from trips.services import route_options

from .helpers import (
    OPEN_METEO_URL,
    TOMTOM_ROUTE_URL_PREFIX,
    TOMTOM_SEARCH_URL_PREFIX,
    load_fixture,
    open_meteo_callback,
)

ROUTE_URL = re.compile(re.escape(TOMTOM_ROUTE_URL_PREFIX) + ".*")
SEARCH_URL = re.compile(re.escape(TOMTOM_SEARCH_URL_PREFIX) + ".*")


@pytest.fixture
def client():
    return APIClient()


def future(hours: float = 2) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def plan_body(**overrides):
    body = {
        "origin": {"label": "Dallas, TX", "lat": 32.7767, "lon": -96.797},
        "destination": {"label": "Denver, CO", "lat": 39.7392, "lon": -104.9903},
        "departure_time": future(),
        "load_weight_lbs": 42000,
    }
    return body | overrides


def test_health(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_geocode_requires_three_characters(client):
    response = client.get("/api/geocode/", {"q": "ab"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid"
    assert "q" in body["fields"]


@responses.activate
def test_geocode_returns_places(client):
    responses.get(SEARCH_URL, json=load_fixture("tomtom_search_denver.json"))
    response = client.get("/api/geocode/", {"q": "denver"})
    assert response.status_code == 200
    assert response.json()["results"][0] == {
        "label": "Denver, CO",
        "lat": 39.738453,
        "lon": -104.984853,
    }


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"departure_time": "2026-11-01T08:00:00"}, "departure_time"),  # no UTC offset
        ({"departure_time": future(-1)}, "departure_time"),
        ({"departure_time": future(24 * 8)}, "departure_time"),
        ({"load_weight_lbs": 0}, "load_weight_lbs"),
        ({"load_weight_lbs": 80001}, "load_weight_lbs"),
        ({"origin": {"label": "x", "lat": 95, "lon": 0}}, "origin"),
    ],
)
def test_plan_validation_errors(client, overrides, field):
    response = client.post("/api/trips/plan/", plan_body(**overrides), format="json")
    assert response.status_code == 400
    assert field in response.json()["fields"]


def test_plan_rejects_same_origin_and_destination(client):
    body = plan_body(destination={"label": "Dallas", "lat": 32.7768, "lon": -96.7971})
    response = client.post("/api/trips/plan/", body, format="json")
    assert response.status_code == 400
    assert response.json()["detail"] == "Origin and destination must be different places."


@responses.activate
def test_plan_happy_path(client):
    responses.get(ROUTE_URL, json=load_fixture("tomtom_route_dallas_denver.json"))
    # 38 mph everywhere: High by the wind table, Severe for a load over 40,000 lb.
    responses.add_callback(responses.GET, OPEN_METEO_URL, callback=open_meteo_callback(38.0))

    response = client.post("/api/trips/plan/", plan_body(), format="json")
    assert response.status_code == 200
    body = response.json()
    assert len(responses.calls) == 2  # one routing call (3 routes) + one weather batch
    assert body["checkpoint_interval_miles"] == 25  # shortest route ~798 mi
    assert [r["label"] for r in body["routes"]] == ["Route A", "Route B", "Route C"]
    assert body["warnings"] == []

    first = body["routes"][0]
    assert first["distance_miles"] == pytest.approx(882.3, abs=0.1)
    cps = first["checkpoints"]
    assert cps[0]["mile"] == 0
    assert cps[1]["mile"] == 25
    assert cps[-1]["mile"] == first["distance_miles"]
    assert [cp["eta"] for cp in cps] == sorted(cp["eta"] for cp in cps)
    assert cps[1]["risk"] == "SEVERE"
    assert cps[1]["factors"]["load_rule"] == "wind_35_44_load_over_40000"
    assert cps[1]["weather"]["wind_mph"] == 38.0
    assert first["summary"]["miles_by_risk"]["SEVERE"] == pytest.approx(882.3, abs=0.2)
    assert len(polyline.decode(first["geometry"])) >= 2

    # Severe everywhere, so the shortest route by distance (Route B, ~798 mi) has the fewest
    # miles at Severe and wins on the first criterion.
    assert body["recommended_route_id"] == "route-2"
    assert body["recommendation_reason"].startswith("Route B has the fewest miles at Severe")


@responses.activate
def test_plan_calm_weather_recommends_fastest(client):
    responses.get(ROUTE_URL, json=load_fixture("tomtom_route_dallas_denver.json"))
    responses.add_callback(responses.GET, OPEN_METEO_URL, callback=open_meteo_callback(5.0))
    body = client.post("/api/trips/plan/", plan_body(), format="json").json()
    # All Low: average risk ties at 0, so the fastest route (Route A, 42,715 s) wins.
    assert body["recommended_route_id"] == "route-1"
    assert body["recommendation_reason"].startswith("Route A has the shortest travel time")


@responses.activate
def test_plan_light_load_is_not_raised(client):
    responses.get(ROUTE_URL, json=load_fixture("tomtom_route_dallas_denver.json"))
    responses.add_callback(responses.GET, OPEN_METEO_URL, callback=open_meteo_callback(38.0))
    response = client.post("/api/trips/plan/", plan_body(load_weight_lbs=40000), format="json")
    checkpoint = response.json()["routes"][0]["checkpoints"][1]
    assert checkpoint["risk"] == "HIGH"
    assert checkpoint["factors"]["load_rule"] is None


@responses.activate
def test_plan_upstream_failure_is_503(client):
    responses.get(ROUTE_URL, json={}, status=503)
    response = client.post("/api/trips/plan/", plan_body(), format="json")
    assert response.status_code == 503
    assert response.json()["code"] == "upstream_unavailable"


@responses.activate
def test_plan_no_route_is_422(client):
    responses.get(ROUTE_URL, json={"detailedError": {"code": "NO_ROUTE_FOUND"}}, status=400)
    response = client.post("/api/trips/plan/", plan_body(), format="json")
    assert response.status_code == 422
    assert response.json()["code"] == "no_route"


def corridor_body(**overrides):
    line = polyline.encode([(32.7767, -96.797), (35.0, -99.0), (39.7392, -104.9903)], 5)
    body = {"routes": [line], "start_time": future(), "load_weight_lbs": 42000}
    return body | overrides


@responses.activate
def test_corridor_weather_happy_path(client, settings):
    settings.CORRIDOR_MAX_CELLS = 120
    responses.add_callback(responses.GET, OPEN_METEO_URL, callback=open_meteo_callback(48.0))
    response = client.post("/api/trips/corridor-weather/", corridor_body(), format="json")
    assert response.status_code == 200
    body = response.json()
    assert len(body["hours"]) == 49
    assert 0 < len(body["cells"]) <= 120
    assert len(body["risk"]) == 49
    assert len(body["risk"][0]) == len(body["cells"])
    assert body["risk"][0][0] == 4  # 48 mph with > 30,000 lb is No Travel
    assert body["wind_mph"][0][0] == 48.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"routes": ["not a polyline!"]},
        {"routes": []},
        {"routes": ["_p~iF~ps|U"] * 4},
        {"start_time": "2026-11-01T08:00:00"},
    ],
)
def test_corridor_validation_errors(client, overrides):
    body = corridor_body(**overrides)
    response = client.post("/api/trips/corridor-weather/", body, format="json")
    assert response.status_code == 400


# --- Route options fallback ----------------------------------------------------------------

DEPART = datetime(2026, 11, 1, tzinfo=UTC)


def fake_route(points, length_m=100_000.0) -> Route:
    return Route(
        points=tuple(points),
        length_m=length_m,
        travel_time_s=3600,
        departure=DEPART,
        arrival=DEPART + timedelta(hours=1),
    )


def test_route_options_adds_distinct_detours(monkeypatch):
    origin, destination = LatLon(35, -100), LatLon(36, -100)
    main = fake_route([origin, LatLon(35.5, -100.0), destination])

    def fake_calculate(locations, depart_at, max_alternatives=0, timeout=None):
        if len(locations) == 2:
            return [main]
        via = locations[1]
        return [fake_route([origin, via, destination], length_m=120_000)]

    monkeypatch.setattr(route_options.tomtom, "calculate_routes", fake_calculate)
    routes, warnings = route_options.get_route_options(origin, destination, None)
    assert len(routes) == 3
    assert warnings == []
    # Via points lie on opposite sides of the north-south line
    assert routes[1].points[1].lon * routes[2].points[1].lon > 0
    assert {round(routes[1].points[1].lon, 2), round(routes[2].points[1].lon, 2)} != {-100.0}


def test_route_options_rejects_long_or_duplicate_detours(monkeypatch):
    origin, destination = LatLon(35, -100), LatLon(36, -100)
    main = fake_route([origin, LatLon(35.5, -100.0), destination])

    def fake_calculate(locations, depart_at, max_alternatives=0, timeout=None):
        if len(locations) == 2:
            return [main]
        if locations[1].lon > -100:
            return [fake_route(main.points, length_m=110_000)]  # same path as main
        return [fake_route([origin, locations[1], destination], length_m=200_000)]  # too long

    monkeypatch.setattr(route_options.tomtom, "calculate_routes", fake_calculate)
    routes, warnings = route_options.get_route_options(origin, destination, None)
    assert len(routes) == 1
    assert warnings == ["Only 1 distinct route option was found for this trip."]


# --- Map tile proxy --------------------------------------------------------------------------

TILE_URL = re.compile(re.escape("https://api.tomtom.com/map/1/tile/basic/main/") + ".*")
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@responses.activate
def test_tile_proxy_returns_png_and_hides_the_key(client):
    responses.get(TILE_URL, body=PNG, content_type="image/png")
    response = client.get("/api/tiles/5/7/12.png", HTTP_ACCEPT="image/avif,image/webp,image/*")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["Cache-Control"] == "public, max-age=86400"
    assert response.content == PNG
    assert "key=test-tomtom-key" in responses.calls[0].request.url
    assert b"test-tomtom-key" not in response.content


@pytest.mark.parametrize(
    "path", ["/api/tiles/19/0/0.png", "/api/tiles/2/4/0.png", "/api/tiles/2/0/4.png"]
)
def test_tile_proxy_rejects_out_of_range_tiles(client, path):
    assert client.get(path, HTTP_ACCEPT="image/*").status_code == 404


@pytest.mark.parametrize(
    ("status", "body", "content_type", "expected"),
    [
        (500, b"", "text/plain", 503),
        (403, b"", "text/plain", 503),
        (400, b"<error/>", "text/xml", 502),
        (200, b"<html>", "text/html", 503),
    ],
)
@responses.activate
def test_tile_proxy_failures_return_error_status(client, status, body, content_type, expected):
    # An error status is what makes the map switch that tile to OpenStreetMap.
    responses.get(TILE_URL, body=body, status=status, content_type=content_type)
    response = client.get("/api/tiles/5/7/12.png", HTTP_ACCEPT="image/*")
    assert response.status_code == expected
