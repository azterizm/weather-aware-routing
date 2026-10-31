import re
from datetime import UTC, datetime, timedelta

import pytest
import requests
import responses

from trips.domain.types import LatLon
from trips.providers import open_meteo, tomtom
from trips.providers.http import (
    NoRouteFound,
    ProviderError,
    UpstreamQuotaExceeded,
    UpstreamUnavailable,
    redact,
)

from .helpers import (
    OPEN_METEO_URL,
    TOMTOM_ROUTE_URL_PREFIX,
    TOMTOM_SEARCH_URL_PREFIX,
    load_fixture,
    open_meteo_callback,
)

ROUTE_URL = re.compile(re.escape(TOMTOM_ROUTE_URL_PREFIX) + ".*")
SEARCH_URL = re.compile(re.escape(TOMTOM_SEARCH_URL_PREFIX) + ".*")
DALLAS, DENVER = LatLon(32.7767, -96.797), LatLon(39.7392, -104.9903)


def test_redact_hides_api_keys():
    text = "GET /x?key=abc123&lat=1 and apikey=zzz"
    assert redact(text) == "GET /x?key=***&lat=1 and apikey=***"


@responses.activate
def test_search_places_parses_and_caches():
    responses.get(SEARCH_URL, json=load_fixture("tomtom_search_denver.json"))
    places = tomtom.search_places("Denver")
    assert places[0].label == "Denver, CO"
    assert places[0].location.lat == pytest.approx(39.738453)
    assert tomtom.search_places("  denver ") == places  # normalised query hits the cache
    assert len(responses.calls) == 1
    assert "key=test-tomtom-key" in responses.calls[0].request.url
    assert "countrySet=US" in responses.calls[0].request.url


@responses.activate
def test_calculate_routes_parses_fixture():
    responses.get(ROUTE_URL, json=load_fixture("tomtom_route_dallas_denver.json"))
    depart = datetime(2026, 11, 1, 12, tzinfo=UTC)
    routes = tomtom.calculate_routes([DALLAS, DENVER], depart, max_alternatives=2)
    assert len(routes) == 3
    first = routes[0]
    assert first.length_m == 1419954
    assert first.travel_time_s == 42715
    assert first.departure.tzinfo is not None
    assert first.point_times_s[0] == 0
    assert first.point_times_s[-1] == 42715
    assert any(t is None for t in first.point_times_s)  # progress is sparse
    url = responses.calls[0].request.url
    assert "travelMode=truck" in url
    assert "maxAlternatives=2" in url
    assert "departAt=2026-11-01T12%3A00%3A00%2B00%3A00" in url


@responses.activate
def test_calculate_routes_departs_now_without_time():
    responses.get(ROUTE_URL, json=load_fixture("tomtom_route_dallas_denver.json"))
    tomtom.calculate_routes([DALLAS, DENVER], None)
    assert "departAt=now" in responses.calls[0].request.url


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (403, {"detailedError": {"code": "Forbidden"}}, UpstreamQuotaExceeded),
        (429, {}, UpstreamQuotaExceeded),
        (400, {"detailedError": {"code": "NO_ROUTE_FOUND"}}, NoRouteFound),
        (400, {"detailedError": {"code": "BAD_INPUT"}}, ProviderError),
        (500, {}, UpstreamUnavailable),
    ],
)
@responses.activate
def test_calculate_routes_error_mapping(status, body, error):
    responses.get(ROUTE_URL, json=body, status=status)
    with pytest.raises(error):
        tomtom.calculate_routes([DALLAS, DENVER], None)


@responses.activate
def test_network_failure_message_never_contains_the_key():
    responses.get(ROUTE_URL, body=requests.ConnectionError("url: /x?key=test-tomtom-key"))
    with pytest.raises(UpstreamUnavailable) as info:
        tomtom.calculate_routes([DALLAS, DENVER], None)
    assert "test-tomtom-key" not in str(info.value)
    assert info.value.__cause__ is None


NOW = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)


@responses.activate
def test_fetch_hourly_dedupes_quantized_points_and_caches():
    calls = []
    responses.add_callback(responses.GET, OPEN_METEO_URL, callback=open_meteo_callback(calls=calls))
    points = [LatLon(35.001, -100.001), LatLon(35.002, -100.002), LatLon(36.0, -101.0)]
    result = open_meteo.fetch_hourly(points, NOW, NOW + timedelta(hours=3))
    assert calls == [2]  # first two points share a 0.05 degree cell
    assert result[0] is result[1]
    assert result[0].start == NOW
    assert len(result[2].wind_mph) == 4

    open_meteo.fetch_hourly(points, NOW, NOW + timedelta(hours=3))
    assert calls == [2]  # served from cache


@responses.activate
def test_fetch_hourly_batches_large_requests():
    calls = []
    responses.add_callback(responses.GET, OPEN_METEO_URL, callback=open_meteo_callback(calls=calls))
    points = [LatLon(30 + i * 0.1, -100.0) for i in range(150)]
    result = open_meteo.fetch_hourly(points, NOW, NOW + timedelta(hours=1))
    assert sorted(calls) == [50, 100]
    assert all(series is not None for series in result)


@responses.activate
def test_fetch_hourly_converts_units_and_sums_rain_and_showers():
    responses.add_callback(
        responses.GET,
        OPEN_METEO_URL,
        callback=open_meteo_callback(
            wind_mph=16.09344,
            rain_in=2.54,
            showers_in=2.54,
            snow=2.54,
            units={"wind_speed_10m": "km/h", "rain": "mm", "showers": "mm", "snowfall": "cm"},
        ),
    )
    (series,) = open_meteo.fetch_hourly([LatLon(35, -100)], NOW, NOW + timedelta(hours=1))
    assert series.wind_mph[0] == pytest.approx(10.0)
    assert series.rain_in[0] == pytest.approx(0.2)
    assert series.snow_in[0] == pytest.approx(1.0)


@responses.activate
def test_fetch_hourly_rejects_unknown_units():
    responses.add_callback(
        responses.GET,
        OPEN_METEO_URL,
        callback=open_meteo_callback(units={"snowfall": "furlong"}),
    )
    with pytest.raises(UpstreamUnavailable):
        open_meteo.fetch_hourly([LatLon(35, -100)], NOW, NOW + timedelta(hours=1))


@responses.activate
def test_fetch_hourly_beyond_horizon_returns_none_without_calling():
    start = NOW + timedelta(days=20)
    assert open_meteo.fetch_hourly([LatLon(35, -100)], start, start + timedelta(hours=2)) == [None]
    assert len(responses.calls) == 0


@pytest.mark.parametrize(
    ("status", "error"),
    [(429, UpstreamQuotaExceeded), (400, ProviderError), (503, UpstreamUnavailable)],
)
@responses.activate
def test_fetch_hourly_error_mapping(status, error):
    responses.get(OPEN_METEO_URL, json={"error": True, "reason": "bad"}, status=status)
    with pytest.raises(error):
        open_meteo.fetch_hourly([LatLon(35, -100)], NOW, NOW + timedelta(hours=1))
