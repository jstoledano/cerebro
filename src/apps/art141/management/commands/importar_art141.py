import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.art141.models import RegistroArt141
from apps.pusinex.models import Manzana, Seccion


class Command(BaseCommand):
    help = "Sincroniza registros de trámites realizados bajo el artículo 141."

    def add_arguments(self, parser):
        parser.add_argument(
            "archivo",
            type=str,
            help="Ruta al archivo CSV de trámites Artículo 141.",
        )

    def handle(self, *args, **options):
        archivo = Path(options["archivo"])

        if not archivo.exists():
            raise CommandError(f"No existe el archivo: {archivo}")

        filas = self._leer_csv(archivo)

        creados = 0
        actualizados = 0

        sin_seccion_mge = 0
        sin_manzana_mge = 0

        for numero_fila, fila in enumerate(filas, start=1):
            try:
                datos, estado_mge = self._procesar_fila(
                    fila,
                    numero_fila,
                )
            except Exception as exc:
                raise CommandError(
                    f"Error en fila {numero_fila}: {exc}"
                ) from exc

            ciudadano_id = datos.pop("ciudadano_id")
            fecha_solicitud_tramite = datos.pop(
                "fecha_solicitud_tramite"
            )

            _, created = RegistroArt141.objects.update_or_create(
                ciudadano_id=ciudadano_id,
                fecha_solicitud_tramite=fecha_solicitud_tramite,
                defaults=datos,
            )

            if created:
                creados += 1
            else:
                actualizados += 1

            if estado_mge == "sin_seccion":
                sin_seccion_mge += 1

            elif estado_mge == "sin_manzana":
                sin_manzana_mge += 1

        total = RegistroArt141.objects.count()

        personas = (
            RegistroArt141.objects
            .values("ciudadano_id")
            .distinct()
            .count()
        )

        personas_ln = (
            RegistroArt141.objects
            .filter(estatusciudadano_id=2)
            .values("ciudadano_id")
            .distinct()
            .count()
        )

        entregadas = (
            RegistroArt141.objects
            .exclude(fecha_entrega_credencial__isnull=True)
            .count()
        )

        sin_entrega = (
            RegistroArt141.objects
            .filter(fecha_entrega_credencial__isnull=True)
            .count()
        )

        secciones_origen = (
            RegistroArt141.objects
            .values("seccion_origen")
            .distinct()
            .count()
        )

        manzanas_origen = (
            RegistroArt141.objects
            .values(
                "seccion_origen",
                "localidad",
                "manzana_origen",
            )
            .distinct()
            .count()
        )

        con_georreferencia_valida = (
            RegistroArt141.objects
            .exclude(seccion__isnull=True)
            .count()
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Sincronización Artículo 141 concluida."
            )
        )
        self.stdout.write("")
        self.stdout.write(
            f"Registros creados:            {creados}"
        )
        self.stdout.write(
            f"Registros actualizados:       {actualizados}"
        )
        self.stdout.write(
            f"Registros en la base:         {total}"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Personas identificadas:       {personas}"
        )
        self.stdout.write(
            f"Personas en Lista Nominal:    {personas_ln}"
        )
        self.stdout.write(
            f"Credenciales entregadas:      {entregadas}"
        )
        self.stdout.write(
            f"Sin fecha de entrega:         {sin_entrega}"
        )
        self.stdout.write(
            f"Secciones de origen:          {secciones_origen}"
        )
        self.stdout.write(
            f"Manzanas de origen:           {manzanas_origen}"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Con georreferencia válida:    {con_georreferencia_valida}"
        )
        self.stdout.write(
            f"Georreferencia pendiente:     {sin_seccion_mge}"
        )
        self.stdout.write("")
        self.stdout.write(
            f"Sin referencia de manzana:    {sin_manzana_mge}"
        )

    def _leer_csv(self, archivo):
        with archivo.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as fh:
            lineas = fh.readlines()

        indice_encabezado = None

        for indice, linea in enumerate(lineas):
            if (
                "CIUDADANO_ID" in linea
                and "FECHA_SOLICITUD_AFECTACION" in linea
            ):
                indice_encabezado = indice
                break

        if indice_encabezado is None:
            raise CommandError(
                "No se encontró el encabezado esperado con "
                "CIUDADANO_ID y FECHA_SOLICITUD_AFECTACION."
            )

        return csv.DictReader(
            lineas[indice_encabezado:]
        )

    def _procesar_fila(self, fila, numero_fila):
        ciudadano_id = self._texto(
            fila.get("CIUDADANO_ID")
        )

        if not ciudadano_id:
            raise ValueError("CIUDADANO_ID vacío")

        fecha_solicitud_tramite = self._fecha(
            fila.get("FECHA_SOLICITUD_AFECTACION")
        )

        if fecha_solicitud_tramite is None:
            raise ValueError(
                "FECHA_SOLICITUD_AFECTACION vacía"
            )

        entidad = self._entero_opcional(
            fila.get("ENTIDAD")
        )

        distrito = self._entero_opcional(
            fila.get("DISTRITO")
        )

        municipio = self._texto(
            fila.get("MUNICIPIO")
        )

        seccion_num = self._entero_opcional(
            fila.get("SECCION")
        )

        localidad_num = self._entero_opcional(
            fila.get("LOCALIDAD")
        )

        manzana_num = self._entero_opcional(
            fila.get("MANZANA")
        )

        seccion = None
        manzana = None
        estado_mge = "completo"

        if seccion_num is not None:
            seccion = (
                Seccion.objects
                .filter(seccion=seccion_num)
                .first()
            )

        if seccion is None:
            estado_mge = "sin_seccion"

        elif (
            localidad_num is not None
            and manzana_num is not None
        ):
            manzana = (
                Manzana.objects
                .filter(
                    seccion=seccion,
                    localidad=localidad_num,
                    manzana=manzana_num,
                )
                .first()
            )

            if manzana is None:
                estado_mge = "sin_manzana"

        datos = {
            "fuar": None,
            "ciudadano_id": ciudadano_id,
            "fecha_solicitud_tramite": fecha_solicitud_tramite,
            "fecha_entrega_credencial": self._fecha(
                fila.get("FECHA_ENTREGA_CREDENCIAL")
            ),
            "estatusciudadano_id": self._entero_opcional(
                fila.get("ESTATUSCIUDADANO_ID")
            ),
            "entidad": entidad,
            "distrito": distrito,
            "municipio": municipio,
            "seccion_origen": seccion_num,
            "localidad": localidad_num,
            "manzana_origen": manzana_num,
            "seccion": seccion,
            "manzana": manzana,
            "edad": self._entero_opcional(
                fila.get("EDAD")
            ),
            "sexo": self._texto(
                fila.get("SEXO")
            ),
        }

        return datos, estado_mge

    @staticmethod
    def _texto(valor):
        if valor is None:
            return ""

        return str(valor).strip()

    @staticmethod
    def _entero_opcional(valor):
        valor = (valor or "").strip()

        if not valor:
            return None

        try:
            return int(valor)
        except ValueError as exc:
            raise ValueError(
                f"Valor entero inválido: {valor}"
            ) from exc

    @staticmethod
    def _fecha(valor):
        valor = (valor or "").strip()

        if not valor:
            return None

        formatos = (
            "%d/%m/%Y",
            "%Y-%m-%d",
        )

        for formato in formatos:
            try:
                return datetime.strptime(
                    valor,
                    formato,
                ).date()

            except ValueError:
                continue

        raise ValueError(
            f"Fecha no reconocida: {valor}"
        )
