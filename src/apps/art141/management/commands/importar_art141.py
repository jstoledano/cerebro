import csv
from collections import defaultdict
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.art141.models import TramiteArt141, UniversoVA
from apps.pusinex.models import Localidad, Manzana, Seccion


class Command(BaseCommand):
    help = (
        "Sincroniza trámites históricos de Artículo 141 "
        "y el universo vigente de Voto Anticipado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "archivo",
            type=str,
            help="Ruta al archivo CSV de Artículo 141.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        archivo = options["archivo"]

        filas = self._leer_csv(archivo)

        if not filas:
            raise CommandError("El archivo no contiene registros.")

        datos_procesados = []

        for numero_fila, fila in enumerate(filas, start=1):
            try:
                datos = self._procesar_fila(fila)
            except Exception as exc:
                raise CommandError(
                    f"Error en fila {numero_fila}: {exc}"
                ) from exc

            datos_procesados.append(datos)

        resultado_kpi = self._sincronizar_kpi(
            datos_procesados
        )

        resultado_va = self._sincronizar_va(
            datos_procesados
        )

        self._mostrar_resultado(
            resultado_kpi,
            resultado_va,
        )

    def _leer_csv(self, archivo):
        try:
            with open(
                archivo,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as fh:
                lineas = fh.readlines()

        except FileNotFoundError as exc:
            raise CommandError(
                f"No existe el archivo: {archivo}"
            ) from exc

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
                "No se encontró el encabezado esperado."
            )

        return list(
            csv.DictReader(
                lineas[indice_encabezado:]
            )
        )

    def _procesar_fila(self, fila):
        ciudadano_id = self._texto(
            fila.get("CIUDADANO_ID")
        )

        if not ciudadano_id:
            raise ValueError("CIUDADANO_ID vacío")

        fecha_solicitud = self._fecha(
            fila.get("FECHA_SOLICITUD_AFECTACION")
        )

        if fecha_solicitud is None:
            raise ValueError(
                "FECHA_SOLICITUD_AFECTACION vacía"
            )

        entidad = self._entero(
            fila.get("ENTIDAD")
        )

        distrito = self._entero(
            fila.get("DISTRITO")
        )

        municipio = self._texto(
            fila.get("MUNICIPIO")
        )

        seccion_num = self._entero(
            fila.get("SECCION")
        )

        localidad_num = self._entero(
            fila.get("LOCALIDAD")
        )

        manzana_num = self._entero(
            fila.get("MANZANA")
        )

        seccion = None
        localidad_mge = None
        manzana = None

        if seccion_num is not None:
            seccion = (
                Seccion.objects
                .filter(
                    seccion=seccion_num,
                    activa=True,
                )
                .first()
            )

        if (
            seccion is not None
            and localidad_num is not None
        ):
            localidad_mge = (
                Localidad.objects
                .filter(
                    seccion=seccion,
                    localidad=localidad_num,
                )
                .first()
            )

        if (
            seccion is not None
            and localidad_num is not None
            and manzana_num is not None
            and manzana_num != 9999
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

        return {
            "fuar": None,

            "ciudadano_id": ciudadano_id,

            "fecha_solicitud_tramite": (
                fecha_solicitud
            ),

            "fecha_entrega_credencial": (
                self._fecha(
                    fila.get(
                        "FECHA_ENTREGA_CREDENCIAL"
                    )
                )
            ),

            "estatusciudadano_id": (
                self._entero(
                    fila.get(
                        "ESTATUSCIUDADANO_ID"
                    )
                )
            ),

            "entidad": entidad,
            "distrito": distrito,
            "municipio": municipio,
            "seccion_origen": seccion_num,
            "localidad": localidad_num,
            "manzana_origen": manzana_num,

            "seccion": seccion,
            "localidad_mge": localidad_mge,
            "manzana": manzana,

            "edad": self._entero(
                fila.get("EDAD")
            ),

            "sexo": self._texto(
                fila.get("SEXO")
            ),
        }

    def _sincronizar_kpi(self, filas):
        creados = 0
        actualizados = 0

        for datos in filas:
            defaults = datos.copy()

            ciudadano_id = defaults.pop(
                "ciudadano_id"
            )

            fecha_solicitud = defaults.pop(
                "fecha_solicitud_tramite"
            )

            _, created = (
                TramiteArt141.objects
                .update_or_create(
                    ciudadano_id=ciudadano_id,
                    fecha_solicitud_tramite=(
                        fecha_solicitud
                    ),
                    defaults=defaults,
                )
            )

            if created:
                creados += 1
            else:
                actualizados += 1

        return {
            "creados": creados,
            "actualizados": actualizados,
            "total": (
                TramiteArt141.objects.count()
            ),
        }

    def _sincronizar_va(self, filas):
        ahora = timezone.now()

        por_ciudadano = defaultdict(list)

        for datos in filas:
            por_ciudadano[
                datos["ciudadano_id"]
            ].append(datos)

        # Toda persona que existía previamente
        # parte como ausente del corte actual.
        UniversoVA.objects.update(
            presente_fuente=False,
            activo=False,
        )

        creados = 0
        actualizados = 0
        activos = 0
        inactivos = 0

        for ciudadano_id, registros in (
            por_ciudadano.items()
        ):
            registros_ln = [
                registro
                for registro in registros
                if (
                    registro[
                        "estatusciudadano_id"
                    ] == 2
                )
            ]

            if registros_ln:
                seleccionado = max(
                    registros_ln,
                    key=self._clave_orden_va,
                )
                activo = True

            else:
                seleccionado = max(
                    registros,
                    key=self._clave_orden_va,
                )
                activo = False

            defaults = {
                "activo": activo,
                "presente_fuente": True,

                "estatusciudadano_id": (
                    seleccionado[
                        "estatusciudadano_id"
                    ]
                ),

                "fecha_solicitud_tramite": (
                    seleccionado[
                        "fecha_solicitud_tramite"
                    ]
                ),

                "fecha_entrega_credencial": (
                    seleccionado[
                        "fecha_entrega_credencial"
                    ]
                ),

                "entidad": seleccionado[
                    "entidad"
                ],

                "distrito": seleccionado[
                    "distrito"
                ],

                "municipio": seleccionado[
                    "municipio"
                ],

                "seccion_origen": seleccionado[
                    "seccion_origen"
                ],

                "localidad": seleccionado[
                    "localidad"
                ],

                "manzana_origen": seleccionado[
                    "manzana_origen"
                ],

                "seccion": seleccionado[
                    "seccion"
                ],

                "localidad_mge": seleccionado[
                    "localidad_mge"
                ],

                "manzana": seleccionado[
                    "manzana"
                ],

                "edad": seleccionado[
                    "edad"
                ],

                "sexo": seleccionado[
                    "sexo"
                ],

                "ultima_presencia": ahora,
            }

            _, created = (
                UniversoVA.objects
                .update_or_create(
                    ciudadano_id=ciudadano_id,
                    defaults=defaults,
                )
            )

            if created:
                creados += 1
            else:
                actualizados += 1

            if activo:
                activos += 1
            else:
                inactivos += 1

        return {
            "creados": creados,
            "actualizados": actualizados,
            "activos": activos,
            "inactivos": inactivos,
            "total": UniversoVA.objects.count(),
        }

    @staticmethod
    def _clave_orden_va(registro):
        fecha_entrega = (
            registro[
                "fecha_entrega_credencial"
            ]
            or datetime.min.date()
        )

        fecha_solicitud = (
            registro[
                "fecha_solicitud_tramite"
            ]
            or datetime.min.date()
        )

        return (
            fecha_entrega,
            fecha_solicitud,
        )

    def _mostrar_resultado(
        self,
        resultado_kpi,
        resultado_va,
    ):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Sincronización Artículo 141 concluida."
            )
        )

        self.stdout.write("")
        self.stdout.write("KPI ARTÍCULO 141")
        self.stdout.write(
            f"Trámites creados:       "
            f"{resultado_kpi['creados']}"
        )
        self.stdout.write(
            f"Trámites actualizados:  "
            f"{resultado_kpi['actualizados']}"
        )
        self.stdout.write(
            f"Trámites históricos:    "
            f"{resultado_kpi['total']}"
        )

        self.stdout.write("")
        self.stdout.write("UNIVERSO VA")
        self.stdout.write(
            f"Personas creadas:        "
            f"{resultado_va['creados']}"
        )
        self.stdout.write(
            f"Personas actualizadas:   "
            f"{resultado_va['actualizados']}"
        )
        self.stdout.write(
            f"Personas VA activas:     "
            f"{resultado_va['activos']}"
        )
        self.stdout.write(
            f"Presentes no activas:    "
            f"{resultado_va['inactivos']}"
        )
        self.stdout.write(
            f"Personas históricas VA:  "
            f"{resultado_va['total']}"
        )

        self._mostrar_georreferencia()

    def _mostrar_georreferencia(self):
        kpi = TramiteArt141.objects.all()

        va = UniversoVA.objects.filter(
            activo=True
        )

        self.stdout.write("")
        self.stdout.write("GEOREFERENCIA KPI")
        self._mostrar_niveles(kpi)

        self.stdout.write("")
        self.stdout.write("GEOREFERENCIA VA")
        self._mostrar_niveles(va)

    def _mostrar_niveles(self, queryset):
        manzana = queryset.filter(
            manzana__isnull=False
        ).count()

        localidad = queryset.filter(
            manzana__isnull=True,
            localidad_mge__isnull=False,
        ).count()

        seccion = queryset.filter(
            manzana__isnull=True,
            localidad_mge__isnull=True,
            seccion__isnull=False,
        ).count()

        pendiente = queryset.filter(
            seccion__isnull=True
        ).count()

        self.stdout.write(
            f"Nivel manzana:           {manzana}"
        )

        self.stdout.write(
            f"Nivel localidad:         {localidad}"
        )

        self.stdout.write(
            f"Nivel sección:           {seccion}"
        )

        self.stdout.write(
            f"Georreferencia pendiente:{pendiente:>9}"
        )

    @staticmethod
    def _texto(valor):
        if valor is None:
            return ""

        return str(valor).strip()

    @staticmethod
    def _entero(valor):
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
