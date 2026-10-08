import calendar
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.art141.config import (
    ANIO_INICIO_VA,
    PLAZO_MAXIMO_VA_MESES,
)
from apps.art141.models import TramiteArt141, UniversoVA
from apps.pusinex.models import Localidad, Manzana, Seccion


class Command(BaseCommand):
    help = (
        "Sincroniza el histórico de trámites Artículo 141 "
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
        archivo = Path(options["archivo"])

        if not archivo.exists():
            raise CommandError(
                f"No existe el archivo: {archivo}"
            )

        filas = self._leer_csv(archivo)

        if not filas:
            raise CommandError(
                "El archivo no contiene registros."
            )

        datos_procesados = []

        for numero_fila, fila in enumerate(
            filas,
            start=1,
        ):
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
        lineas = None

        for encoding in (
            "utf-8-sig",
            "cp1252",
            "latin-1",
        ):
            try:
                with archivo.open(
                    "r",
                    encoding=encoding,
                    newline="",
                ) as fh:
                    lineas = fh.readlines()

                break

            except UnicodeDecodeError:
                continue

        if lineas is None:
            raise CommandError(
                "No fue posible determinar la "
                "codificación del archivo."
            )

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
        fuar = self._texto(
            fila.get("FUAR")
        )

        if not fuar:
            raise ValueError("FUAR vacío")

        if len(fuar) > 13:
            raise ValueError(
                f"FUAR inválido: {fuar}"
            )

        ciudadano_id = self._texto(
            fila.get("CIUDADANO_ID")
        )

        if not ciudadano_id:
            raise ValueError(
                "CIUDADANO_ID vacío"
            )

        fecha_solicitud = self._fecha(
            fila.get(
                "FECHA_SOLICITUD_AFECTACION"
            )
        )

        if fecha_solicitud is None:
            raise ValueError(
                "FECHA_SOLICITUD_AFECTACION vacía"
            )

        entidad = self._entidad(
            fila.get("ENTIDAD_TRAMITE")
            or fila.get("ENTIDAD")
        )

        distrito = self._entero(
            fila.get("DISTRITO_TRAMITE")
            or fila.get("DISTRITO")
        )

        municipio = self._texto(
            fila.get("MUNICIPIO_TRAMITE")
            or fila.get("MUNICIPIO")
        )

        seccion_num = self._entero(
            fila.get("SECCION_TRAMITE")
            or fila.get("SECCION")
        )

        localidad_num = self._entero(
            fila.get("LOCALIDAD_TRAMITE")
            or fila.get("LOCALIDAD")
        )

        manzana_num = self._entero(
            fila.get("MANZANA_TRAMITE")
            or fila.get("MANZANA")
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

        estatusciudadano_id = self._entero(
            fila.get("ESTATUSCIUDADANO_ID")
        )

        lista_nominal = self._booleano_si_no(
            fila.get("LISTA_NOMINAL")
        )

        presente_padron_actual = (
            self._booleano_si_no(
                fila.get(
                    "PRESENTE_PADRON_ACTUAL"
                )
            )
        )

        return {
            "fuar": fuar,
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
                estatusciudadano_id
            ),
            "lista_nominal": lista_nominal,
            "presente_padron_actual": (
                presente_padron_actual
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
                fila.get("EDAD_CALCULADA")
                or fila.get("EDAD")
            ),
            "sexo": self._texto(
                fila.get("SEXO")
            ),
        }

    def _sincronizar_kpi(self, filas):
        eliminados_legacy = (
            TramiteArt141.objects
            .filter(fuar__isnull=True)
            .delete()[0]
        )

        creados = 0
        actualizados = 0

        for datos in filas:
            defaults = self._datos_modelo(
                datos
            )

            fuar = defaults.pop("fuar")

            _, created = (
                TramiteArt141.objects
                .update_or_create(
                    fuar=fuar,
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
            "eliminados_legacy": (
                eliminados_legacy
            ),
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
            elegibles = [
                registro
                for registro in registros
                if self._es_elegible_va(
                    registro
                )
            ]

            if elegibles:
                seleccionado = max(
                    elegibles,
                    key=self._clave_orden_va,
                )
                activo = True

            else:
                seleccionado = max(
                    registros,
                    key=self._clave_orden_va,
                )
                activo = False

            presente_padron = any(
                registro[
                    "presente_padron_actual"
                ]
                for registro in registros
            )

            defaults = {
                "activo": activo,
                "presente_fuente": (
                    presente_padron
                ),
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
            }

            if presente_padron:
                defaults[
                    "ultima_presencia"
                ] = ahora

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

    def _es_elegible_va(self, registro):
        if not registro[
            "presente_padron_actual"
        ]:
            return False

        if not registro["lista_nominal"]:
            return False

        fecha_solicitud = registro[
            "fecha_solicitud_tramite"
        ]

        if fecha_solicitud is None:
            return False

        if (
            fecha_solicitud.year
            < ANIO_INICIO_VA
        ):
            return False

        fecha_entrega = registro[
            "fecha_entrega_credencial"
        ]

        if fecha_entrega is None:
            return True

        if fecha_entrega < fecha_solicitud:
            return False

        fecha_limite = self._sumar_meses(
            fecha_solicitud,
            PLAZO_MAXIMO_VA_MESES,
        )

        return fecha_entrega <= fecha_limite

    @staticmethod
    def _sumar_meses(fecha, meses):
        mes = fecha.month - 1 + meses

        anio = (
            fecha.year
            + mes // 12
        )

        mes = mes % 12 + 1

        dia = min(
            fecha.day,
            calendar.monthrange(
                anio,
                mes,
            )[1],
        )

        return fecha.replace(
            year=anio,
            month=mes,
            day=dia,
        )

    @staticmethod
    def _clave_orden_va(registro):
        fecha_solicitud = (
            registro[
                "fecha_solicitud_tramite"
            ]
            or datetime.min.date()
        )

        fecha_entrega = (
            registro[
                "fecha_entrega_credencial"
            ]
            or datetime.min.date()
        )

        return (
            fecha_solicitud,
            fecha_entrega,
            registro["fuar"],
        )

    @staticmethod
    def _datos_modelo(datos):
        return {
            "fuar": datos["fuar"],
            "ciudadano_id": (
                datos["ciudadano_id"]
            ),
            "fecha_solicitud_tramite": (
                datos[
                    "fecha_solicitud_tramite"
                ]
            ),
            "fecha_entrega_credencial": (
                datos[
                    "fecha_entrega_credencial"
                ]
            ),
            "estatusciudadano_id": (
                datos[
                    "estatusciudadano_id"
                ]
            ),
            "entidad": datos["entidad"],
            "distrito": datos["distrito"],
            "municipio": datos["municipio"],
            "seccion_origen": (
                datos["seccion_origen"]
            ),
            "localidad": datos["localidad"],
            "manzana_origen": (
                datos["manzana_origen"]
            ),
            "seccion": datos["seccion"],
            "localidad_mge": (
                datos["localidad_mge"]
            ),
            "manzana": datos["manzana"],
            "edad": datos["edad"],
            "sexo": datos["sexo"],
        }

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
        self.stdout.write(
            "KPI ARTÍCULO 141"
        )
        self.stdout.write(
            f"Trámites creados:       "
            f"{resultado_kpi['creados']}"
        )
        self.stdout.write(
            f"Trámites actualizados:  "
            f"{resultado_kpi['actualizados']}"
        )
        self.stdout.write(
            f"Registros legacy eliminados: "
            f"{resultado_kpi['eliminados_legacy']}"
        )
        self.stdout.write(
            f"Trámites históricos:    "
            f"{resultado_kpi['total']}"
        )

        self.stdout.write("")
        self.stdout.write(
            "UNIVERSO VA"
        )
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
            f"Personas no activas:     "
            f"{resultado_va['inactivos']}"
        )
        self.stdout.write(
            f"Personas históricas VA:  "
            f"{resultado_va['total']}"
        )

        self._mostrar_georreferencia()

    def _mostrar_georreferencia(self):
        self.stdout.write("")
        self.stdout.write(
            "GEOREFERENCIA KPI"
        )
        self._mostrar_niveles(
            TramiteArt141.objects.all()
        )

        self.stdout.write("")
        self.stdout.write(
            "GEOREFERENCIA VA"
        )
        self._mostrar_niveles(
            UniversoVA.objects.filter(
                activo=True
            )
        )

    def _mostrar_niveles(self, queryset):
        nivel_manzana = queryset.filter(
            manzana__isnull=False
        ).count()

        nivel_localidad = queryset.filter(
            manzana__isnull=True,
            localidad_mge__isnull=False,
        ).count()

        nivel_seccion = queryset.filter(
            manzana__isnull=True,
            localidad_mge__isnull=True,
            seccion__isnull=False,
        ).count()

        pendiente = queryset.filter(
            seccion__isnull=True
        ).count()

        self.stdout.write(
            f"Nivel manzana:           "
            f"{nivel_manzana}"
        )
        self.stdout.write(
            f"Nivel localidad:         "
            f"{nivel_localidad}"
        )
        self.stdout.write(
            f"Nivel sección:           "
            f"{nivel_seccion}"
        )
        self.stdout.write(
            f"Georreferencia pendiente:"
            f"{pendiente:>9}"
        )

    @staticmethod
    def _texto(valor):
        if valor is None:
            return ""

        return str(valor).strip()

    @staticmethod
    def _entero(valor):
        valor = str(
            valor or ""
        ).strip()

        if not valor:
            return None

        try:
            return int(valor)

        except ValueError as exc:
            raise ValueError(
                f"Valor entero inválido: "
                f"{valor}"
            ) from exc

    @staticmethod
    def _entidad(valor):
        texto = str(
            valor or ""
        ).strip()

        if not texto:
            return None

        if texto.isdigit():
            return int(texto)

        if texto.upper() == "TLAXCALA":
            return 29

        raise ValueError(
            f"Entidad no reconocida: "
            f"{texto}"
        )

    @staticmethod
    def _booleano_si_no(valor):
        texto = str(
            valor or ""
        ).strip().upper()

        return texto in {
            "SI",
            "SÍ",
            "1",
            "TRUE",
        }

    @staticmethod
    def _fecha(valor):
        valor = str(
            valor or ""
        ).strip()

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
            f"Fecha no reconocida: "
            f"{valor}"
        )
