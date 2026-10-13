from django.db import models

from apps.pusinex.models import Localidad, Manzana, Seccion


class TramiteArt141(models.Model):
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

    fecha_afectacion_padron = models.DateField(
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

    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.SET_NULL,
        related_name="tramites_art141",
        null=True,
        blank=True,
    )

    localidad_mge = models.ForeignKey(
        Localidad,
        on_delete=models.SET_NULL,
        related_name="tramites_art141",
        null=True,
        blank=True,
    )

    manzana = models.ForeignKey(
        Manzana,
        on_delete=models.SET_NULL,
        related_name="tramites_art141",
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
        verbose_name = "Trámite Artículo 141"
        verbose_name_plural = "Trámites Artículo 141"
        ordering = [
            "fecha_solicitud_tramite",
            "fuar",
        ]

    def __str__(self):
        return (
            f"Art. 141 | "
            f"FUAR {self.fuar} | "
            f"{self.ciudadano_id}"
        )


class UniversoVA(models.Model):
    ciudadano_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    activo = models.BooleanField(
        default=False,
        db_index=True,
    )

    presente_fuente = models.BooleanField(
        default=False,
    )

    estatusciudadano_id = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    fecha_solicitud_tramite = models.DateField(
        null=True,
        blank=True,
    )

    fecha_entrega_credencial = models.DateField(
        null=True,
        blank=True,
    )

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

    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.SET_NULL,
        related_name="universo_va",
        null=True,
        blank=True,
    )

    localidad_mge = models.ForeignKey(
        Localidad,
        on_delete=models.SET_NULL,
        related_name="universo_va",
        null=True,
        blank=True,
    )

    manzana = models.ForeignKey(
        Manzana,
        on_delete=models.SET_NULL,
        related_name="universo_va",
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

    ultima_presencia = models.DateTimeField(
        null=True,
        blank=True,
    )

    created = models.DateTimeField(
        auto_now_add=True,
    )

    updated = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Persona en universo VA"
        verbose_name_plural = "Personas en universo VA"
        ordering = [
            "distrito",
            "seccion_origen",
            "ciudadano_id",
        ]

    def __str__(self):
        return (
            f"VA | "
            f"{self.ciudadano_id} | "
            f"{'Activo' if self.activo else 'Inactivo'}"
        )
