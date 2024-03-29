# Generated by Django 4.2.4 on 2023-08-23 18:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0006_alter_documento_lmd'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reporte',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('causa', models.CharField(choices=[('1', 'No se puede descargar el documento'), ('2', 'El documento no es el correcto'), ('3', 'Hay una nueva versión del documento'), ('4', 'Otro problema')], max_length=1)),
                ('descripcion', models.TextField(blank=True)),
                ('correo', models.EmailField(max_length=254)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('documento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='docs.documento')),
            ],
            options={
                'verbose_name': 'Reporte',
                'verbose_name_plural': 'Reportes',
            },
        ),
    ]
