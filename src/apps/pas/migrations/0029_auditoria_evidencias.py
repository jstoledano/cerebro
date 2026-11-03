from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pas", "0028_evidencias_por_ejecucion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="evidencia", name="modificada_por",
            field=models.ForeignKey(
                blank=True, editable=False, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="evidencias_modificadas", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="EventoEvidencia",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evidencia_id", models.PositiveIntegerField(db_index=True)),
                ("identidad", models.CharField(max_length=255)),
                ("rol", models.CharField(max_length=20)),
                ("operacion", models.CharField(max_length=10)),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("anterior", models.JSONField(default=dict)),
                ("posterior", models.JSONField(default=dict)),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("ejecucion", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="eventos_evidencia", to="pas.ejecucion")),
            ],
            options={"ordering": ["-fecha", "-pk"], "default_permissions": ("view",)},
        ),
    ]
