# Generated by Django 2.1 on 2018-08-28 02:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('productividad', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalPronosticoTramites',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(verbose_name='Año')),
                ('distrito', models.PositiveSmallIntegerField(choices=[(1, 'Distrito 01'), (2, 'Distrito 02'), (3, 'Distrito 03')])),
                ('tramites', models.SmallIntegerField()),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical pronostico tramites',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='PronosticoTramites',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(verbose_name='Año')),
                ('distrito', models.PositiveSmallIntegerField(choices=[(1, 'Distrito 01'), (2, 'Distrito 02'), (3, 'Distrito 03')])),
                ('tramites', models.SmallIntegerField()),
            ],
        ),
        migrations.AlterModelOptions(
            name='reporte',
            options={'get_latest_by': 'fecha_corte', 'ordering': ['remesa'], 'verbose_name': 'Reporte de Productividad', 'verbose_name_plural': 'Reportes de Productividad'},
        ),
    ]
