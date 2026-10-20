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


class Plan(TrackingFields):
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

    def __str__(self):
        return "%s - %s" % (self.folio, self.nombre)

    @property
    def siglas(self):
        if self.documento == CNC:
            return "CNC"
        elif self.documento == PCM:
            return "PCM"
        return "N/A"


class Accion(TrackingFields):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
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
        max_length=255, blank=True, null=True, help_text="Evidencia documental esperada"
    )
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)

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
    def responsable_display(self):
        return user_display_name(self.responsable)

    @property
    def get_estado(self):
        """Regresa el estado de una acción correctiva, de acuerdo al último seguimiento capturado."""
        latest = self._latest_seguimiento()
        if latest and latest.estado == CERRADA:
            return "Cerrada"

        fecha_limite = self.fecha_fin
        hoy = django.utils.timezone.localdate()
        if fecha_limite and fecha_limite < hoy:
            return "Abierta Fuera de Tiempo"
        return "Abierta en Tiempo"

    @property
    def estado_operativo(self):
        latest = self._latest_seguimiento()

        if not latest:
            return None

        return latest.get_estado_display()

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

    def __str__(self):
        return f"{self.id} - {self.plan}: {self.get_estado}"


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
