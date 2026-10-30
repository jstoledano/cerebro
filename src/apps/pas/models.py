import datetime

import django.utils.timezone
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from tinymce.models import HTMLField

from apps.profiles.models import (
    UnidadOrganizacional,
    JL,
    JD01,
    JD02,
    JD03,
)


User = get_user_model()


def user_display_name(user):
    if not user:
        return ""
    full_name = (user.get_full_name() or "").strip()
    if full_name:
        return full_name
    return user.email or user.username


class TrackingFields(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


CNC = 1
PCM = 2
PROYECTO = 3
PROGRAMA = 4
META = 5

DOCUMENTO = (
    (CNC, "Cédula de No Conformidad"),
    (PCM, "Plan de Cambios y Mejoras al SGC"),
    (PROYECTO, "Proyecto"),
    (PROGRAMA, "Programa"),
    (META, "Meta"),
)

PROCESO = (
    (1, "Estratégico"),
    (2, "Sustantivos"),
    (3, "Soporte"),
    (4, "Medición, Análisis y Mejora"),
    (5, "SGC"),
)

TIPO = ((1, "Corrección"), (2, "Acción Correctiva"), (3, "Riesgo"))

FUENTE = (
    (1, "Auditoría Externa"),
    (2, "Auditoría Interna"),
    (3, "Queja del cliente"),
    (4, "Revisión por la Dirección"),
    (5, "Proceso"),
    (6, "Documentación del SGC"),
    (7, "Objetivos e Indicadores"),
    (8, "Evaluación de riesgos"),
    (9, "Otros"),
)

MEJORA = ((1, "Procesos"), (2, "Servicio"), (3, "Sistema"))

CERRADA = 99

A_ESTADO = (
    (1, "Seguimiento"),
    (2, "Revisión de Evidencia"),
    (3, "En espera de una respuesta"),
    (4, "En espera de una acción"),
    (5, "En espera de un evento"),
    (CERRADA, "Cerrada"),
)

JPG = "image/jpeg"
PDF = "application/pdf"
PNG = "image/png"

VISIBILIDAD_PUBLICA = "publica"
VISIBILIDAD_INTERNA = "interna"
VISIBILIDAD_RESTRINGIDA = "restringida"

VISIBILIDAD = (
    (VISIBILIDAD_PUBLICA, "Pública"),
    (VISIBILIDAD_INTERNA, "Interna"),
    (VISIBILIDAD_RESTRINGIDA, "Restringida"),
)


class PlanQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user and user.is_authenticated:
            if user.is_superuser or user.has_perm("pas.view_plan"):
                return self

            return self.filter(
                visibilidad__in=[
                    VISIBILIDAD_PUBLICA,
                    VISIBILIDAD_INTERNA,
                ]
            )

        return self.filter(
            visibilidad=VISIBILIDAD_PUBLICA
        )


PERIODICIDAD_UNICA = "unica"
PERIODICIDAD_CONTINUA = "continua"
PERIODICIDAD_SEMANAL = "semanal"
PERIODICIDAD_QUINCENAL = "quincenal"
PERIODICIDAD_MENSUAL = "mensual"
PERIODICIDAD_BIMESTRAL = "bimestral"
PERIODICIDAD_TRIMESTRAL = "trimestral"
PERIODICIDAD_ANUAL = "anual"
PERIODICIDAD_MANUAL = "manual"

PERIODICIDAD = (
    (
        PERIODICIDAD_UNICA,
        "Una vez",
    ),
    (
        PERIODICIDAD_CONTINUA,
        "Continua",
    ),
    (
        PERIODICIDAD_SEMANAL,
        "Semanal",
    ),
    (
        PERIODICIDAD_QUINCENAL,
        "Quincenal",
    ),
    (
        PERIODICIDAD_MENSUAL,
        "Mensual",
    ),
    (
        PERIODICIDAD_BIMESTRAL,
        "Bimestral",
    ),
    (
        PERIODICIDAD_TRIMESTRAL,
        "Trimestral",
    ),
    (
        PERIODICIDAD_ANUAL,
        "Anual",
    ),
    (
        PERIODICIDAD_MANUAL,
        "Fechas definidas manualmente",
    ),
)


AMBITO_JL = "JL"
AMBITO_D01 = "D01"
AMBITO_D02 = "D02"
AMBITO_D03 = "D03"

AMBITO = (
    (AMBITO_JL, "Junta Local"),
    (AMBITO_D01, "Distrito 01"),
    (AMBITO_D02, "Distrito 02"),
    (AMBITO_D03, "Distrito 03"),
)


FORMATO_SIN_EVIDENCIA = "ninguno"
FORMATO_PDF = "pdf"
FORMATO_XLSX = "xlsx"
FORMATO_DOCX = "docx"
FORMATO_PPTX = "pptx"
FORMATO_ZIP = "zip"

FORMATO_EVIDENCIA = (
    (
        FORMATO_SIN_EVIDENCIA,
        "Sin evidencia requerida",
    ),
    (
        FORMATO_PDF,
        "PDF",
    ),
    (
        FORMATO_XLSX,
        "Excel (XLSX)",
    ),
    (
        FORMATO_DOCX,
        "Word (DOCX)",
    ),
    (
        FORMATO_PPTX,
        "PowerPoint (PPTX)",
    ),
    (
        FORMATO_ZIP,
        "Archivo comprimido (ZIP)",
    ),
)


class Plan(TrackingFields):
    objects = PlanQuerySet.as_manager()

    class Meta:
        verbose_name = _("Plan")
        verbose_name_plural = _("Planes")

    # #################################### #
    # I. Identificación general

    nombre = models.CharField(
        max_length=255,
        help_text=(
            "Nombre del plan, proyecto, "
            "programa o meta."
        ),
    )

    documento = models.IntegerField(
        "Tipo",
        choices=DOCUMENTO,
        help_text=(
            "Selecciona el tipo de registro."
        ),
    )

    folio = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=(
            "Folio o identificador institucional, "
            "cuando exista."
        ),
    )

    fecha_llenado = models.DateField(
        "Fecha de registro",
        default=django.utils.timezone.now,
    )

    descripcion = HTMLField(
        "Descripción",
        default="",
        blank=True,
        help_text=(
            "Descripción general del plan, "
            "proyecto, programa o meta."
        ),
    )

    documento_fuente = models.FileField(
        "Documento fuente",
        upload_to="pas/documentos",
        blank=True,
        null=True,
        help_text=(
            "Documento que da origen o sustento "
            "al registro, cuando exista."
        ),
    )

    fecha_inicio = models.DateField(
        "Fecha de inicio",
        blank=True,
        null=True,
        help_text=(
            "Fecha de inicio, cuando sea aplicable."
        ),
    )

    fecha_termino = models.DateField(
        "Fecha de término",
        blank=True,
        null=True,
        help_text=(
            "Fecha de término, cuando sea aplicable."
        ),
    )

    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDAD,
        default=VISIBILIDAD_PUBLICA,
        help_text=(
            "Define quién puede consultar el plan."
        ),
    )

    # #################################### #
    # II. Datos específicos de CNC

    tipo = models.IntegerField(
        choices=TIPO,
        help_text="Tipo de acción requerida",
        blank=True,
        null=True,
    )

    desc_cnc = HTMLField(
        "Descripción de la No Conformidad / Riesgo",
        default="",
        blank=True,
        null=True,
    )

    correccion = HTMLField(
        default="",
        blank=True,
        null=True,
        help_text=(
            "Corrección (si aplica)"
        ),
    )

    fuente = models.IntegerField(
        choices=FUENTE,
        blank=True,
        null=True,
    )

    otra_fuente = models.TextField(
        "Otra (especifique)",
        blank=True,
        null=True,
        help_text=(
            "Especifique la fuente si seleccionó Otros"
        ),
    )

    # #################################### #
    # III. Datos heredados de PCM

    proposito = models.CharField(
        "Propósito",
        blank=True,
        null=True,
        help_text=(
            "Propósito del cambio o mejora al SGC"
        ),
        max_length=255,
    )

    requisito = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text=(
            "Requisito(s) de ISO 9001:2015 "
            "afectado(s) y/o beneficiados"
        ),
    )

    proceso = models.IntegerField(
        choices=PROCESO,
        blank=True,
        null=True,
        help_text=(
            "Proceso(s) del SGC afectado(s) "
            "y/o beneficiados"
        ),
    )

    desc_pcm = HTMLField(
        "Descripción",
        default="",
        blank=True,
        null=True,
        help_text=(
            "Descripción del cambio o mejora al SGC"
        ),
    )

    consecuencias = HTMLField(
        "Consecuencias",
        default="",
        blank=True,
        null=True,
        help_text=(
            "Consecuencias potenciales de que "
            "el cambio o mejora no se realice"
        ),
    )

    # #################################### #
    # IV. Análisis de causa raíz

    analisis = HTMLField(
        default="",
        blank=True,
        null=True,
        help_text=(
            "Análisis de la causa raíz"
        ),
    )

    evidencia_analisis = models.FileField(
        upload_to="pas",
        blank=True,
        null=True,
    )

    # #################################### #
    # V. Cierre

    eliminacion = models.BooleanField(
        default=False,
    )

    txt_eliminacion = HTMLField(
        blank=True,
        null=True,
    )

    recurrencia = models.BooleanField(
        default=False,
    )

    txt_recurrencia = HTMLField(
        blank=True,
        null=True,
    )

    @property
    def esta_cerrado(self):
        return self.eliminacion

    @property
    def tiene_recurrencia(self):
        return self.recurrencia

    @property
    def permite_modificaciones(self):
        return not (
            self.esta_cerrado
            or self.tiene_recurrencia
        )

    @property
    def siglas(self):
        siglas = {
            CNC: "CNC",
            PCM: "PCM",
            PROYECTO: "Proyecto",
            PROGRAMA: "Programa",
            META: "Meta",
        }

        return siglas.get(
            self.documento,
            "N/A",
        )

    def __str__(self):
        if self.folio:
            return (
                f"{self.folio} - "
                f"{self.nombre}"
            )

        return self.nombre


