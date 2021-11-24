# Generated by Django 3.2.9 on 2021-11-24 22:18

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('ideas', '0002_idea_scope'),
    ]

    operations = [
        migrations.AlterField(
            model_name='idea',
            name='contact',
            field=models.CharField(help_text='Escribe tu correo electrónico o número telefónico', max_length=100, verbose_name='Contacto'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='desc',
            field=tinymce.models.HTMLField(help_text='Escribe tu idea o proyecto. Un proyecto es algo que quieres\n        implementar. Describe qué quieres lograr y cómo quieres lograrlo', verbose_name='Descripción'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='docs',
            field=models.FileField(blank=True, help_text='Sube los formatos que uses en tu proyecto en un solo zip', null=True, upload_to='ideas', verbose_name='Formatos'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='evidence',
            field=models.FileField(blank=True, help_text='Sube las evidencias que usaste en tu proyecto en un solo zip', null=True, upload_to='ideas', verbose_name='Evidencias'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='name',
            field=models.CharField(help_text='Escribe tu nombre', max_length=120, verbose_name='Nombre'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='results',
            field=tinymce.models.HTMLField(blank=True, help_text='Escribe los resultados que has obtenido con tu proyecto', null=True, verbose_name='Results'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='scope',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Proceso'), (1, 'Actividad'), (2, 'Sistema'), (3, 'Formato'), (4, 'Indicador'), (5, 'Objetivo')], default=0, help_text='Selecciona que vas a afectar con tu idea', verbose_name='Alcance'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='site',
            field=models.CharField(help_text='Escribe tu módulo o Junta', max_length=30, verbose_name='Sitio'),
        ),
        migrations.AlterField(
            model_name='idea',
            name='type',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Idea'), (1, 'Proyecto')], help_text='Selecciona si presentas una idea o un proyecto', verbose_name='Tipo'),
        ),
    ]