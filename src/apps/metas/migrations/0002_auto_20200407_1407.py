# Generated by Django 3.0.4 on 2020-04-07 19:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metas', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='goal',
            old_name='cicles',
            new_name='loops',
        ),
    ]