PRIORIDAD_NORMAL = "normal"
PRIORIDAD_URGENTE = "urgente"
PRIORIDAD_CRITICA = "critica"

PRIORIDAD = (
    (PRIORIDAD_NORMAL, "Normal"),
    (PRIORIDAD_URGENTE, "Urgente"),
    (PRIORIDAD_CRITICA, "Crítica"),
)


class Accion(TrackingFields):
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
    )

    accion = HTMLField()

    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="acciones_responsables",
        blank=True,
        null=True,
        help_text=(
            "Persona responsable directa de la actividad. "
            "Se utiliza cuando la asignación no se determina por puesto y ámbito."
        ),
    )

    puesto_responsable = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text=(
            "Clave de la unidad organizacional responsable. "
            "Cuando se seleccionan varios ámbitos, PM² "
            "resolverá la unidad equivalente en cada ámbito."
        ),
    )

    recursos = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Recursos necesarios para realizar la actividad",
    )

    evidencia = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Descripción de la evidencia documental esperada",
    )

    formato_evidencia = models.CharField(
        max_length=10,
        choices=FORMATO_EVIDENCIA,
        blank=True,
        default="",
        help_text=(
            "Formato de archivo esperado para la evidencia "
            "de cada ejecución."
        ),
    )

    periodicidad = models.CharField(
        max_length=20,
        choices=PERIODICIDAD,
        default=PERIODICIDAD_UNICA,
        help_text="Periodicidad prevista para la actividad.",
    )

    ambitos = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Ámbitos en los que debe ejecutarse la actividad. "
            "Ejemplo: ['D01', 'D02', 'D03']."
        ),
    )

    fecha_inicio = models.DateField(
        blank=True,
        null=True,
    )

    fecha_fin = models.DateField(
        blank=True,
        null=True,
    )

    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD,
        default=PRIORIDAD_NORMAL,
        help_text="Nivel de atención para el seguimiento de la actividad.",
    )

    class Meta:
        verbose_name = _("Actividad")
        verbose_name_plural = _("Actividades")

    @property
    def responsable_display(self):
        return user_display_name(self.responsable)

    def _ejecuciones_estado(self):
        prefetched = getattr(
            self,
            "_prefetched_objects_cache",
            {},
        )

        if "ciclos" in prefetched:
            ejecuciones = []

            for ciclo in prefetched["ciclos"]:
                ciclo_prefetched = getattr(
                    ciclo,
                    "_prefetched_objects_cache",
                    {},
                )

                if "ejecuciones" in ciclo_prefetched:
                    ejecuciones.extend(ciclo_prefetched["ejecuciones"])

                else:
                    ejecuciones.extend(ciclo.ejecuciones.all())

            return ejecuciones

        return list(
            Ejecucion.objects.filter(ciclo__accion=self).select_related("ciclo")
        )

    @property
    def get_estado(self):
        """
        Estado general de la actividad a partir de sus
        ejecuciones concretas.

        Una actividad recurrente sin fecha de término
        permanece abierta aunque todas las ejecuciones
        materializadas hasta el momento estén cerradas.
        """

        hoy = django.utils.timezone.localdate()

        ejecuciones = self._ejecuciones_estado()

        es_recurrente_abierta = self.fecha_fin is None and self.periodicidad not in {
            PERIODICIDAD_UNICA,
            PERIODICIDAD_CONTINUA,
            PERIODICIDAD_MANUAL,
        }

        if not ejecuciones:
            if self.fecha_fin and self.fecha_fin < hoy:
                return "Abierta Fuera de Tiempo"

            return "Abierta en Tiempo"

        if any(
            (not ejecucion.completada and ejecucion.fecha_fin < hoy)
            for ejecucion in ejecuciones
        ):
            return "Abierta Fuera de Tiempo"

        if es_recurrente_abierta:
            return "Abierta en Tiempo"

        if all(ejecucion.completada for ejecucion in ejecuciones):
            return "Cerrada"

        return "Abierta en Tiempo"

    @property
    def salud_plazo(self):
        """
        Resume la situación temporal de la actividad
        a partir de sus ejecuciones concretas.

        Una recurrencia abierta no se considera cerrada
        sólo porque las ejecuciones materializadas hasta
        el momento hayan sido completadas.
        """

        hoy = django.utils.timezone.localdate()

        ejecuciones = self._ejecuciones_estado()

        es_recurrente_abierta = self.fecha_fin is None and self.periodicidad not in {
            PERIODICIDAD_UNICA,
            PERIODICIDAD_CONTINUA,
            PERIODICIDAD_MANUAL,
        }

        if not ejecuciones:
            if not self.fecha_fin:
                return "Sin fecha de término"

            if self.fecha_fin < hoy:
                return "Vencida"

            if self.fecha_fin == hoy:
                return "Vence hoy"

            return "En tiempo"

        pendientes = [
            ejecucion for ejecucion in ejecuciones if not ejecucion.completada
        ]

        if any(ejecucion.fecha_fin < hoy for ejecucion in pendientes):
            return "Vencida"

        if any(ejecucion.fecha_fin == hoy for ejecucion in pendientes):
            return "Vence hoy"

        if es_recurrente_abierta:
            return "En tiempo"

        if not pendientes:
            cerrada_fuera_de_tiempo = any(
                (
                    ejecucion.fecha_completada
                    and ejecucion.fecha_completada > ejecucion.fecha_fin
                )
                for ejecucion in ejecuciones
            )

            if cerrada_fuera_de_tiempo:
                return "Cerrada fuera de tiempo"

            return "Cerrada en tiempo"

        return "En tiempo"

    def resolver_responsable_ejecucion(
        self,
        ambito,
    ):
        if self.responsable_id:
            return self.responsable

        if not self.puesto_responsable:
            return None

        sitios = {
            AMBITO_JL: JL,
            AMBITO_D01: JD01,
            AMBITO_D02: JD02,
            AMBITO_D03: JD03,
        }

        digitos_sede = {
            AMBITO_JL: "0",
            AMBITO_D01: "1",
            AMBITO_D02: "2",
            AMBITO_D03: "3",
        }

        site = sitios.get(ambito)

        digito_sede = digitos_sede.get(ambito)

        if site is None or digito_sede is None:
            return None

        clave_base = str(self.puesto_responsable).strip()

        if not clave_base:
            return None

        # ------------------------------------------------------
        # La clave capturada representa la unidad de referencia
        # de Junta Local.
        #
        # Ejemplos:
        #
        # 50   -> 50 / 51 / 52 / 53
        # 5010 -> 5010 / 5110 / 5210 / 5310
        # 00   -> 00 / 01 / 02 / 03
        #
        # Las unidades sin equivalente distrital simplemente
        # no se resolverán fuera de su ámbito real.
        # ------------------------------------------------------

        if ambito == AMBITO_JL:
            clave_objetivo = clave_base

        elif len(clave_base) == 2:
            clave_objetivo = clave_base[0] + digito_sede

        elif len(clave_base) == 4:
            clave_objetivo = clave_base[0] + digito_sede + clave_base[2:]

        else:
            return None

        unidad = UnidadOrganizacional.objects.filter(
            clave=clave_objetivo,
            activa=True,
            site=site,
        ).first()

        if not unidad:
            return None

        return (
            User.objects.filter(
                is_active=True,
                profile__unidad_organizacional=unidad,
            )
            .select_related(
                "profile",
                "profile__unidad_organizacional",
            )
            .order_by(
                "profile__order",
                "first_name",
                "last_name",
                "pk",
            )
            .first()
        )

    def fechas_programadas_en_rango(
        self,
        fecha_desde,
        fecha_hasta,
    ):
        if not self.fecha_inicio:
            return []

        if self.periodicidad in {
            PERIODICIDAD_UNICA,
            PERIODICIDAD_MANUAL,
        }:
            return []

        fecha_inicio = self.fecha_inicio
        fecha_fin = self.fecha_fin

        def sumar_meses(
            fecha,
            meses,
        ):
            mes = fecha.month - 1 + meses

            anio = fecha.year + mes // 12

            mes = mes % 12 + 1

            if mes == 12:
                siguiente_mes = datetime.date(
                    anio + 1,
                    1,
                    1,
                )
            else:
                siguiente_mes = datetime.date(
                    anio,
                    mes + 1,
                    1,
                )

            ultimo_dia = (siguiente_mes - datetime.timedelta(days=1)).day

            return datetime.date(
                anio,
                mes,
                min(
                    fecha.day,
                    ultimo_dia,
                ),
            )

        def siguiente_fecha(
            fecha,
        ):
            if self.periodicidad == PERIODICIDAD_SEMANAL:
                return fecha + datetime.timedelta(days=7)

            if self.periodicidad == PERIODICIDAD_QUINCENAL:
                return fecha + datetime.timedelta(days=14)

            if self.periodicidad == PERIODICIDAD_MENSUAL:
                return sumar_meses(
                    fecha,
                    1,
                )

            if self.periodicidad == PERIODICIDAD_BIMESTRAL:
                return sumar_meses(
                    fecha,
                    2,
                )

            if self.periodicidad == PERIODICIDAD_TRIMESTRAL:
                return sumar_meses(
                    fecha,
                    3,
                )

            if self.periodicidad == PERIODICIDAD_ANUAL:
                return sumar_meses(
                    fecha,
                    12,
                )

            return None

        fechas = []

        fecha = fecha_inicio

        while fecha < fecha_desde:
            fecha = siguiente_fecha(fecha)

            if fecha is None:
                return []

            if fecha_fin and fecha > fecha_fin:
                return []

        while fecha < fecha_hasta:
            if fecha_fin and fecha > fecha_fin:
                break

            fechas.append(fecha)

            fecha = siguiente_fecha(fecha)

            if fecha is None:
                break

        return fechas

        def siguiente_fecha(
            fecha,
        ):
            if self.periodicidad == PERIODICIDAD_SEMANAL:
                return fecha + datetime.timedelta(days=7)

            if self.periodicidad == PERIODICIDAD_QUINCENAL:
                return fecha + datetime.timedelta(days=14)

            if self.periodicidad == PERIODICIDAD_MENSUAL:
                return sumar_meses(
                    fecha,
                    1,
                )

            if self.periodicidad == PERIODICIDAD_BIMESTRAL:
                return sumar_meses(
                    fecha,
                    2,
                )

            if self.periodicidad == PERIODICIDAD_TRIMESTRAL:
                return sumar_meses(
                    fecha,
                    3,
                )

            return None

        fechas = []

        fecha = fecha_inicio

        while fecha < fecha_desde:
            fecha = siguiente_fecha(fecha)

            if fecha is None:
                return []

            if fecha_fin and fecha > fecha_fin:
                return []

        while fecha < fecha_hasta:
            if fecha_fin and fecha > fecha_fin:
                break

            fechas.append(fecha)

            fecha = siguiente_fecha(fecha)

            if fecha is None:
                break

        return fechas

    def generar_ejecuciones(self):
        def normalizar_fecha(
            valor,
        ):
            if valor is None:
                return None

            if isinstance(
                valor,
                datetime.datetime,
            ):
                return valor.date()

            if isinstance(
                valor,
                datetime.date,
            ):
                return valor

            if isinstance(
                valor,
                str,
            ):
                return datetime.date.fromisoformat(valor)

            raise TypeError(f"Tipo de fecha no soportado: {type(valor).__name__}")

        fecha_inicio_actividad = normalizar_fecha(self.fecha_inicio)

        fecha_fin_actividad = normalizar_fecha(self.fecha_fin)

        if not fecha_inicio_actividad:
            raise ValueError("La actividad debe tener fecha de inicio.")

        if fecha_fin_actividad and fecha_fin_actividad < fecha_inicio_actividad:
            raise ValueError(
                "La fecha de término no puede ser anterior a la fecha de inicio."
            )

        # ======================================================
        # Continua requiere un intervalo real.
        # ======================================================

        if self.periodicidad == PERIODICIDAD_CONTINUA and not fecha_fin_actividad:
            raise ValueError("Una actividad continua debe tener fecha de término.")

        ambitos = self.ambitos or [AMBITO_JL]

        ambitos_validos = {
            AMBITO_JL,
            AMBITO_D01,
            AMBITO_D02,
            AMBITO_D03,
        }

        ambitos_invalidos = set(ambitos) - ambitos_validos

        if ambitos_invalidos:
            raise ValueError(
                "La actividad contiene ámbitos "
                "no válidos: " + ", ".join(sorted(ambitos_invalidos))
            )

        def sumar_meses(
            fecha,
            meses,
        ):
            mes = fecha.month - 1 + meses

            anio = fecha.year + mes // 12

            mes = mes % 12 + 1

            if mes == 12:
                primer_dia_siguiente_mes = datetime.date(
                    anio + 1,
                    1,
                    1,
                )
            else:
                primer_dia_siguiente_mes = datetime.date(
                    anio,
                    mes + 1,
                    1,
                )

            ultimo_dia = (primer_dia_siguiente_mes - datetime.timedelta(days=1)).day

            dia = min(
                fecha.day,
                ultimo_dia,
            )

            return datetime.date(
                anio,
                mes,
                dia,
            )

        def siguiente_fecha(
            fecha,
        ):
            if self.periodicidad == PERIODICIDAD_SEMANAL:
                return fecha + datetime.timedelta(days=7)

            if self.periodicidad == PERIODICIDAD_QUINCENAL:
                return fecha + datetime.timedelta(days=14)

            if self.periodicidad == PERIODICIDAD_MENSUAL:
                return sumar_meses(
                    fecha,
                    1,
                )

            if self.periodicidad == PERIODICIDAD_BIMESTRAL:
                return sumar_meses(
                    fecha,
                    2,
                )

            if self.periodicidad == PERIODICIDAD_TRIMESTRAL:
                return sumar_meses(
                    fecha,
                    3,
                )

            if self.periodicidad == PERIODICIDAD_ANUAL:
                return sumar_meses(
                    fecha,
                    12,
                )

            raise ValueError("Periodicidad no reconocida.")

        def construir_etiqueta(
            numero,
            fecha,
        ):
            if self.periodicidad == PERIODICIDAD_SEMANAL:
                return f"Semana {numero}"

            if self.periodicidad == PERIODICIDAD_QUINCENAL:
                return f"Quincena {numero}"

            if self.periodicidad == PERIODICIDAD_MENSUAL:
                return fecha.strftime("%B %Y").capitalize()

            if self.periodicidad == PERIODICIDAD_BIMESTRAL:
                return f"Bimestre {numero}"

            if self.periodicidad == PERIODICIDAD_TRIMESTRAL:
                return f"Trimestre {numero}"

            if self.periodicidad == PERIODICIDAD_ANUAL:
                return str(fecha.year)

            return f"Ciclo {numero}"

        def construir_periodos():
            # --------------------------------------------------
            # Manual: utiliza los ciclos existentes.
            # --------------------------------------------------

            if self.periodicidad == PERIODICIDAD_MANUAL:
                return None

            # --------------------------------------------------
            # Una vez:
            #
            # Un solo ciclo. Puede ser puntual o abarcar
            # un intervalo si existe fecha_fin.
            # --------------------------------------------------

            if self.periodicidad == PERIODICIDAD_UNICA:
                return [
                    {
                        "numero": 1,
                        "etiqueta": "Única",
                        "fecha_inicio": (fecha_inicio_actividad),
                        "fecha_fin": (fecha_fin_actividad or fecha_inicio_actividad),
                    }
                ]

            # --------------------------------------------------
            # Continua:
            #
            # Un solo ciclo cuya ejecución permanece activa
            # durante todo el intervalo.
            # --------------------------------------------------

            if self.periodicidad == PERIODICIDAD_CONTINUA:
                return [
                    {
                        "numero": 1,
                        "etiqueta": "Continua",
                        "fecha_inicio": (fecha_inicio_actividad),
                        "fecha_fin": (fecha_fin_actividad),
                    }
                ]

            # --------------------------------------------------
            # Recurrentes
            # --------------------------------------------------

            periodos = []

            fecha = fecha_inicio_actividad

            numero = 1

            hoy = django.utils.timezone.localdate()

            referencia_abierta = max(
                hoy,
                fecha_inicio_actividad,
            )

            while True:
                if fecha_fin_actividad and fecha > fecha_fin_actividad:
                    break

                periodos.append(
                    {
                        "numero": numero,
                        "etiqueta": (
                            construir_etiqueta(
                                numero,
                                fecha,
                            )
                        ),
                        "fecha_inicio": fecha,
                        "fecha_fin": fecha,
                    }
                )

                if fecha_fin_actividad is None and fecha > referencia_abierta:
                    break

                fecha = siguiente_fecha(fecha)

                numero += 1

            return periodos

        periodos = construir_periodos()

        # ======================================================
        # Ciclos manuales
        # ======================================================

        if periodos is None:
            ciclos = list(
                self.ciclos.order_by(
                    "fecha_inicio",
                    "numero",
                )
            )

            if not ciclos:
                raise ValueError(
                    "La actividad utiliza fechas "
                    "manuales pero todavía no tiene "
                    "ciclos definidos."
                )

        # ======================================================
        # Ciclos generados
        # ======================================================

        else:
            numeros_generados = set()

            for periodo in periodos:
                numeros_generados.add(periodo["numero"])

                CicloActividad.objects.update_or_create(
                    accion=self,
                    numero=(periodo["numero"]),
                    defaults={
                        "etiqueta": (periodo["etiqueta"]),
                        "fecha_inicio": (periodo["fecha_inicio"]),
                        "fecha_fin": (periodo["fecha_fin"]),
                        "user": self.user,
                    },
                )

            self.ciclos.exclude(numero__in=(numeros_generados)).delete()

            ciclos = list(
                self.ciclos.order_by(
                    "fecha_inicio",
                    "numero",
                )
            )

        # ======================================================
        # Ejecuciones por ámbito
        # ======================================================

        ejecuciones = []

        for ciclo in ciclos:
            for ambito in ambitos:
                responsable = self.resolver_responsable_ejecucion(ambito)

                ejecucion, _ = Ejecucion.objects.update_or_create(
                    ciclo=ciclo,
                    ambito=ambito,
                    defaults={
                        "responsable": (responsable),
                        "user": (self.user),
                    },
                )

                ejecuciones.append(ejecucion)

            ciclo.ejecuciones.exclude(ambito__in=ambitos).delete()

        return ejecuciones

    def __str__(self):
        return (
            f"{self.id} - "
            f"{self.plan}: "
            f"{self.get_estado}"
        )


