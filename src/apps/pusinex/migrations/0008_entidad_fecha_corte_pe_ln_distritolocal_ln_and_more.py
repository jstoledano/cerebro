from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pusinex", "0007_cambiomge"),
    ]

    operations = [
        migrations.AddField(
            model_name="entidad",
            name="fecha_corte_pe_ln",
            field=models.DateField(
                blank=True,
                help_text="Fecha de corte del Padrón Electoral y Lista Nominal",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="distritolocal",
            name="ln",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lista Nominal precalculada",
            ),
        ),
        migrations.AddField(
            model_name="distritolocal",
            name="pe",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Padrón Electoral precalculado",
            ),
        ),
    ]
