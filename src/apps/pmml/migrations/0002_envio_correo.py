from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pmml", "0001_initial")]
    operations = [migrations.CreateModel(
        name="EnvioCorreo",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("clave", models.CharField(max_length=255, unique=True)),
            ("destinatario", models.EmailField(max_length=254)),
            ("tipo", models.CharField(max_length=20)),
            ("fecha", models.DateField()),
            ("asunto", models.CharField(max_length=255)),
            ("texto", models.TextField()),
            ("html", models.TextField()),
            ("responder_a", models.JSONField(blank=True, default=list)),
            ("estado", models.CharField(choices=[("pendiente", "Pendiente"), ("enviando", "En curso; revisar si quedó interrumpido"), ("aceptado", "Aceptado por SMTP"), ("fallido", "Rechazado; permite reintento explícito"), ("incierto", "Resultado incierto; requiere revisión")], default="pendiente", max_length=12)),
            ("documentado", models.BooleanField(default=False)),
            ("intentos", models.PositiveIntegerField(default=0)),
            ("error", models.TextField(blank=True)),
            ("message_id", models.CharField(blank=True, max_length=255)),
            ("creado", models.DateTimeField(auto_now_add=True)),
            ("actualizado", models.DateTimeField(auto_now=True)),
            ("aceptado_en", models.DateTimeField(blank=True, null=True)),
        ], options={"ordering": ["-creado", "-pk"]},
    )]
