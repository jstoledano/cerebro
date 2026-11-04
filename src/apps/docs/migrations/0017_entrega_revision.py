from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("docs", "0016_revision_checksum_algoritmo_and_more"), ("pmml", "0002_envio_correo")]
    operations = [migrations.CreateModel(
        name="EntregaRevision",
        fields=[
            ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("destinatario", models.EmailField(max_length=254)),
            ("revision", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entregas_correo", to="docs.revision")),
            ("envio", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="revisiones_documentales", to="pmml.enviocorreo")),
        ], options={"constraints": [models.UniqueConstraint(fields=("revision", "destinatario"), name="docs_revision_destinatario_unico")]},
    )]