class CicloActividad(TrackingFields):
    accion = models.ForeignKey(
        Accion,
        on_delete=models.CASCADE,
        related_name="ciclos",
    )

    numero = models.PositiveIntegerField(
        help_text="Número consecutivo del ciclo dentro de la actividad.",
    )

    etiqueta = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=(
            "Descripción legible del ciclo. "
            "Ejemplo: Semana 43, Primera quincena de octubre."
        ),
    )

    fecha_inicio = models.DateField()

    fecha_fin = models.DateField()

    class Meta:
        verbose_name = _("Ciclo de actividad")
        verbose_name_plural = _("Ciclos de actividad")
        ordering = [
            "fecha_inicio",
            "numero",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "accion",
                    "numero",
                ],
                name="pas_unique_action_cycle_number",
            ),
        ]

    def __str__(self):
        etiqueta = self.etiqueta or f"Ciclo {self.numero}"

        return (
            f"{self.accion_id} - {etiqueta} "
            f"({self.fecha_inicio:%d/%m/%Y})"
        )


class Ejecucion(TrackingFields):
    ciclo = models.ForeignKey(
        CicloActividad,
        on_delete=models.CASCADE,
        related_name="ejecuciones",
    )

    ambito = models.CharField(
        max_length=10,
        choices=AMBITO,
        help_text="Ámbito responsable de esta ejecución.",
    )

    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="pas_ejecuciones_responsables",
        blank=True,
        null=True,
        help_text=(
            "Persona responsable concreta de esta ejecución."
        ),
    )

    completada = models.BooleanField(
        default=False,
        help_text=(
            "Indica que la ejecución fue registrada como terminada."
        ),
    )

    fecha_completada = models.DateField(
        blank=True,
        null=True,
        help_text=(
            "Fecha en que la ejecución fue registrada como terminada."
        ),
    )

    class Meta:
        verbose_name = _("Ejecución")
        verbose_name_plural = _("Ejecuciones")
        ordering = [
            "ciclo__fecha_inicio",
            "ambito",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ciclo",
                    "ambito",
                ],
                name="pas_unique_cycle_scope",
            ),
        ]

    @property
    def accion(self):
        return self.ciclo.accion

    @property
    def plan(self):
        return self.ciclo.accion.plan

    @property
    def fecha_inicio(self):
        return self.ciclo.fecha_inicio

    @property
    def fecha_fin(self):
        return self.ciclo.fecha_fin

    @property
    def responsable_display(self):
        return user_display_name(self.responsable)

    @property
    def ambito_display(self):
        return self.get_ambito_display()

    @property
    def estado_agenda(self):
        if self.completada:
            return "terminada"

        hoy = django.utils.timezone.localdate()

        if self.fecha_fin < hoy:
            return "vencida"

        if self.fecha_inicio == hoy:
            return "inicia_hoy"

        if self.fecha_fin == hoy:
            return "vence_hoy"

        if self.fecha_inicio > hoy:
            return "programada"

        return "pendiente"

    @property
    def estado_agenda_display(self):
        estados = {
            "terminada": "Terminada",
            "vencida": "Vencida",
            "inicia_hoy": "Inicia hoy",
            "vence_hoy": "Vence hoy",
            "programada": "Programada",
            "pendiente": "Pendiente",
        }

        return estados[self.estado_agenda]

    @property
    def esta_pendiente(self):
        return not self.completada

    @property
    def esta_vencida(self):
        return self.estado_agenda == "vencida"

    @property
    def inicia_hoy(self):
        return (
            not self.completada
            and self.fecha_inicio
            == django.utils.timezone.localdate()
        )

    @property
    def vence_hoy(self):
        return (
            not self.completada
            and self.fecha_fin
            == django.utils.timezone.localdate()
        )

    @property
    def tiene_evidencia(self):
        prefetched = getattr(
            self,
            "_prefetched_objects_cache",
            {},
        )

        if "evidencias" in prefetched:
            return any(
                bool(evidencia.archivo)
                for evidencia in prefetched["evidencias"]
            )

        return (
            self.evidencias
            .filter(archivo__isnull=False)
            .exclude(archivo="")
            .exists()
        )

    @property
    def evidencia(self):
        try:
            return self.evidencia_registrada
        except Evidencia.DoesNotExist:
            return None

    def marcar_completada(self, fecha=None):
        self.completada = True
        self.fecha_completada = (
            fecha
            or django.utils.timezone.localdate()
        )

        self.save(
            update_fields=[
                "completada",
                "fecha_completada",
                "modified",
            ]
        )

    def reabrir(self):
        self.completada = False
        self.fecha_completada = None

        self.save(
            update_fields=[
                "completada",
                "fecha_completada",
                "modified",
            ]
        )

    def __str__(self):
        etiqueta = (
            self.ciclo.etiqueta
            or f"Ciclo {self.ciclo.numero}"
        )

        return (
            f"{self.ciclo.accion_id} - "
            f"{etiqueta} - "
            f"{self.get_ambito_display()}"
        )


