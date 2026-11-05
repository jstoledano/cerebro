import uuid
from django.db import models


class Subscriber(models.Model):
    nombre_completo = models.CharField(max_length=255)
    usuario_inst = models.CharField(
        max_length=150,
        unique=True,
        help_text="Usuario institucional (ej. javier.sanchezt)",
    )
    is_active = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.usuario_inst

    @property
    def email_full(self):
        usuario = self.usuario_inst.strip().lower()
        return usuario if usuario.endswith("@ine.mx") else f"{usuario}@ine.mx"



class EnvioCorreo(models.Model):
    """Mensaje y resultado SMTP. La aceptación SMTP no confirma lectura ni bandeja."""
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIANDO = "enviando", "En curso; revisar si quedó interrumpido"
        ACEPTADO = "aceptado", "Aceptado por SMTP"
        FALLIDO = "fallido", "Rechazado; permite reintento explícito"
        INCIERTO = "incierto", "Resultado incierto; requiere revisión"

    clave = models.CharField(max_length=255, unique=True)
    destinatario = models.EmailField()
    tipo = models.CharField(max_length=20)
    fecha = models.DateField()
    asunto = models.CharField(max_length=255)
    texto = models.TextField()
    html = models.TextField()
    responder_a = models.JSONField(default=list, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    documentado = models.BooleanField(default=False)
    intentos = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    message_id = models.CharField(max_length=255, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    aceptado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado", "-pk"]
