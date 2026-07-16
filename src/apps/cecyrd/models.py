from django.db import models


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
