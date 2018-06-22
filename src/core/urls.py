# coding: utf-8
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from core.views import index
from dpi import views as dpi

router = DefaultRouter()
router.register(r'dpi', dpi.ExpedienteIncompletoViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('auth/', include('djoser.urls.authtoken')),
    path('admin/', admin.site.urls),
    path('metas/', include('metas.urls')),
    path('dpi/', include('dpi.urls')),
    path('docs/', include('docs.urls')),
    path('mesas/', include('mesas.urls')),
    path('', index, name='index')
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
