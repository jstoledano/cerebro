# Generated by Django 3.1 on 2020-11-26 21:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metas', '0004_auto_20200410_1247'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goal',
            name='fields',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='proof',
            name='fields',
            field=models.JSONField(blank=True, null=True, verbose_name='Campos'),
        ),
    ]
