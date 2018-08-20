# Generated by Django 2.1 on 2018-08-10 04:30

import apps.metas.models
from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Evidencia',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('fecha', models.DateField()),
                ('eval_calidad', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Evaluación del Criterio de Calidad')),
                ('eval_oportunidad', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Evaluación del Criterio de Oportunidad')),
                ('campos', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Evidencia',
                'verbose_name_plural': 'Evidencias',
            },
        ),
        migrations.CreateModel(
            name='MetasSPE',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('puesto', models.CharField(choices=[('VEL', 'Vocal Ejecutivo de Junta Local'), ('VSL', 'Vocal Secretario de Junta Local'), ('VRL', 'Vocal del RFE de Junta Local'), ('VCL', 'Vocal de Capacitación de Junta Local'), ('VOL', 'Vocal de Organización de Junta Local'), ('VED', 'Vocal Ejecutivo de Junta Distrital'), ('VSD', 'Vocal Secretario de Junta Distrital'), ('VRD', 'Vocal del RFE de Junta Distrital'), ('VCD', 'Vocal de Capacitación de Junta Distrital'), ('VOD', 'Vocal de Organización de Junta Distrital'), ('JOSA', 'JOSA'), ('JOSAD', 'JOSAD'), ('JMM', 'Jefe de Monitoreo a Módulos'), ('JOCE', 'Jefe de Cartografía'), ('RA', 'Rama Administrativa')], max_length=6, verbose_name='Cargo')),
                ('clave', models.CharField(max_length=2, verbose_name='Clave de la Meta')),
                ('nom_corto', models.CharField(max_length=25, verbose_name='Identificación')),
                ('year', models.PositiveIntegerField(verbose_name='Año')),
                ('ciclos', models.PositiveSmallIntegerField(verbose_name='Repeticiones')),
                ('description', models.TextField(verbose_name='Descripción de la Meta')),
                ('soporte', models.FileField(blank=True, null=True, upload_to=apps.metas.models.archivo_soporte, verbose_name='Soporte')),
                ('campos', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='meta_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Meta',
                'verbose_name_plural': 'Control de Metas del SPE',
            },
        ),
        migrations.AddField(
            model_name='evidencia',
            name='meta',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evidenciaFK_meta', to='metas.MetasSPE'),
        ),
        migrations.AddField(
            model_name='evidencia',
            name='miembro',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evidenciaFK_pipol', to=settings.AUTH_USER_MODEL, verbose_name='Miembro del SPE'),
        ),
        migrations.AddField(
            model_name='evidencia',
            name='usuario',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='evidenciaFK_usuario', to=settings.AUTH_USER_MODEL),
        ),
    ]
