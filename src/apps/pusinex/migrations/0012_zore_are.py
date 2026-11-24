# Incorporacion de ZORE y ARE informativas al MGE.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pusinex", "0011_pelnresidualseccion")]

    operations = [
        migrations.CreateModel(
            name="Zore",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("numero", models.PositiveSmallIntegerField()),
                ("supervisor_nombre", models.CharField(blank=True, default="", max_length=200)),
                ("supervisor_correo", models.EmailField(blank=True, default="", max_length=254)),
                ("supervisor_telefono", models.CharField(blank=True, default="", max_length=60)),
                ("distrito", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="zores", to="pusinex.distrito")),
            ],
            options={
                "verbose_name": "ZORE",
                "verbose_name_plural": "ZORE",
                "ordering": ["distrito_id", "numero"],
                "permissions": [("ver_personal_zore_are", "Puede consultar los datos personales de supervisores y CAE")],
                "constraints": [models.UniqueConstraint(fields=("distrito", "numero"), name="pusinex_zore_distrito_numero_uniq")],
            },
        ),
        migrations.CreateModel(
            name="Are",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("numero", models.PositiveSmallIntegerField()),
                ("cae_nombre", models.CharField(blank=True, default="", max_length=200)),
                ("cae_correo", models.EmailField(blank=True, default="", max_length=254)),
                ("cae_telefono", models.CharField(blank=True, default="", max_length=60)),
                ("distrito", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ares", to="pusinex.distrito")),
                ("zore", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ares", to="pusinex.zore")),
            ],
            options={
                "verbose_name": "ARE",
                "verbose_name_plural": "ARE",
                "ordering": ["distrito_id", "numero"],
                "constraints": [models.UniqueConstraint(fields=("distrito", "numero"), name="pusinex_are_distrito_numero_uniq")],
            },
        ),
        migrations.CreateModel(
            name="SeccionAre",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("casillas_ln", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("are", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asignaciones", to="pusinex.are")),
                ("seccion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asignaciones_are", to="pusinex.seccion")),
            ],
            options={
                "verbose_name": "Asignacion seccion-ARE",
                "verbose_name_plural": "Asignaciones seccion-ARE",
                "ordering": ["seccion_id", "are__numero"],
                "constraints": [models.UniqueConstraint(fields=("seccion", "are"), name="pusinex_seccion_are_uniq")],
            },
        ),
    ]
