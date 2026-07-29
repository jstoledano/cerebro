"""Caché Redis selectivo para las páginas públicas de Cerebro."""

from django.conf import settings
from django.core.cache import caches
from django.middleware.cache import (
    FetchFromCacheMiddleware,
    UpdateCacheMiddleware,
)
from django.utils.cache import patch_vary_headers


CACHEABLE_PREFIXES = (
    "/docs/",
    "/pas/",
    "/ideas/",
    "/cartografia/",
    "/cecyrd/",
)

ALWAYS_BYPASS_PREFIXES = (
    "/admin/",
    "/login/",
    "/logout/",
    "/tinymce/",
    "/profiles/",
    "/pmml/",
    "/vozmac/",
    "/api/",
    "/assets/",
    "/media/",
    "/cartografia/paquetes/",
    "/cecyrd/carga/",
    "/cecyrd/api/etl/",
    "/cecyrd/api/revision/",
)

MUTATION_SEGMENTS = {
    "add",
    "edit",
    "delete",
    "guardar",
    "iniciar",
    "progreso",
    "setup",
    "process_add",
    "tipo_add",
    "panic",
    "panic_resolve",
    "notificaciones",
    "closure",
}


class CerebroCachePolicyMixin:
    """Determina qué solicitudes pueden compartir una respuesta cacheada."""

    @staticmethod
    def request_is_cacheable(request):
        if settings.DEBUG:
            return False

        if request.method not in {"GET", "HEAD"}:
            return False

        if request.headers.get("Authorization"):
            return False

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return False

        if settings.SESSION_COOKIE_NAME in request.COOKIES:
            return False

        path = request.path_info

        if path == "/":
            return True

        if path.startswith(ALWAYS_BYPASS_PREFIXES):
            return False

        if not path.startswith(CACHEABLE_PREFIXES):
            return False

        if path.startswith("/cecyrd/api/"):
            return path.startswith("/cecyrd/api/dashboard/")

        segments = {
            segment
            for segment in path.strip("/").split("/")
            if segment
        }

        if segments.intersection(MUTATION_SEGMENTS):
            return False

        return True


class SelectiveFetchFromCacheMiddleware(
    CerebroCachePolicyMixin,
    FetchFromCacheMiddleware,
):
    """Lee de Redis únicamente respuestas públicas y compartibles."""

    def process_request(self, request):
        eligible = self.request_is_cacheable(request)
        request._cerebro_cache_eligible = eligible

        if not eligible:
            request._cache_update_cache = False
            return None

        response = super().process_request(request)

        if response is not None:
            response["X-Cerebro-Cache"] = "HIT"

        return response


class SelectiveUpdateCacheMiddleware(
    CerebroCachePolicyMixin,
    UpdateCacheMiddleware,
):
    """Guarda páginas públicas e invalida el caché tras escrituras."""

    mutating_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def process_response(self, request, response):
        if (
            request.method in self.mutating_methods
            and 200 <= response.status_code < 400
        ):
            caches["pages"].clear()

        eligible = getattr(
            request,
            "_cerebro_cache_eligible",
            False,
        )

        update_cache = getattr(
            request,
            "_cache_update_cache",
            False,
        )

        if not eligible or not update_cache:
            if response.get("X-Cerebro-Cache") != "HIT":
                response["X-Cerebro-Cache"] = "BYPASS"
            return response

        if response.status_code != 200 or response.streaming:
            request._cache_update_cache = False
            response["X-Cerebro-Cache"] = "BYPASS"
            return response

        # Docs y PAS pueden responder HTML completo o fragmentos HTMX
        # para la misma URL. Este encabezado separa ambas variantes.
        patch_vary_headers(response, ("HX-Request",))

        response["X-Cerebro-Cache"] = "MISS"
        response["X-Cerebro-Cache-TTL"] = str(
            settings.CACHE_MIDDLEWARE_SECONDS
        )

        return super().process_response(request, response)
