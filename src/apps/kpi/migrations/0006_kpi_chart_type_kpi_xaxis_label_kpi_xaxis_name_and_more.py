# Generated by Django 5.0.6 on 2024-09-25 16:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kpi', '0005_record_cumulative_percentage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kpi',
            name='chart_type',
            field=models.CharField(blank=True, help_text='Tipo de gráfica', max_length=50, null=True, verbose_name='Gráfica'),
        ),
        migrations.AddField(
            model_name='kpi',
            name='xaxis_label',
            field=models.CharField(blank=True, help_text='Etiqueta para el eje de las X', max_length=50, null=True, verbose_name='Etiqueta X'),
        ),
        migrations.AddField(
            model_name='kpi',
            name='xaxis_name',
            field=models.CharField(blank=True, help_text='Unidad de medida del eje X', max_length=50, null=True, verbose_name='Eje X'),
        ),
        migrations.AddField(
            model_name='kpi',
            name='yaxis_label',
            field=models.CharField(blank=True, help_text='Etiqueta para el eje de las Y', max_length=50, null=True, verbose_name='Etiqueta Y'),
        ),
        migrations.AddField(
            model_name='kpi',
            name='yaxis_name',
            field=models.CharField(blank=True, help_text='Unidad de medida del eje Y', max_length=50, null=True, verbose_name='Eje Y'),
        ),
    ]
