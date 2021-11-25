# Generated by Django 3.2.9 on 2021-11-24 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Idea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.PositiveSmallIntegerField(choices=[(0, 'Idea'), (1, 'Proyecto')], verbose_name='Tipo')),
                ('name', models.CharField(max_length=120, verbose_name='Nombre')),
                ('contact', models.CharField(max_length=100, verbose_name='Contacto')),
                ('site', models.CharField(max_length=30, verbose_name='Sitio')),
                ('desc', models.TextField(verbose_name='Descripción')),
                ('results', models.TextField(blank=True, null=True, verbose_name='Results')),
                ('docs', models.FileField(blank=True, null=True, upload_to='ideas')),
                ('evidence', models.FileField(blank=True, null=True, upload_to='ideas')),
            ],
        ),
    ]
