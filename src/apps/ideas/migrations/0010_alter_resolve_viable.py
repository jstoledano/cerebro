# Generated by Django 5.0.6 on 2024-08-27 20:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ideas', '0009_alter_resolve_resolve'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resolve',
            name='viable',
            field=models.IntegerField(choices=[(0, 'En espera'), (1, 'No viable'), (2, 'Viable')], default=0, help_text='Selecciona si la idea es viable o no', verbose_name='Viable'),
        ),
    ]
