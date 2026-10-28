from rest_framework import serializers

from apps.pas.models import (
    Plan,
    Accion,
    Ejecucion,
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


class AccionSerializer(
    serializers.ModelSerializer
):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    def validate(
        self,
        attrs,
    ):
        plan = attrs.get(
            "plan",
            getattr(
                self.instance,
                "plan",
                None,
            ),
        )

        if (
            plan
            and not plan.permite_modificaciones
        ):
            raise serializers.ValidationError(
                (
                    "El plan se encuentra cerrado "
                    "o con recurrencia registrada."
                )
            )

        fecha_inicio = attrs.get(
            "fecha_inicio",
            getattr(
                self.instance,
                "fecha_inicio",
                None,
            ),
        )

        fecha_fin = attrs.get(
            "fecha_fin",
            getattr(
                self.instance,
                "fecha_fin",
                None,
            ),
        )

        periodicidad = attrs.get(
            "periodicidad",
            getattr(
                self.instance,
                "periodicidad",
                None,
            ),
        )

        ambitos = attrs.get(
            "ambitos",
            getattr(
                self.instance,
                "ambitos",
                [],
            ),
        ) or []

        puesto_responsable = attrs.get(
            "puesto_responsable",
            getattr(
                self.instance,
                "puesto_responsable",
                "",
            ),
        )

        responsable = attrs.get(
            "responsable",
            getattr(
                self.instance,
                "responsable",
                None,
            ),
        )

        if (
            fecha_inicio
            and fecha_fin
            and fecha_inicio > fecha_fin
        ):
            raise serializers.ValidationError(
                {
                    "fecha_fin": (
                        "La fecha de término no puede "
                        "ser anterior a la fecha de inicio."
                    )
                }
            )

        if (
            periodicidad
            == "continua"
        ):
            errors = {}

            if not fecha_inicio:
                errors[
                    "fecha_inicio"
                ] = (
                    "Una actividad continua debe "
                    "tener fecha de inicio."
                )

            if not fecha_fin:
                errors[
                    "fecha_fin"
                ] = (
                    "Una actividad continua debe "
                    "tener fecha de término."
                )

            if errors:
                raise serializers.ValidationError(
                    errors
                )

        if (
            len(ambitos) > 1
            and not puesto_responsable
        ):
            raise serializers.ValidationError(
                {
                    "puesto_responsable": (
                        "Para una actividad con varios "
                        "ámbitos selecciona el responsable "
                        "normativo."
                    )
                }
            )

        if (
            len(ambitos) <= 1
            and not puesto_responsable
            and not responsable
        ):
            raise serializers.ValidationError(
                {
                    "responsable": (
                        "Selecciona un responsable operativo "
                        "o un responsable normativo."
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
            "puesto_responsable",
            "periodicidad",
            "ambitos",
            "evidencia",
            "formato_evidencia",
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


class EvidenciaSerializer(
    serializers.ModelSerializer
):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    ejecucion = serializers.PrimaryKeyRelatedField(
        queryset=Ejecucion.objects.all(),
        required=True,
    )

    class Meta:
        model = Evidencia

        fields = [
            "id",
            "ejecucion",
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
            "accion",
            "created",
            "modified",
        ]

    def validate(
        self,
        attrs,
    ):
        ejecucion = attrs.get(
            "ejecucion",
            getattr(
                self.instance,
                "ejecucion",
                None,
            ),
        )

        if not ejecucion:
            raise serializers.ValidationError(
                {
                    "ejecucion": (
                        "La evidencia debe estar "
                        "asociada a una ejecución."
                    )
                }
            )

        plan = ejecucion.plan

        request = self.context.get(
            "request"
        )

        if (
            request
            and not Plan.objects
            .visible_to(request.user)
            .filter(pk=plan.pk)
            .exists()
        ):
            raise serializers.ValidationError(
                {
                    "ejecucion": (
                        "La ejecución seleccionada "
                        "no está disponible."
                    )
                }
            )

        if not plan.permite_modificaciones:
            raise serializers.ValidationError(
                (
                    "El plan se encuentra cerrado "
                    "o no admite modificaciones."
                )
            )

        return attrs

    def create(
        self,
        validated_data,
    ):
        validated_data[
            "accion"
        ] = None

        return super().create(
            validated_data
        )
