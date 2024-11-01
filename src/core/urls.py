# coding: utf-8
"""Patrones de rutas generales."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from core.views import Index


urlpatterns = [
    path('login/', LoginView.as_view(template_name="login.html"), name='login'),
    path('logout/', LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('docs/', include('apps.docs.urls')),
    path('carto/', include('apps.carto.urls')),
    path('ideas/', include('apps.ideas.urls')),
    path('pas/', include('apps.pas.urls')),
    path('', Index.as_view(), name='index')

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
