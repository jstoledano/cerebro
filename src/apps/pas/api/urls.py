from rest_framework.routers import DefaultRouter

from .views import (
    PlanViewSet,
    AccionViewSet,
    EvidenciaViewSet,
)


router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="pas-plan")
router.register(r"actions", AccionViewSet, basename="pas-accion")
router.register(
    r"evidences",
    EvidenciaViewSet,
    basename="pas-evidencia",
)

urlpatterns = router.urls
