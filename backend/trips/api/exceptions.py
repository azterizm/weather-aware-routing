"""Uniform JSON error bodies: {"detail": str, "code": str, "fields"?: {...}}."""

from __future__ import annotations

import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from ..providers.http import ProviderError

logger = logging.getLogger("trips.api")


def _first_message(errors) -> str | None:
    if isinstance(errors, list) and errors:
        return _first_message(errors[0])
    if isinstance(errors, dict) and errors:
        return _first_message(next(iter(errors.values())))
    return str(errors) if errors else None


def api_exception_handler(exc, context):
    if isinstance(exc, ProviderError):
        return Response({"detail": exc.message, "code": exc.code}, status=exc.status)

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {"detail": "Something went wrong. Please try again.", "code": "server_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        fields = response.data if isinstance(response.data, dict) else {}
        non_field = fields.pop("non_field_errors", None)
        response.data = {
            "detail": _first_message(non_field) or "Please correct the highlighted fields.",
            "code": "invalid",
            "fields": fields,
        }
    elif isinstance(exc, exceptions.Throttled):
        response.data = {
            "detail": f"Too many requests. Try again in {exc.wait or 1:.0f} s.",
            "code": "throttled",
        }
    else:
        response.data = {"detail": str(exc.detail), "code": exc.default_code}
    return response
