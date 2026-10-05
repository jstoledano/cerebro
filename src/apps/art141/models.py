from django.db import models

from apps.pusinex.models import Manzana, Seccion


class RegistroArt141(models.Model):
    ciudadano_id = models.CharField(
        max_length=100,
        db_index=True,
    )

    fecha_solicitud_afectacion = models.DateField(
        null=True,
        blank=True,
    )

    seccion = models.ForeignKey(
        Seccion,
        on_delete=models.PROTECT,
        related_name="registros_art141",
    )

    manzana = models.ForeignKey(
        Manzana,
        on_delete=models.PROTECT,
        related_name="registros_art141",
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

    folio_nacional = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    lista_nominal = models.BooleanField(
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
        verbose_name = "Registro Artículo 141"
        verbose_name_plural = "Registros Artículo 141"
        ordering = [
            "seccion__distrito__distrito",
            "seccion__municipio__municipio",
            "seccion__seccion",
            "manzana__localidad",
            "manzana__manzana",
        ]

    def __str__(self):
        return (
            f"Art. 141 | "
            f"Ciudadano {self.ciudadano_id} | "
            f"Sección {self.seccion.seccion:04d}"
        )