class Evidencia(TrackingFields):
    ejecucion = models.ForeignKey(
        Ejecucion,
        on_delete=models.CASCADE,
        related_name="evidencias",
        blank=True,
        null=True,
        help_text=(
            "Ejecución concreta a la que corresponde "
            "el archivo de evidencia."
        ),
    )

    accion = models.ForeignKey(
        Accion,
        on_delete=models.CASCADE,
        related_name="evidencias",
        blank=True,
        null=True,
        help_text=(
            "Relación heredada con la actividad. "
            "Se conserva temporalmente durante la migración "
            "al modelo de ejecuciones."
        ),
    )

    archivo = models.FileField(
        upload_to="pas/evidencias",
        blank=True,
        null=True,
    )

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=(
            "Descripción opcional del archivo registrado."
        ),
    )

    fecha = models.DateField(
        default=django.utils.timezone.now,
        help_text=(
            "Fecha asociada al registro de la evidencia."
        ),
    )

    class Meta:
        verbose_name = _("Evidencia")
        verbose_name_plural = _("Evidencias")
        ordering = [
            "-fecha",
            "-created",
        ]

    @property
    def actividad(self):
        if self.ejecucion_id:
            return self.ejecucion.accion

        return self.accion

    @property
    def plan(self):
        actividad = self.actividad

        if actividad:
            return actividad.plan

        return None

    @property
    def ambito(self):
        if not self.ejecucion_id:
            return None

        return self.ejecucion.ambito

    def __str__(self):
        if self.ejecucion_id:
            return (
                f"Evidencia {self.pk} - "
                f"Ejecución {self.ejecucion_id}"
            )

        return (
            f"Evidencia {self.pk} - "
            f"Actividad {self.accion_id}"
        )

