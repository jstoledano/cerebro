from django.db import models

from apps.pusinex.models import Manzana, Seccion


class RegistroArt141(models.Model):
    fuar = models.CharField(
        max_length=13,
        unique=True,
        null=True,
        blank=True,
    )

    ciudadano_id = models.CharField(
        max_length=100,
        db_index=True,
    )

    fecha_solicitud_tramite = models.DateField(
        null=True,
        blank=True,
    )

    fecha_entrega_credencial = models.DateField(
        null=True,
        blank=True,
    )

    estatusciudadano_id = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    # Ubicación geoelectoral reportada en la fuente
    entidad = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    distrito = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    municipio = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    seccion_origen = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    localidad = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    manzana_origen = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    # Relación con el MGE actual
    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="registros_art141",
        null=True,
        blank=True,
    )

    manzana = models.ForeignKey(
        Manzana,
        on_delete=models.PROTECT,
        related_name="registros_art141",
        null=True,
        blank=True,
    )

    edad = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    sexo = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    created = models.DateTimeField(
        auto_now_add=True,
    )

    updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ciudadano_id",
                    "fecha_solicitud_tramite",
                ],
                name="uniq_art141_ciudadano_fecha",
            ),
        ]

    def __str__(self):
        return f"Art. 141 | FUAR {self.fuar}"
