# Generated by Django 5.0.6 on 2024-09-09 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pas', '0005_alter_accion_responsable_alter_plan_proposito'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accion',
            name='responsable',
            field=models.CharField(blank=True, help_text='Iniciales del Responsable', max_length=5, null=True),
        ),
    ]