class Seguimiento(TrackingFields, models.Model):
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE)
    descripcion = HTMLField()
    fecha = models.DateField(help_text="Fecha de la actualización")
    evidencia = models.FileField(upload_to="pas", blank=True, null=True)
    estado = models.IntegerField(choices=A_ESTADO)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="seguimientos_responsables",
        help_text="Persona responsable de la actualización",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Seguimiento de Acciones")
        verbose_name_plural = _("Seguimiento")
        get_latest_by = "fecha"
        # get_latest_by = 'modified'

    def __str__(self):
        return f"{self.accion} - {self.fecha}: {self.get_estado_display()}"

    @property
    def responsable_display(self):
        return user_display_name(self.responsable)


def generar_ejecuciones_faltantes(plan):
    actividades = (
        plan.accion_set
        .select_related(
            "responsable",
            "user",
        )
        .prefetch_related(
            "ciclos",
        )
        .order_by(
            "id",
        )
    )

    resultado = {
        "generadas": [],
        "omitidas": [],
        "errores": [],
    }

    for actividad in actividades:
        if actividad.ciclos.exists():
            resultado["omitidas"].append(
                {
                    "actividad_id": actividad.pk,
                    "motivo": "Ya tiene ciclos.",
                }
            )
            continue

        try:
            ejecuciones = (
                actividad.generar_ejecuciones()
            )

            resultado["generadas"].append(
                {
                    "actividad_id": actividad.pk,
                    "ciclos": (
                        actividad.ciclos.count()
                    ),
                    "ejecuciones": len(
                        ejecuciones
                    ),
                }
            )

        except Exception as exc:
            resultado["errores"].append(
                {
                    "actividad_id": actividad.pk,
                    "error": str(exc),
                }
            )

    return resultado
