# Generated by Django 5.2.4 on 2025-07-08 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kpi', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='campaign',
            options={'verbose_name': 'Campaña', 'verbose_name_plural': 'Campañas'},
        ),
        migrations.AlterModelOptions(
            name='tramitemensual',
            options={'verbose_name': 'Trámites'},
        ),
        migrations.AlterField(
            model_name='campaign',
            name='forecast',
            field=models.PositiveIntegerField(verbose_name='Pronóstico de trámites esperados'),
        ),
    ]
