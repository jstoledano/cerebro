from rest_framework import serializers

from apps.pas.models import (
    Plan,
    Accion,
    Evidencia,
)


class PlanSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate(self, attrs):
        fecha_inicio = attrs.get(
            "fecha_inicio",
            getattr(self.instance, "fecha_inicio", None),
        )
        fecha_termino = attrs.get(
            "fecha_termino",
            getattr(self.instance, "fecha_termino", None),
        )

        if fecha_inicio and fecha_termino and fecha_inicio > fecha_termino:
            raise serializers.ValidationError(
                {
                    "fecha_termino": (
                        "La fecha de término no puede ser anterior "
                        "a la fecha de inicio."
                    )
                }
            )

        return attrs

    class Meta:
        model = Plan
        fields = [
            "id",
            "nombre",
            "documento",
            "folio",
            "fecha_llenado",
            "visibilidad",
            "tipo",
            "desc_cnc",
            "correccion",
            "fuente",
            "otra_fuente",
            "fecha_inicio",
            "fecha_termino",
            "proposito",
            "requisito",
            "proceso",
            "desc_pcm",
            "consecuencias",
            "analisis",
            "evidencia_analisis",
            "user",
            "created",
            "modified",
        ]
        read_only_fields = [
            "id",
            "created",
            "modified",
        ]


class AccionSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate(self, attrs):
        plan = attrs.get(
            "plan",
            getattr(self.instance, "plan", None),
        )

        if plan and (not plan.permite_modificaciones):
            raise serializers.ValidationError(
                "El plan se encuentra cerrado o con recurrencia registrada."
            )

        fecha_inicio = attrs.get(
            "fecha_inicio",
            getattr(self.instance, "fecha_inicio", None),
        )
        fecha_fin = attrs.get(
            "fecha_fin",
            getattr(self.instance, "fecha_fin", None),
        )

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError(
                {
                    "fecha_fin": (
                        "La fecha de término no puede ser anterior "
                        "a la fecha de inicio."
                    )
                }
            )

        return attrs

    class Meta:
        model = Accion
        fields = [
            "id",
            "plan",
            "accion",
            "prioridad",
            "responsable",
            "recursos",
            "evidencia",
            "fecha_inicio",
            "fecha_fin",
            "user",
            "created",
            "modified",
        ]
        read_only_fields = [
            "id",
            "created",
            "modified",
        ]


class EvidenciaSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Evidencia
        fields = [
            "id",
            "accion",
            "archivo",
            "descripcion",
            "fecha",
            "user",
            "created",
            "modified",
        ]
        read_only_fields = [
            "id",
            "created",
            "modified",
        ]

    def validate(self, attrs):
        accion = attrs.get(
            "accion",
            getattr(self.instance, "accion", None),
        )

        if accion and not accion.plan.permite_modificaciones:
            raise serializers.ValidationError(
                "El plan se encuentra cerrado o con recurrencia registrada."
            )

        return attrs
