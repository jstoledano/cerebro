# Generated by Django 2.1 on 2018-08-10 04:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('state', models.PositiveSmallIntegerField(choices=[(29, 'Tlaxcala')], default=29)),
                ('site', models.PositiveSmallIntegerField(choices=[(0, 'Junta Local'), (1, '01 Junta Distrital'), (2, '02 Junta Distrital'), (3, 'O3 Junta Distrital')], default=0)),
                ('position', models.CharField(choices=[('VEL', 'Vocal Ejecutivo de Junta Local'), ('VSL', 'Vocal Secretario de Junta Local'), ('VRL', 'Vocal del RFE de Junta Local'), ('VCL', 'Vocal de Capacitación de Junta Local'), ('VOL', 'Vocal de Organización de Junta Local'), ('VED', 'Vocal Ejecutivo de Junta Distrital'), ('VSD', 'Vocal Secretario de Junta Distrital'), ('VRD', 'Vocal del RFE de Junta Distrital'), ('VCD', 'Vocal de Capacitación de Junta Distrital'), ('VOD', 'Vocal de Organización de Junta Distrital'), ('JOSA', 'JOSA'), ('JOSAD', 'JOSAD'), ('JMM', 'Jefe de Monitoreo a Módulos'), ('JOCE', 'Jefe de Cartografía'), ('RA', 'Rama Administrativa')], default='RA', max_length=5)),
                ('order', models.PositiveSmallIntegerField(blank=True, default=99, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
