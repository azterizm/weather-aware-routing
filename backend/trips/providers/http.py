"""Shared HTTP plumbing for third-party providers: retries, timeouts, typed errors.

Provider URLs carry API keys in the query string, so nothing here ever logs or re-raises a
full URL: messages are built from the provider name and status only.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("trips.providers")

# (connect, read) seconds. Callers pick read timeouts so a whole API request stays inside
# Heroku's 30 s router limit.
DEFAULT_TIMEOUT = (3.05, 10)

_SECRET_PARAM = re.compile(r"(?i)\b(key|apikey)=[^&\s'\"]+")


class ProviderError(Exception):
    """An upstream provider failed. `status` and `code` drive the API error response."""

    status = 502
    code = "upstream_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UpstreamUnavailable(ProviderError):
    status = 503
    code = "upstream_unavailable"


class UpstreamQuotaExceeded(ProviderError):
    status = 503
    code = "quota_exceeded"


class NoRouteFound(ProviderError):
    status = 422
    code = "no_route"


def redact(text: str) -> str:
    return _SECRET_PARAM.sub(r"\1=***", text)


def build_session() -> requests.Session:
    # Connection failures and 429/5xx responses are retried; read timeouts are not, because
    # a slow upstream rarely gets faster and retries would exceed the request budget.
    retry = Retry(
        total=2,
        connect=2,
        read=0,
        status=1,
        backoff_factor=0.3,
        status_forcelist=(429, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=False,  # a long Retry-After would blow the request budget
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = "weather-aware-routing/1.0"
    return session


session = build_session()


def get(
    provider: str, url: str, params: Any, timeout: tuple[float, float] = DEFAULT_TIMEOUT
) -> requests.Response:
    """GET with retries. Network failures become UpstreamUnavailable (without the URL)."""
    started = time.perf_counter()
    try:
        response = session.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        logger.warning("%s request failed: %s", provider, redact(type(exc).__name__))
        raise UpstreamUnavailable(f"{provider} did not respond. Please try again.") from None
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("%s %s %.0fms", provider, response.status_code, elapsed_ms)
    return response


def parse_json(provider: str, response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        raise UpstreamUnavailable(f"{provider} returned an invalid response.") from None
