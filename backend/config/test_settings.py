"""Settings for the test suite: deterministic, no real secrets, no real API keys."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")

from .settings import *  # noqa: F403
from .settings import REST_FRAMEWORK

DEBUG = False
TOMTOM_API_KEY = "test-tomtom-key"
OPEN_METEO_API_KEY = ""
OPEN_METEO_BASE_URL = "https://api.open-meteo.com"
SECURE_SSL_REDIRECT = False
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": dict.fromkeys(["geocode", "plan", "corridor", "tiles"], "1000/min"),
}
