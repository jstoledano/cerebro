# Generated by Django 2.0.5 on 2018-05-28 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dpi', '0002_auto_20180528_1512'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expedientedpi',
            name='delta_aclarar',
            field=models.SmallIntegerField(editable=False, help_text='Delta entre notificación y entrevista', null=True),
        ),
        migrations.AlterField(
            model_name='expedientedpi',
            name='delta_distrito',
            field=models.SmallIntegerField(editable=False, help_text='Delta entre tramite y envío a JL', null=True),
        ),
        migrations.AlterField(
            model_name='expedientedpi',
            name='delta_entrevista',
            field=models.SmallIntegerField(editable=False, help_text='Delta entre notificación y entrevista', null=True),
        ),
        migrations.AlterField(
            model_name='expedientedpi',
            name='delta_enviar',
            field=models.SmallIntegerField(editable=False, help_text='Delta entre entrevista y envío a JL', null=True),
        ),
        migrations.AlterField(
            model_name='expedientedpi',
            name='delta_notificar',
            field=models.SmallIntegerField(editable=False, help_text='Delta entre tramite y notificación', null=True),
        ),
        migrations.AlterField(
            model_name='expedientedpi',
            name='delta_verificar',
            field=models.SmallIntegerField(editable=False, help_text='Delta entre solicitud de verificación y ejecución de la cédula', null=True),
        ),
    ]
