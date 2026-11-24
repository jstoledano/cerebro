"""Interfaz protegida para ejecutar el comando importar_zores_ares desde PUSINEX.

El CSV llega como archivo temporal al comando existente. La operacion se limita
al distrito del expediente desde el que se invoca; no se alteran otros distritos.
"""
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.contrib.auth.decorators import login_required, permission_required
from django.core.management import call_command
from django.core.management.base import CommandError
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .management.commands.importar_zores_ares import leer_csv
from .models import Distrito, Seccion


MAX_CSV_BYTES = 2 * 1024 * 1024


@login_required
@permission_required("pusinex.change_zore", raise_exception=True)
@require_http_methods(["GET", "POST"])
def cargar_zore_are(request, distrito):
    distrito_obj = get_object_or_404(Distrito, pk=distrito)
    contexto = {"distrito": distrito_obj}
    if request.method == "GET":
        return render(request, "pusinex/zore_are_carga.html", contexto)

    archivo = request.FILES.get("archivo")
    if archivo is None or not archivo.name.lower().endswith(".csv"):
        contexto["error"] = "Selecciona un archivo CSV válido."
        return render(request, "pusinex/zore_are_carga.html", contexto, status=400)
    if archivo.size > MAX_CSV_BYTES:
        contexto["error"] = "El archivo excede el máximo permitido de 2 MB."
        return render(request, "pusinex/zore_are_carga.html", contexto, status=400)

    aplicar = request.POST.get("accion") == "aplicar"
    if aplicar and request.POST.get("confirmar") != "si":
        contexto["error"] = "Confirma expresamente el reemplazo antes de aplicar."
        return render(request, "pusinex/zore_are_carga.html", contexto, status=400)

    ruta = None
    try:
        with NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as temporal:
            ruta = Path(temporal.name)
            for bloque in archivo.chunks():
                temporal.write(bloque)
        filas = leer_csv(ruta)
        numeros = {fila["seccion"] for fila in filas}
        ubicaciones = dict(
            Seccion.objects.filter(pk__in=numeros).values_list("pk", "distrito_id")
        )
        desconocidas = numeros - set(ubicaciones)
        if desconocidas:
            raise CommandError(
                "Secciones desconocidas en el MGE: " +
                ", ".join(f"{n:04d}" for n in sorted(desconocidas)[:20])
            )
        ajenas = sorted(sec for sec, dist in ubicaciones.items() if dist != distrito)
        if ajenas:
            raise CommandError(
                f"El archivo incluye secciones ajenas al distrito {distrito:02d}: " +
                ", ".join(f"{n:04d}" for n in ajenas[:20])
            )

        salida = StringIO()
        errores = StringIO()
        call_command(
            "importar_zores_ares", str(ruta),
            simular=not aplicar, permitir_incompleto=False,
            stdout=salida, stderr=errores,
        )
        contexto["resultado"] = salida.getvalue()
        contexto["diagnostico"] = errores.getvalue()
        contexto["aplicado"] = aplicar
    except (CommandError, OSError, UnicodeError, ValueError) as exc:
        contexto["error"] = str(exc)
    finally:
        if ruta is not None:
            ruta.unlink(missing_ok=True)
    return render(request, "pusinex/zore_are_carga.html", contexto)
