# Generated by Django 2.1.3 on 2019-02-13 16:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('productividad', '0005_auto_20180904_1030'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reporte',
            options={'get_latest_by': 'fecha_corte', 'verbose_name': 'Reporte de Productividad', 'verbose_name_plural': 'Reportes de Productividad'},
        ),
    ]
