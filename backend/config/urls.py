from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import include, path
from django.views.decorators.http import require_safe


@require_safe
def spa_index(request):
    """Serve the built single-page app. Hashed assets are served by WhiteNoise."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HttpResponseNotFound(
            "Frontend not built. Run `make dev-frontend` or `npm run build` in frontend/.",
            content_type="text/plain",
        )
    response = HttpResponse(index.read_bytes(), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    return response


urlpatterns = [
    path("api/", include("trips.api.urls")),
    path("", spa_index, name="spa-index"),
]
