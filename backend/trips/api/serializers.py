"""Request validation. Responses are built in presenters.py."""

from __future__ import annotations

from datetime import timedelta

import polyline
from django.utils import timezone
from rest_framework import serializers

from ..domain.geo import haversine_miles
from ..domain.types import LatLon, Place

MAX_LOAD_LBS = 80_000
DEPARTURE_PAST_SLACK = timedelta(minutes=15)  # tolerate client clock skew
DEPARTURE_MAX_AHEAD = timedelta(days=7)  # keeps the whole trip inside the forecast horizon
CORRIDOR_PAST_SLACK = timedelta(hours=1)  # the heatmap is requested right after the plan
MAX_ENCODED_ROUTE_CHARS = 200_000
MIN_TRIP_MILES = 0.5


class AwareDateTimeField(serializers.DateTimeField):
    """ISO 8601 date-time that must carry a UTC offset; naive values are rejected."""

    default_error_messages = {"naive": "Include a UTC offset, such as 2026-11-01T08:00:00-05:00."}

    def enforce_timezone(self, value):
        if timezone.is_naive(value):
            self.fail("naive")
        return super().enforce_timezone(value)


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=300)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        return Place(label=values["label"], location=LatLon(values["lat"], values["lon"]))


class LoadWeightField(serializers.FloatField):
    def __init__(self, **kwargs):
        super().__init__(min_value=1, max_value=MAX_LOAD_LBS, **kwargs)


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=3, max_length=100, trim_whitespace=True)


class TripPlanRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure_time = AwareDateTimeField()
    load_weight_lbs = LoadWeightField()

    def validate_departure_time(self, value):
        now = timezone.now()
        if value < now - DEPARTURE_PAST_SLACK:
            raise serializers.ValidationError("Departure time cannot be in the past.")
        if value > now + DEPARTURE_MAX_AHEAD:
            raise serializers.ValidationError("Departure must be within the next 7 days.")
        return value

    def validate(self, attrs):
        origin, destination = attrs["origin"], attrs["destination"]
        if haversine_miles(origin.location, destination.location) < MIN_TRIP_MILES:
            raise serializers.ValidationError("Origin and destination must be different places.")
        return attrs


class EncodedRouteField(serializers.CharField):
    """Google encoded polyline (precision 5), decoded to a list of LatLon."""

    def __init__(self, **kwargs):
        super().__init__(max_length=MAX_ENCODED_ROUTE_CHARS, trim_whitespace=False, **kwargs)

    def to_internal_value(self, data):
        encoded = super().to_internal_value(data)
        try:
            points = [LatLon(lat, lon) for lat, lon in polyline.decode(encoded, 5)]
        except (ValueError, IndexError, TypeError):
            raise serializers.ValidationError("Invalid encoded polyline.") from None
        if len(points) < 2 or not all(-90 <= p.lat <= 90 and -180 <= p.lon <= 180 for p in points):
            raise serializers.ValidationError("Invalid encoded polyline.")
        return points


class CorridorRequestSerializer(serializers.Serializer):
    routes = serializers.ListField(child=EncodedRouteField(), min_length=1, max_length=3)
    start_time = AwareDateTimeField()
    load_weight_lbs = LoadWeightField()

    def validate_start_time(self, value):
        now = timezone.now()
        if value < now - CORRIDOR_PAST_SLACK or value > now + DEPARTURE_MAX_AHEAD:
            raise serializers.ValidationError("Start time must be within the next 7 days.")
        return value
