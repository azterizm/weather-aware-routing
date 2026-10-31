from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("geocode/", views.GeocodeView.as_view(), name="geocode"),
    path("trips/plan/", views.TripPlanView.as_view(), name="trip-plan"),
    path("trips/corridor-weather/", views.CorridorWeatherView.as_view(), name="corridor-weather"),
    path("tiles/<int:zoom>/<int:x>/<int:y>.png", views.MapTileView.as_view(), name="map-tile"),
]
