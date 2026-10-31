from __future__ import annotations

from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.response import Response
from rest_framework.views import APIView

from ..providers import tomtom
from ..services.corridor import build_corridor_forecast
from ..services.trip_planner import plan_trip
from .presenters import corridor_json, place_json, plan_json
from .serializers import (
    CorridorRequestSerializer,
    GeocodeQuerySerializer,
    TripPlanRequestSerializer,
)


class HealthView(APIView):
    throttle_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class GeocodeView(APIView):
    """GET /api/geocode/?q= — place suggestions for the trip form."""

    throttle_scope = "geocode"

    def get(self, request):
        query = GeocodeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        places = tomtom.search_places(query.validated_data["q"])
        return Response({"results": [place_json(p) for p in places]})


class TripPlanView(APIView):
    """POST /api/trips/plan/ — route options with checkpoints, risk and a recommendation."""

    throttle_scope = "plan"

    def post(self, request):
        body = TripPlanRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        plan = plan_trip(
            origin=data["origin"],
            destination=data["destination"],
            departure=data["departure_time"],
            load_lbs=data["load_weight_lbs"],
        )
        return Response(plan_json(plan))


class CorridorWeatherView(APIView):
    """POST /api/trips/corridor-weather/ — risk heatmap for 0-48 h after departure."""

    throttle_scope = "corridor"

    def post(self, request):
        body = CorridorRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        forecast = build_corridor_forecast(
            data["routes"], data["start_time"], data["load_weight_lbs"]
        )
        return Response(corridor_json(forecast))


class FirstRendererNegotiation(BaseContentNegotiation):
    """Tiles are images; error bodies still use the first (JSON) renderer whatever the
    browser's image Accept header says."""

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class MapTileView(APIView):
    """GET /api/tiles/{z}/{x}/{y}.png — TomTom map tiles proxied so the API key stays private.

    Any failure returns an error status, which makes the map load that tile from
    OpenStreetMap instead.
    """

    throttle_scope = "tiles"
    content_negotiation_class = FirstRendererNegotiation

    def get(self, request, zoom: int, x: int, y: int):
        limit = 2**zoom
        if zoom > tomtom.MAX_TILE_ZOOM or x >= limit or y >= limit:
            raise NotFound("No map tile exists at these coordinates.")
        response = HttpResponse(tomtom.fetch_tile(zoom, x, y), content_type="image/png")
        response["Cache-Control"] = "public, max-age=86400"
        # PNG is already compressed; this keeps GZipMiddleware from spending CPU on it.
        response["Content-Encoding"] = "identity"
        return response
