from django.db import migrations, models
import core.notification_schedule


class Migration(migrations.Migration):
    dependencies = [("pas", "0029_auditoria_evidencias")]
    operations = [migrations.CreateModel(
        name="CalendarioNotificaciones",
        fields=[
            ("id", models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False, serialize=False)),
            ("dias", models.JSONField(default=core.notification_schedule.dias_laborables, validators=[core.notification_schedule.validar_dias])),
        ],
    )]
