# Generated by Django 5.0.6 on 2024-08-29 21:29

import tinymce.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pas', '0003_remove_plan_fecha_deteccion_plan_fecha_inicio_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='consecuencias',
            field=tinymce.models.HTMLField(blank=True, default='', help_text='Consecuencias potenciales de que el cambio o mejora no se realice', null=True, verbose_name='Consecuencias'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='desc_pcm',
            field=tinymce.models.HTMLField(blank=True, default='', help_text='Descripción del cambio o mejora al SGC', null=True, verbose_name='Descripción'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='fecha_inicio',
            field=models.DateField(blank=True, help_text='Fecha en la que se inició el Plan de Cambios y Mejoras', null=True, verbose_name='Fecha de Inicio'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='fecha_termino',
            field=models.DateField(blank=True, help_text='Fecha en la que se terminará el Plan de Cambios y Mejoras', null=True, verbose_name='Fecha de Término'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='proceso',
            field=models.IntegerField(blank=True, choices=[(1, 'Estratégico'), (2, 'Sustantivos'), (3, 'Soporte'), (4, 'Medición, Análisis y Mejora'), (5, 'SGC')], help_text='Proceso(s) del SGC afectado(s) y/o beneficiados', null=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='proposito',
            field=tinymce.models.HTMLField(blank=True, help_text='Propósito del cambio o mejora al SGC', null=True, verbose_name='Propósito'),
        ),
        migrations.AlterField(
            model_name='plan',
            name='requisito',
            field=models.CharField(blank=True, help_text='Requisito(s) de ISO 9001:2015 afectado(s) y/o beneficiados', max_length=255, null=True),
        ),
    ]
