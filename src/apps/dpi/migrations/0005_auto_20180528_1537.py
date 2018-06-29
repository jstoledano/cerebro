# Generated by Django 2.0.5 on 2018-05-28 20:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dpi', '0004_auto_20180528_1530'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expedientedpi',
            name='estado',
            field=models.PositiveSmallIntegerField(choices=[(0, 'No indica'), (1, 'Rechazado'), (2, 'Error en MAC'), (3, 'Aclarado')], default=0, help_text='Estado del trámite'),
        ),
    ]