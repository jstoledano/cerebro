# Generated by Django 5.0.6 on 2024-09-18 19:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kpi', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='record',
            options={'ordering': ('period__kpi', 'date'), 'verbose_name': 'Registro', 'verbose_name_plural': 'Registros'},
        ),
        migrations.RemoveField(
            model_name='kpi',
            name='lapse',
        ),
        migrations.RemoveField(
            model_name='kpi',
            name='nominal',
        ),
        migrations.RemoveField(
            model_name='kpi',
            name='period',
        ),
        migrations.RemoveField(
            model_name='kpi',
            name='period_begin',
        ),
        migrations.RemoveField(
            model_name='kpi',
            name='period_end',
        ),
        migrations.RemoveField(
            model_name='kpi',
            name='target',
        ),
        migrations.RemoveField(
            model_name='record',
            name='kpi',
        ),
        migrations.CreateModel(
            name='Period',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', models.CharField(help_text='Descripción o nombre del periodo de tiempo', max_length=255, verbose_name='Periodo')),
                ('start', models.DateField(help_text='Fecha de inicio del periodo', verbose_name='Inicio')),
                ('end', models.DateField(help_text='Fecha de fin del periodo', verbose_name='Fin')),
                ('target', models.FloatField(verbose_name='Meta')),
                ('nominal', models.FloatField(verbose_name='Nominativo')),
                ('active', models.BooleanField(default=True, verbose_name='Activo')),
                ('kpi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kpi.kpi')),
            ],
            options={
                'verbose_name': 'Periodo',
                'verbose_name_plural': 'Periodos',
                'ordering': ('kpi', 'period'),
            },
        ),
        migrations.AddField(
            model_name='record',
            name='period',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='kpi.period'),
            preserve_default=False,
        ),
    ]
