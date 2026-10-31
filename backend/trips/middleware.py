import logging
import time

logger = logging.getLogger("trips.requests")


class RequestTimingMiddleware:
    """Logs method, path, status and duration for API requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s %s %.0fms", request.method, request.path, response.status_code, elapsed_ms
            )
        return response
