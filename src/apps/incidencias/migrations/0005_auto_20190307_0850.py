# Generated by Django 2.1.3 on 2019-03-07 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('incidencias', '0004_auto_20190227_1130'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidencia',
            name='all_day',
            field=models.BooleanField(default=False, verbose_name='Todo el día'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='incidencia',
            name='modulo',
            field=models.CharField(choices=[('290151', '290151'), ('290152', '290152'), ('290153', '290153'), ('290251', '290251'), ('290252', '290252'), ('290253', '290253'), ('290254', '290254'), ('290351', '290351'), ('290352', '290352'), ('290353', '290353'), ('999999', 'Todos los MAC')], max_length=6),
        ),
    ]
