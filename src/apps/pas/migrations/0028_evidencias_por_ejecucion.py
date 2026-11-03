import django.db.models.deletion
from django.db import migrations, models


def verificar_evidencias_vinculadas(apps, schema_editor):
    Evidencia = apps.get_model("pas", "Evidencia")
    alias = schema_editor.connection.alias

    pendientes = (
        Evidencia.objects.using(alias)
        .filter(ejecucion__isnull=True)
        .count()
    )

    if pendientes:
        raise RuntimeError(
            f"Existen {pendientes} evidencias sin ejecución. "
            "Asigna su ejecución antes de aplicar esta migración."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("pas", "0027_alter_accion_periodicidad"),
    ]

    operations = [
        migrations.RunPython(
            verificar_evidencias_vinculadas,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="evidencia",
            name="ejecucion",
            field=models.ForeignKey(
                to="pas.ejecucion",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="evidencias",
                help_text=(
                    "Ejecución concreta a la que corresponde "
                    "el archivo de evidencia."
                ),
            ),
        ),
    ]
