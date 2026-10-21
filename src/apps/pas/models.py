import datetime

import django.utils.timezone
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from tinymce.models import HTMLField


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
DOCUMENTO = (
    (CNC, "Cédula de No Conformidad"),
    (PCM, "Plan de Cambios y Mejoras al SGC"),
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
PERIODICIDAD_SEMANAL = "semanal"
PERIODICIDAD_QUINCENAL = "quincenal"
PERIODICIDAD_MENSUAL = "mensual"
PERIODICIDAD_BIMESTRAL = "bimestral"
PERIODICIDAD_MANUAL = "manual"

PERIODICIDAD = (
    (PERIODICIDAD_UNICA, "Una vez"),
    (PERIODICIDAD_SEMANAL, "Semanal"),
    (PERIODICIDAD_QUINCENAL, "Quincenal"),
    (PERIODICIDAD_MENSUAL, "Mensual"),
    (PERIODICIDAD_BIMESTRAL, "Bimestral"),
    (PERIODICIDAD_MANUAL, "Fechas definidas manualmente"),
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


FORMATO_PDF = "pdf"
FORMATO_XLSX = "xlsx"
FORMATO_DOCX = "docx"
FORMATO_PPTX = "pptx"
FORMATO_ZIP = "zip"

FORMATO_EVIDENCIA = (
    (FORMATO_PDF, "PDF"),
    (FORMATO_XLSX, "Excel (XLSX)"),
    (FORMATO_DOCX, "Word (DOCX)"),
    (FORMATO_PPTX, "PowerPoint (PPTX)"),
    (FORMATO_ZIP, "Archivo comprimido (ZIP)"),
)


class Plan(TrackingFields):
    objects = PlanQuerySet.as_manager()

    class Meta:
        verbose_name = _("Plan de Acción")
        verbose_name_plural = _("Planes de Acción")

    # #################################### #
    # I. Campos de identificación comunes CNC y PCM
    nombre = models.CharField(max_length=255, help_text="Nombre del Plan de Acción")
    documento = models.IntegerField(
        "Tipo de plan", choices=DOCUMENTO, help_text="Selecciona el tipo de plan"
    )
    folio = models.CharField(max_length=20)
    fecha_llenado = models.DateField(
        "Fecha de Llenado", default=django.utils.timezone.now
    )

    # I.1 Identificación de la CNC
    tipo = models.IntegerField(
        choices=TIPO, help_text="Tipo de acción requerida", blank=True, null=True
    )
    desc_cnc = HTMLField(
        "Descripción de la No Conformidad / Riesgo", default="", blank=True, null=True
    )
    correccion = HTMLField(
        default="", blank=True, null=True, help_text="Corrección (si aplica)"
    )
    fuente = models.IntegerField(choices=FUENTE, blank=True, null=True)
    otra_fuente = models.TextField(
        "Otra (especifique)",
        blank=True,
        null=True,
        help_text="Especifique la fuente si seleccionó Otros",
    )

    # I.2 Identificación del PCM
    fecha_inicio = models.DateField(
        "Fecha de Inicio",
        blank=True,
        null=True,
        help_text="Fecha en la que se inició el Plan de Cambios y Mejoras",
    )
    fecha_termino = models.DateField(
        "Fecha de Término",
        blank=True,
        null=True,
        help_text="Fecha en la que se terminará el Plan de Cambios y Mejoras",
    )
    proposito = models.CharField(
        "Propósito",
        blank=True,
        null=True,
        help_text="Propósito del cambio o mejora al SGC",
        max_length=255,
    )
    requisito = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Requisito(s) de ISO 9001:2015 afectado(s) y/o beneficiados",
    )
    proceso = models.IntegerField(
        choices=PROCESO,
        blank=True,
        null=True,
        help_text="Proceso(s) del SGC afectado(s) y/o beneficiados",
    )
    desc_pcm = HTMLField(
        "Descripción",
        default="",
        blank=True,
        null=True,
        help_text="Descripción del cambio o mejora al SGC",
    )
    consecuencias = HTMLField(
        "Consecuencias",
        default="",
        blank=True,
        null=True,
        help_text="Consecuencias potenciales de que el cambio o mejora no se realice",
    )

    # #################################### #
    # II. Análisis de la CNC o PCM
    analisis = HTMLField(
        default="", blank=True, null=True, help_text="Análisis de la causa raíz"
    )
    evidencia_analisis = models.FileField(upload_to="pas", blank=True, null=True)

    # #################################### #
    # VIII. Cierre
    eliminacion = models.BooleanField(default=False)
    txt_eliminacion = HTMLField(blank=True, null=True)
    recurrencia = models.BooleanField(default=False)
    txt_recurrencia = HTMLField(blank=True, null=True)

    visibilidad = models.CharField(
        max_length=20,
        choices=VISIBILIDAD,
        default=VISIBILIDAD_PUBLICA,
        help_text="Define quién puede consultar el plan.",
    )

    def __str__(self):
        return "%s - %s" % (self.folio, self.nombre)

    @property
    def siglas(self):
        if self.documento == CNC:
            return "CNC"
        elif self.documento == PCM:
            return "PCM"
        return "N/A"

    @property
    def esta_cerrado(self):
        return self.eliminacion

    @property
    def tiene_recurrencia(self):
        return self.recurrencia

    @property
    def permite_modificaciones(self):
        return not (self.esta_cerrado or self.tiene_recurrencia)


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
        help_text="Persona responsable de la actividad",
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

    def _latest_seguimiento(self):
        prefetched = getattr(
            self,
            "_prefetched_objects_cache",
            {},
        ).get("seguimiento_set")

        if prefetched is not None:
            return prefetched[0] if prefetched else None

        return self.seguimiento_set.order_by(
            "-fecha",
            "-created",
        ).first()

    @property
    def estado(self):
        latest = self._latest_seguimiento()
        return latest.estado if latest else None

    @property
    def estado_operativo(self):
        latest = self._latest_seguimiento()

        if not latest:
            return None

        return latest.get_estado_display()

    @property
    def responsable_display(self):
        return user_display_name(self.responsable)

    @property
    def get_estado(self):
        latest = self._latest_seguimiento()

        if latest and latest.estado == CERRADA:
            return "Cerrada"

        hoy = django.utils.timezone.localdate()

        if self.fecha_fin and self.fecha_fin < hoy:
            return "Abierta Fuera de Tiempo"

        return "Abierta en Tiempo"

    @property
    def salud_plazo(self):
        latest = self._latest_seguimiento()
        hoy = django.utils.timezone.localdate()

        if latest and latest.estado == CERRADA:
            if not self.fecha_fin:
                return "Cerrada"

            if latest.fecha <= self.fecha_fin:
                return "Cerrada en tiempo"

            return "Cerrada fuera de tiempo"

        if not self.fecha_fin:
            return "Sin fecha de término"

        if self.fecha_fin < hoy:
            return "Vencida"

        if self.fecha_fin == hoy:
            return "Vence hoy"

        return "En tiempo"

    def generar_ejecuciones(self):
        def normalizar_fecha(valor):
            if valor is None:
                return None

            if isinstance(valor, datetime.datetime):
                return valor.date()

            if isinstance(valor, datetime.date):
                return valor

            if isinstance(valor, str):
                return datetime.date.fromisoformat(valor)

            raise TypeError(f"Tipo de fecha no soportado: {type(valor).__name__}")

        fecha_inicio_actividad = normalizar_fecha(self.fecha_inicio)

        fecha_fin_actividad = normalizar_fecha(self.fecha_fin)

        if not fecha_inicio_actividad:
            raise ValueError("La actividad debe tener fecha de inicio.")

        fecha_fin_actividad = fecha_fin_actividad or fecha_inicio_actividad

        if fecha_fin_actividad < fecha_inicio_actividad:
            raise ValueError(
                "La fecha de término no puede ser anterior a la fecha de inicio."
            )

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
                "La actividad contiene ámbitos no válidos: "
                + ", ".join(sorted(ambitos_invalidos))
            )

        def sumar_meses(fecha, meses):
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

        def construir_periodos():
            if self.periodicidad == PERIODICIDAD_MANUAL:
                return None

            if self.periodicidad == PERIODICIDAD_UNICA:
                return [
                    {
                        "numero": 1,
                        "etiqueta": "Única",
                        "fecha_inicio": fecha_inicio_actividad,
                        "fecha_fin": fecha_fin_actividad,
                    }
                ]

            periodos = []
            inicio = fecha_inicio_actividad
            numero = 1

            while inicio <= fecha_fin_actividad:
                if self.periodicidad == PERIODICIDAD_SEMANAL:
                    siguiente_inicio = inicio + datetime.timedelta(days=7)
                    etiqueta = f"Semana {numero}"

                elif self.periodicidad == PERIODICIDAD_QUINCENAL:
                    siguiente_inicio = inicio + datetime.timedelta(days=14)
                    etiqueta = f"Quincena {numero}"

                elif self.periodicidad == PERIODICIDAD_MENSUAL:
                    siguiente_inicio = sumar_meses(
                        inicio,
                        1,
                    )
                    etiqueta = inicio.strftime("%B %Y").capitalize()

                elif self.periodicidad == PERIODICIDAD_BIMESTRAL:
                    siguiente_inicio = sumar_meses(
                        inicio,
                        2,
                    )
                    etiqueta = f"Bimestre {numero}"

                else:
                    raise ValueError("Periodicidad no reconocida.")

                fin = min(
                    siguiente_inicio - datetime.timedelta(days=1),
                    fecha_fin_actividad,
                )

                periodos.append(
                    {
                        "numero": numero,
                        "etiqueta": etiqueta,
                        "fecha_inicio": inicio,
                        "fecha_fin": fin,
                    }
                )

                inicio = siguiente_inicio
                numero += 1

            return periodos

        periodos = construir_periodos()

        if periodos is None:
            ciclos = list(
                self.ciclos.order_by(
                    "fecha_inicio",
                    "numero",
                )
            )

            if not ciclos:
                raise ValueError(
                    "La actividad utiliza fechas manuales "
                    "pero todavía no tiene ciclos definidos."
                )

        else:
            numeros_generados = set()

            for periodo in periodos:
                numeros_generados.add(periodo["numero"])

                CicloActividad.objects.update_or_create(
                    accion=self,
                    numero=periodo["numero"],
                    defaults={
                        "etiqueta": periodo["etiqueta"],
                        "fecha_inicio": periodo["fecha_inicio"],
                        "fecha_fin": periodo["fecha_fin"],
                        "user": self.user,
                    },
                )

            self.ciclos.exclude(numero__in=numeros_generados).delete()

            ciclos = list(
                self.ciclos.order_by(
                    "fecha_inicio",
                    "numero",
                )
            )

        ejecuciones = []

        for ciclo in ciclos:
            for ambito in ambitos:
                ejecucion, _ = Ejecucion.objects.update_or_create(
                    ciclo=ciclo,
                    ambito=ambito,
                    defaults={
                        "responsable": self.responsable,
                        "user": self.user,
                    },
                )

                ejecuciones.append(ejecucion)

            ciclo.ejecuciones.exclude(ambito__in=ambitos).delete()

        return ejecuciones

    def __str__(self):
        return f"{self.id} - {self.plan}: {self.get_estado}"


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
        try:
            evidencia = self.evidencia_registrada
        except Evidencia.DoesNotExist:
            return False

        return bool(evidencia.archivo)

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
    ejecucion = models.OneToOneField(
        Ejecucion,
        on_delete=models.CASCADE,
        related_name="evidencia_registrada",
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
