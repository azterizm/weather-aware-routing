from __future__ import annotations

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
