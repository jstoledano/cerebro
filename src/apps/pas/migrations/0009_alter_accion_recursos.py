# Generated by Django 5.0.6 on 2024-09-10 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pas', '0008_accion_evidencia_alter_seguimiento_fecha'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accion',
            name='recursos',
            field=models.CharField(blank=True, help_text='Recursos necesarios para realizar la actividad', max_length=255, null=True),
        ),
    ]