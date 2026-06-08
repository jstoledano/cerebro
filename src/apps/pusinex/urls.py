from django.urls import path

from apps.pusinex.views import (
    VNM2024,
    Administration,
    CreatePUSINEX,
    Index,
    MunicipioDetail,
    PusinexDetail,
    PUSINEXLastUpdate,
    PUSINEXZip,
    VNMZipView,
    DistritoDetail,
    SeccionDetail,
)

app_name = "pusinex"
urlpatterns = [
    path('vnm/', VNM2024.as_view(), name='vnm'),
    path('vnm/<int:dto>', VNMZipView.as_view(), name='vnmZip'),
    path('pusinex/<int:pk>', PusinexDetail.as_view(), name='pusinex'),
    path('seccion/<int:pk>', SeccionDetail.as_view(), name='seccion'),
    path('municipio/<int:pk>', MunicipioDetail.as_view(), name='municipio'),
    path('distrito/<int:pk>', DistritoDetail.as_view(), name='distrito'),
    path('creation/', CreatePUSINEX.as_view(), name='create'),
    path('bgd/', Administration.as_view(), name='bgd'),
    path('paquete/', PUSINEXZip.as_view(), name='paquete'),
    path('latest/', PUSINEXLastUpdate.as_view(), name='latest'),
    path('', Index.as_view(), name='index')
]
