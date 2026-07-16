from django.contrib.auth.models import User
from django.contrib.gis.db import models

CAT_TIPO = (
    (1, 'URBANO CONCENTRADO'),
    (2, 'URBANO(A)'),
    (3, 'MIXTO'),
    (4, 'RURAL'),
    (5, 'RURAL DISPERSO')
)

CAT_CABECERA = (
    (1, 'CAPITAL DEL ESTADO'),
    (2, 'CABECERA DISTRITAL'),
    (3, 'CABECERA MUNICIPAL'),
    (4, 'CABECERA SECCIONAL')
)


# Función para subir archivos en models.py
def pusinex_file(p, file):
    import os.path

    ext = file.split(".")[-1]

    # AQUÍ ESTÁ LA MAGIA: Forzamos el doble nivel de carpeta requerido
    orig = os.path.join("pusinex", "pusinex")

    distrito = p.seccion.distrito.distrito
    municipio = p.seccion.municipio.municipio
    seccion = p.seccion.seccion
    nombre = f"29{distrito:02}{municipio:03}{seccion:04}_rev{p.f_act:%Y%m%d}.{ext}"
    ruta = os.path.join(orig, f"{distrito:02}", nombre)
    return ruta


class Entidad(models.Model):
    entidad = models.PositiveSmallIntegerField(primary_key=True)
    nombre = models.TextField()
    circunscripcion = models.PositiveSmallIntegerField()
    ubica = models.TextField(help_text="Coordenadas geográficas de la Junta Local", default='')
    pe = models.PositiveIntegerField(
        default=0, help_text="Padrón Electoral precalculado"
    )
    ln = models.PositiveIntegerField(
        default=0, help_text="Lista Nominal precalculada"
    )

    geom = models.MultiPolygonField(srid=32614, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Entidades'
        ordering = ['entidad', ]

    def __str__(self):
        return f'{self.entidad:02} {self.nombre}'


class Distrito(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    distrito = models.PositiveSmallIntegerField(primary_key=True)
    tipo = models.PositiveSmallIntegerField()
    cabecera = models.TextField()
    ubica = models.TextField(help_text="Coordinadas de la ubicación del distrito", default='')
    distancia = models.PositiveIntegerField(blank=True, null=True)
    traslado = models.PositiveIntegerField(
        help_text="Tiempo de traslado al distrito en minutos",
        blank=True, null=True
    )
    pe = models.PositiveIntegerField(
        default=0, help_text="Padrón Electoral precalculado"
    )
    ln = models.PositiveIntegerField(
        default=0, help_text="Lista Nominal precalculada"
    )

    geom = models.MultiPolygonField(srid=32614, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Distritos'
        ordering = ['entidad', 'distrito']

    def __str__(self):
        return f'{self.entidad.entidad:02}-{self.distrito:02}'

    def get_distrito(self):
        return self.distrito


class DistritoLocal(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    distrito_local =models.PositiveSmallIntegerField(primary_key=True)
    cabecera = models.TextField()

    geom = models.MultiPolygonField(srid=32614, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Distritos Locales'
        ordering = ['entidad', 'distrito_local']

    def __str__(self):
        return f'{self.entidad.entidad:02}-{self.distrito_local:02}'


class Municipio(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    municipio = models.PositiveSmallIntegerField(primary_key=True)
    nombre = models.TextField()
    pe = models.PositiveIntegerField(
        default=0, help_text="Padrón Electoral precalculado"
    )
    ln = models.PositiveIntegerField(
        default=0, help_text="Lista Nominal precalculada"
    )

    geom = models.MultiPolygonField(srid=32614, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Municipios'
        ordering = ['entidad', 'municipio', ]

    def __str__(self):
        return f'{self.municipio:03} {self.nombre}'

    def get_pusinex(self):
        return self.seccion_set.filter(tipo__lt=4).count()


class Seccion(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    distrito = models.ForeignKey(Distrito, on_delete=models.CASCADE)
    distrito_l = models.ForeignKey(DistritoLocal, on_delete=models.CASCADE)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    seccion = models.PositiveSmallIntegerField(primary_key=True)
    tipo = models.PositiveSmallIntegerField(choices=CAT_TIPO)
    activa = models.BooleanField(default=True)
    ubica = models.TextField(
        help_text="Coordinadas de la ubicación de la sección", default=""
    )
    distancia = models.PositiveIntegerField(blank=True, null=True)
    traslado = models.PositiveIntegerField(
        help_text="Tiempo de traslado a la sección en minutos",
        blank=True, null=True
    )
    pe = models.PositiveIntegerField(
        default=0, help_text="Padrón Electoral precalculado"
    )
    ln = models.PositiveIntegerField(
        default=0, help_text="Lista Nominal precalculada"
    )

    geom = models.MultiPolygonField(srid=32614, null=True, blank=True)

    class Meta:
        verbose_name = 'Sección'
        verbose_name_plural = 'Secciones'
        ordering = ['distrito__distrito', 'municipio__municipio', 'seccion', ]

    def __str__(self):
        return f'{self.distrito.distrito:02} {self.municipio.municipio:03} {self.seccion:04}'


class Pusinex(models.Model):
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)
    f_act = models.DateField()
    hojas = models.PositiveSmallIntegerField()
    observaciones = models.TextField(blank=True, null=True)
    archivo = models.FileField(upload_to=pusinex_file, blank=True, null=True)
    # Trazabilidad
    user = models.ForeignKey(User, editable=False, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PUSINEX'
        verbose_name_plural = 'PUSINEXs'
        ordering = ['seccion__distrito__distrito', 'seccion__municipio__municipio', 'seccion__seccion', ]
        get_latest_by = ["f_act", ]

    def __str__(self):
        d = self.seccion.distrito.distrito
        m = self.seccion.municipio.municipio
        s = self.seccion.seccion
        return f'29{d:02}{m:02}{s:04}_rev{self.f_act:%Y%m%d}'


class Manzana(models.Model):
    # Relacionamos directamente con la Sección.
    # Usamos related_name="manzanas" para poder hacer: mi_seccion.manzanas.all()
    seccion = models.ForeignKey(
        Seccion, on_delete=models.CASCADE, related_name="manzanas"
    )

    localidad = models.PositiveSmallIntegerField()
    manzana = models.PositiveSmallIntegerField()
    padron = models.PositiveIntegerField(default=0)
    lista_nominal = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Manzana"
        verbose_name_plural = "Manzanas"
        # Esto evita que haya manzanas duplicadas en la misma localidad y sección
        unique_together = ("seccion", "localidad", "manzana")
        ordering = ["seccion", "localidad", "manzana"]

    def __str__(self):
        return f"Sec: {self.seccion_id} | Loc: {self.localidad} | Mz: {self.manzana}"
