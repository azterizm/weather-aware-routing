"""Django settings for the weather-aware routing API.

All deploy-specific values come from environment variables. For local development a
`.env` file at the repository root is loaded (real environment variables win).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env", override=False)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool) -> bool:
    value = env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")
    SECRET_KEY = "dev-only-insecure-secret-key"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "rest_framework",
    "trips",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "trips.middleware.RequestTimingMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# The API is stateless: nothing is persisted, so no database is configured.
DATABASES: dict = {}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "weather-aware-routing",
        "OPTIONS": {"MAX_ENTRIES": 5000},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Frontend (built SPA served by WhiteNoise) -------------------------------------------
FRONTEND_DIST = Path(env("FRONTEND_DIST", str(REPO_ROOT / "frontend" / "dist")))
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.is_dir() else None
WHITENOISE_MAX_AGE = 0 if DEBUG else 3600


def _is_hashed_asset(path: str, url: str) -> bool:
    # Vite emits content-hashed file names under /assets/, so they can be cached forever.
    return url.startswith("/assets/")


WHITENOISE_IMMUTABLE_FILE_TEST = _is_hashed_asset

# --- Django REST Framework ---------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "trips.api.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "geocode": env("THROTTLE_GEOCODE", "60/min"),
        "plan": env("THROTTLE_PLAN", "20/min"),
        "corridor": env("THROTTLE_CORRIDOR", "20/min"),
    },
    "NUM_PROXIES": 1 if not DEBUG else None,
}

# --- Third-party providers ---------------------------------------------------------------
TOMTOM_API_KEY = env("TOMTOM_API_KEY")
TOMTOM_BASE_URL = env("TOMTOM_BASE_URL", "https://api.tomtom.com")
GEOCODE_COUNTRY_SET = env("GEOCODE_COUNTRY_SET", "US")

OPEN_METEO_API_KEY = env("OPEN_METEO_API_KEY")
OPEN_METEO_BASE_URL = env(
    "OPEN_METEO_BASE_URL",
    "https://customer-api.open-meteo.com" if OPEN_METEO_API_KEY else "https://api.open-meteo.com",
)

# Maximum number of corridor heatmap cells (each cell is one Open-Meteo location).
CORRIDOR_MAX_CELLS = int(env("CORRIDOR_MAX_CELLS", "250"))

# --- Security ----------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
# OpenStreetMap's tile usage policy requires a Referer on tile requests; this sends only
# the site origin to other HTTPS sites (the browser default).
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]

# --- Logging -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # urllib3 logs full request URLs (including API keys) at DEBUG level.
        "urllib3": {"level": "WARNING"},
        "django.request": {"level": "ERROR"},
    },
}
