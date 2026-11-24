"""Agrupaciones informativas ZORE/ARE sobre el marco geografico electoral.

Se conservan las geometrías registrales en Seccion. No se generan ni
almacenan poligonos nuevos para ZORE/ARE.
"""
from django.db import models


class Zore(models.Model):
    distrito = models.ForeignKey(
        "pusinex.Distrito", on_delete=models.CASCADE, related_name="zores"
    )
    numero = models.PositiveSmallIntegerField()
    supervisor_nombre = models.CharField(max_length=200, blank=True, default="")
    supervisor_correo = models.EmailField(blank=True, default="")
    supervisor_telefono = models.CharField(max_length=60, blank=True, default="")

    class Meta:
        verbose_name = "ZORE"
        verbose_name_plural = "ZORE"
        ordering = ["distrito_id", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["distrito", "numero"], name="pusinex_zore_distrito_numero_uniq"
            )
        ]
        permissions = [
            (
                "ver_personal_zore_are",
                "Puede consultar los datos personales de supervisores y CAE",
            ),
        ]

    def __str__(self):
        return f"Distrito {self.distrito_id:02d} - ZORE {self.numero:02d}"


class Are(models.Model):
    distrito = models.ForeignKey(
        "pusinex.Distrito", on_delete=models.CASCADE, related_name="ares"
    )
    zore = models.ForeignKey(Zore, on_delete=models.CASCADE, related_name="ares")
    numero = models.PositiveSmallIntegerField()
    cae_nombre = models.CharField(max_length=200, blank=True, default="")
    cae_correo = models.EmailField(blank=True, default="")
    cae_telefono = models.CharField(max_length=60, blank=True, default="")

    class Meta:
        verbose_name = "ARE"
        verbose_name_plural = "ARE"
        ordering = ["distrito_id", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["distrito", "numero"], name="pusinex_are_distrito_numero_uniq"
            )
        ]

    def __str__(self):
        return f"Distrito {self.distrito_id:02d} - ARE {self.numero:03d}"


class SeccionAre(models.Model):
    """Relacion seccion/ARE. Hasta dos ARE por seccion como regla del ETL.

    casillas_ln es un dato operativo de referencia, no una particion geografica.
    """
    seccion = models.ForeignKey(
        "pusinex.Seccion", on_delete=models.CASCADE, related_name="asignaciones_are"
    )
    are = models.ForeignKey(Are, on_delete=models.CASCADE, related_name="asignaciones")
    casillas_ln = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Asignacion seccion-ARE"
        verbose_name_plural = "Asignaciones seccion-ARE"
        ordering = ["seccion_id", "are__numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["seccion", "are"], name="pusinex_seccion_are_uniq"
            )
        ]

    def __str__(self):
        return f"Seccion {self.seccion_id:04d} - {self.are}"
