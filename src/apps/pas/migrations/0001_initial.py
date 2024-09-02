# Generated by Django 5.0.6 on 2024-08-28 21:44

import django.db.models.deletion
import django.utils.timezone
import tinymce.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('nombre', models.CharField(help_text='Nombre del Plan de Acción', max_length=255)),
                ('documento', models.IntegerField(choices=[(1, 'Cédula de No Conformidad'), (2, 'Plan de Cambios y Mejoras al SGC')])),
                ('folio', models.CharField(max_length=20)),
                ('fecha_llenado', models.DateField(default=django.utils.timezone.now, verbose_name='Fecha de Llenado')),
                ('fecha_deteccion', models.DateField(blank=True, null=True, verbose_name='Fecha de Detección')),
                ('tipo', models.IntegerField(choices=[(1, 'Corrección'), (2, 'Acción Correctiva'), (3, 'Riesgo')], help_text='Tipo de acción requerida')),
                ('desc_cnc', tinymce.models.HTMLField(blank=True, default='', null=True)),
                ('fuente', models.IntegerField(choices=[(1, 'Auditoría Externa'), (2, 'Auditoría Interna'), (3, 'Queja del cliente'), (4, 'Revisión por la Dirección'), (5, 'Proceso'), (6, 'Documentación del SGC'), (7, 'Objetivos e Indicadores'), (8, 'Evaluación de riesgos'), (9, 'Otros')])),
                ('otra_fuente', models.TextField(blank=True, null=True)),
                ('fecha_termino', models.DateField(blank=True, null=True, verbose_name='Fecha de Término')),
                ('proposito', models.TextField(blank=True, help_text='Propósito del cambio o mejora al SGC', null=True)),
                ('requisito', models.TextField(blank=True, help_text='Requisito(s) de ISO 9001:2015 afectado(s) y/o beneficiados', null=True)),
                ('proceso', models.IntegerField(choices=[(1, 'Estratégico'), (2, 'Sustantivos'), (3, 'Soporte'), (4, 'Medición, Análisis y Mejora'), (5, 'SGC')])),
                ('desc_pcm', tinymce.models.HTMLField(blank=True, default='', help_text='Descripción del cambio o mejora al SGC', null=True)),
                ('consecuencias', tinymce.models.HTMLField(blank=True, default='', help_text='Consecuencias potenciales de que el cambio o mejora no se realice', null=True)),
                ('analisis', tinymce.models.HTMLField(blank=True, default='', help_text='Análisis de la causa raíz', null=True)),
                ('correccion', tinymce.models.HTMLField(blank=True, default='', help_text='Corrección (si aplica)', null=True)),
                ('evidencia_analisis', models.FileField(blank=True, null=True, upload_to='pas')),
                ('eliminacion', models.BooleanField(default=False)),
                ('txt_eliminacion', tinymce.models.HTMLField(blank=True, null=True)),
                ('recurrencia', models.BooleanField(default=False)),
                ('txt_recurrencia', tinymce.models.HTMLField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Plan de Acción',
                'verbose_name_plural': 'Planes de Acción',
            },
        ),
        migrations.CreateModel(
            name='Accion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('accion', tinymce.models.HTMLField()),
                ('recursos', tinymce.models.HTMLField(blank=True, null=True)),
                ('fecha_inicio', models.DateField(blank=True, null=True)),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('responsable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pas_responsable', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pas.plan')),
            ],
            options={
                'verbose_name': 'Actividad',
                'verbose_name_plural': 'Actividades',
            },
        ),
        migrations.CreateModel(
            name='Seguimiento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('descripcion', tinymce.models.HTMLField()),
                ('fecha', models.DateField()),
                ('evidencia', models.FileField(blank=True, null=True, upload_to='pas')),
                ('estado', models.IntegerField(choices=[(1, 'Seguimiento'), (2, 'Revisión de Evidencia'), (3, 'En espera de una respuesta'), (4, 'En espera de una acción'), (5, 'En espera de un evento'), (99, 'Cerrada')])),
                ('accion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pas.accion')),
                ('responsable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pas_seguimiento_responsable', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Seguimiento de Acciones',
                'verbose_name_plural': 'Seguimiento',
                'get_latest_by': 'fecha',
            },
        ),
    ]
