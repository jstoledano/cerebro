# Generated by Django 2.0.5 on 2018-06-22 18:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metas', '0006_metasspe_campos'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='metasspe',
            name='eval',
        ),
    ]
