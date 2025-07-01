"""
Modelos para la app docs.

Esta aplicación controla los documentos y registros del SGC.

Modelos:
- Tipo
- Proceso
- Documento
- Revision
"""

import os.path
from urllib.parse import urlparse
from os.path import basename
from django.db import models
from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify


User = get_user_model()


class Tipo (models.Model):
    """
    Clase Tipo.

    Modelo para manejar los diferentes tipos de documentos.
    Campos:
    - tipo -> CharField
    - slug -> CharField
    """

    tipo = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)

    def __str__(self) -> str:
        """Formato en texto de la salida del modelo."""
        return f'Tipo: {self.tipo}'


class Proceso (models.Model):
    """
    Clase Proceso.

    Modelo simple para el registro de procesos.
    Campos:
    - proceso -> CharField
    - tipo -> CharField
    """

    proceso = models.CharField(max_length=80)
    slug = models.CharField(max_length=80)

    def __str__(self) -> str:
        """Formato en texto de la salida del modelo."""
        nombre_proceso: str = ""
        if self.slug == 'sgc':
            nombre_proceso = 'Documentos del Sistema'
        elif self.slug == 'stn':
            nombre_proceso = 'Opiniones Técnicas de la STN'
        elif self.slug == 'coc':
            nombre_proceso = 'Oficios de la COC'
        elif self.slug == 'lmd':
            nombre_proceso = 'Lista Maestra de Documentos'
        else:
            nombre_proceso = self.proceso
        return f'Proceso {nombre_proceso}'


class Documento (models.Model):
    """
    Definición del Documento.

    Campos:
    - nombre: El nombre del documento
    - slug: Un nombre corto para identificar el documento
    - ruta: Un campo URL, útil para documentos externos (opcional)
    - activo: Campo lógico, True por default
    - proceso: Contenedor para indicar el proceso al que pertenece
    - tipo: Contenedor para indicar el tipo de documento.
    """

    # Identificación
    nombre = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)

    # Ruta
    ruta = models.URLField(blank=True, null=True)

    # Orden
    proceso = models.ForeignKey(Proceso, on_delete=models.CASCADE)
    tipo = models.ForeignKey(Tipo, on_delete=models.CASCADE)

    # Búsqueda
    lmd = models.BooleanField(
        "LMD",
        help_text="Pertenece a la Lista Maestra de Documentos",
        default=False
    )
    aprobado = models.BooleanField("Documento en aprobación", default=False)
    activo = models.BooleanField(default=True)
    texto_ayuda = models.TextField(blank=True)

    # Trazabilidad
    autor = models.ForeignKey(
        User, related_name='docs', editable=False, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadatos del modelo Documento."""

        ordering = ['tipo', 'id']

        def __str__(self):
            return "Metadatos del modelo Documento"

    def ext(self) -> str:
        """
        Función ext.

        Devuelve la extensión del documento.
        """
        try:
            return self.revision_set.latest('revision').archivo.url.split('.')[-1]
        except IndexError:
            return ""

    def save(self, *args, **kwargs) -> None:
        """Actividades antes de ejecutar save."""
        self.slug = slugify(self.nombre)
        super(Documento, self).save(*args, **kwargs)

    def clave(self) -> str:
        """
        Función clave.

        Devuelve la clave del documento, que es única y se forma por
        el tipo de documento (tres letras) y la identificación del
        documento.
        """
        return "%s-%02d" % (self.tipo.slug, self.id)

    def __str__(self) -> str:
        """Formato en texto del modelo."""
        return "%s (%s-%02d)" % (self.nombre, self.tipo.slug.upper(), self.id)

    def revision_actual(self) -> str:
        """Devuelve la revisión del documento como un entero."""
        try:
            return self.revision_set.latest('revision')
        except IndexError:
            return ""

    def f_actual(self) -> str:
        """Devuelve la fecha de la revisión actual del documento."""
        try:
            return self.revision_set.latest('revision').f_actualizacion
        except IndexError:
            return ""

    def r_actual(self):
        """Devuelve la revisión de un documento con ceros a la izquierda."""
        try:
            x = "%02d" % self.revision_set.order_by('-revision')[0].revision
            return x
        except IndexError:
            return ""

    def historial(self):
        """Devuelve el historial del documento."""
        return self.revision_set.order_by('-revision')[1:]

    def swf(self):
        """Devuelve el archivo sin extensión."""
        return f"{self.revision_set.latest('revision').archivo.url.split('.')[0]}.swf"
        
    def name(self) -> str:
        """
        Devuelve el nombre del archivo al que apunta el campo `ruta`.
        """
        return basename(self.ruta.strip()) if self.ruta else ""


def subir_documento(instancia, archivo) -> str:
    """Función auxiliar para renombrar y colocar archivos en su ruta."""
    ext = archivo.split('.')[-1]
    orig = 'docs'
    tipo = instancia.documento.tipo.slug
    doc = instancia.documento.slug
    rev = instancia.revision
    nombre = "%s_%s-%02d_rev%02d.%s" % (
        doc, tipo, instancia.documento.id, rev, ext)
    ruta = os.path.join(orig, tipo, nombre)
    return ruta


class Revision (models.Model):
    """
    Modelo Revision.

    Campos:
    - documento: referencia al modelo Documento
    - revision: entero. número de revisión
    - f_actualización: fecha de actualización
    - archivo: archivo del documento
    - cambios: registro de cambios
    """

    # Documento
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE)

    # Revisión y actualización
    revision = models.IntegerField()
    f_actualizacion = models.DateField()

    # Archivos de la revisión
    archivo = models.FileField(
        upload_to=subir_documento,
        blank=True,
        null=True
    )

    # Identificación de cambios
    cambios = models.TextField()

    # Trazabilidad
    autor = models.ForeignKey(
        User,
        related_name='revisions_user',
        editable=False,
        on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadatos del modelo Revision."""

        unique_together = (("documento", "revision"),)
        verbose_name: str = "Revisión"
        verbose_name_plural: str = "Control Revisiones"

    def __str__(self) -> str:
        """Formato en texto del modelo."""
        respuesta: str = f"""
{self.documento} rev {self.revision:02d} ({self.f_actualizacion}))
"""
        return respuesta
        
    def nombre(self) -> str:
        return basename(self.archivo.name)


class Reporte(models.Model):
    """
    Modelo Reporte.

    Almacena los reportes hecho con el botón de pánico. Permite hacer
    seguimiento de las acciones tomadas para resolver el problema.

    Campos
    - documento: referencia al modelo Documento
    - causa: la causa por la que se reporta el documento
    - descripcion: descripción del problema (es opcional)
    - correo: correo electrónico del usuario que reporta el problema
    """

    CAUSAS = (
        ('1', 'No se puede descargar el documento '),
        ('2', 'El proceso asignado no es correcto'),
        ('3', 'Hay una nueva versión del documento'),
        ('4', 'Documento faltante'),
        ('99', 'Otro problema')
    )

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE)
    causa = models.CharField(max_length=2, choices=CAUSAS)
    descripcion = models.TextField(blank=True)
    correo = models.EmailField()
    created = models.DateTimeField(auto_now_add=True)

    # Resolución del reporte
    resuelto = models.BooleanField(default=False)
    resolucion = models.TextField('Resolución', blank=True)
    resuelto_por = models.ForeignKey(
        User,
        editable=False,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    resuelto_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        """Metadatos del modelo Reporte."""

        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"

    def __str__(self) -> str:
        """Formato en texto del modelo."""
        return f"{self.documento} - {self.get_causa_display()}"


