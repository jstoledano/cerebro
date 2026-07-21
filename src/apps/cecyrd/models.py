from django.db import models
from django.contrib.auth.models import User


class Tramite(models.Model):
    folio = models.CharField(max_length=13, primary_key=True)
    estatus = models.TextField(blank=True, null=True)
    causa_rechazo = models.TextField(blank=True, null=True)
    movimiento_solicitado = models.TextField(blank=True, null=True)
    movimiento_definitivo = models.TextField(blank=True, null=True)

    fecha_tramite = models.DateTimeField(blank=True, null=True)
    fecha_recibido_cecyrd = models.DateTimeField(blank=True, null=True)
    fecha_registrado_cecyrd = models.DateTimeField(blank=True, null=True)
    fecha_rechazado = models.DateTimeField(blank=True, null=True)
    fecha_cancelado_movimiento_posterior = models.DateTimeField(blank=True, null=True)
    fecha_alta_pe = models.DateTimeField(blank=True, null=True)
    fecha_afectacion_padron = models.DateTimeField(blank=True, null=True)
    fecha_actualizacion_pe = models.DateTimeField(blank=True, null=True)
    fecha_reincorporacion_pe = models.DateTimeField(blank=True, null=True)
    fecha_exitoso = models.DateTimeField(blank=True, null=True)
    fecha_lote_produccion = models.DateTimeField(blank=True, null=True)
    fecha_listo_reimpresion = models.DateTimeField(blank=True, null=True)
    fecha_cpv_creada = models.DateTimeField(blank=True, null=True)
    fecha_cpv_registrada_mac = models.DateTimeField(blank=True, null=True)
    fecha_cpv_disponible = models.DateTimeField(blank=True, null=True)
    fecha_cpv_entregada = models.DateTimeField(blank=True, null=True)
    fecha_afectacion_ln = models.DateTimeField(blank=True, null=True)

    distrito = models.SmallIntegerField()
    mac = models.CharField(max_length=6)

    # Interval se mapea a DurationField en Django
    tramo_disponible = models.DurationField(blank=True, null=True)
    tramo_entrega = models.DurationField(blank=True, null=True)
    tramo_exitoso = models.DurationField(blank=True, null=True)

    class Meta:
        db_table = "tramites"
        # Añadimos el índice que tenías en el SQL original para rendimiento
        indexes = [
            models.Index(fields=["folio"], name="tramites_folio_idx"),
        ]

    def __str__(self):
        return self.folio


class RevisionDireccion(models.Model):
    # Metadatos del Periodo
    periodo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Identificador único del semestre, ej. 'sem1_2026'"
    )
    fecha_cierre = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Usuario que generó el cierre inicial"
    )

    # Capa de Datos Ciega e Inmutable (KPIs Congelados)
    total_tramites = models.PositiveIntegerField(default=0)
    analizados = models.PositiveIntegerField(default=0)
    en_tiempo = models.PositiveIntegerField(default=0)
    rezago = models.PositiveIntegerField(default=0)
    porcentaje_global = models.FloatField(default=0.0)
    promedio_dias = models.FloatField(default=0.0)

    # Capa Humana Editable (Para el usuario "altamente falible")
    conclusiones = models.TextField(
        blank=True,
        default="",
        help_text="Observaciones analíticas del responsable"
    )
    recomendaciones = models.TextField(
        blank=True,
        default="",
        help_text="Acciones correctivas o de mejora continua"
    )

    # Trazabilidad Oficial
    pdf_oficial = models.FileField(
        upload_to='cecyrd/portadas/',
        blank=True,
        null=True,
        help_text="Fotografía institucional inmutable del periodo generada post-ETL"
    )

    class Meta:
        verbose_name = "Revisión por la Dirección"
        verbose_name_plural = "Revisiones por la Dirección"
        ordering = ['-fecha_cierre']

    def __str__(self):
        return f"Revisión {self.periodo} - Cumplimiento: {self.porcentaje_global}%"
