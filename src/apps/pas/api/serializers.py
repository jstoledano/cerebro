from rest_framework import serializers
from apps.pas.forms import EvidenciaForm
from apps.pas.permissions import es_normativo_ejecucion

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


class EvidenciaSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    historial = serializers.SerializerMethodField()

    def get_historial(self, obj):
        if getattr(self.context.get("view"), "action", None) == "list":
            return []
        return list(obj.ejecucion.eventos_evidencia.filter(evidencia_id=obj.pk).values(
            "fecha", "identidad", "rol", "operacion", "anterior", "posterior",
        ))

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
            "modificada_por",
            "historial",
        ]
        read_only_fields = [
            "id",
            "accion",
            "created",
            "modified",
            "modificada_por",
            "historial",
        ]

    def validate(self, attrs):
        ejecucion = attrs.get(
            "ejecucion",
            getattr(self.instance, "ejecucion", None),
        )

        if ejecucion is None:
            raise serializers.ValidationError(
                {
                    "ejecucion": (
                        "La evidencia debe estar asociada "
                        "a una ejecución."
                    )
                }
            )

        if (
            self.instance is not None
            and ejecucion.pk != self.instance.ejecucion_id
        ):
            raise serializers.ValidationError(
                {
                    "ejecucion": (
                        "La ejecución de una evidencia existente "
                        "debe conservarse."
                    )
                }
            )

        request = self.context.get("request")

        if request is None or not (
            Plan.objects.visible_to(request.user)
            .filter(pk=ejecucion.plan.pk)
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

        if not ejecucion.plan.permite_modificaciones:
            raise serializers.ValidationError(
                "El plan se encuentra cerrado "
                "o no admite modificaciones."
            )

        if ejecucion.completada and not (
            self.instance is not None
            and es_normativo_ejecucion(request.user, ejecucion)
        ):
            raise serializers.ValidationError(
                "La ejecución está terminada. Debes reabrirla "
                "antes de modificar sus evidencias."
            )

        if "archivo" in attrs and not attrs["archivo"]:
            raise serializers.ValidationError(
                {
                    "archivo": (
                        "Debes conservar el archivo actual "
                        "o proporcionar uno nuevo."
                    )
                }
            )

        if self.instance is not None:
            fecha_inicial = self.instance.fecha
            descripcion_inicial = self.instance.descripcion
        else:
            fecha_inicial = (
                Evidencia._meta.get_field("fecha").get_default()
            )
            descripcion_inicial = ""

        archivos = {}

        if "archivo" in attrs:
            archivos["archivo"] = attrs["archivo"]

        form = EvidenciaForm(
            data={
                "fecha": attrs.get("fecha", fecha_inicial),
                "descripcion": attrs.get(
                    "descripcion",
                    descripcion_inicial,
                ),
            },
            files=archivos,
            instance=self.instance,
            execution=ejecucion,
        )

        if not form.is_valid():
            raise serializers.ValidationError(
                {
                    (
                        "non_field_errors"
                        if campo == "__all__"
                        else campo
                    ): list(errores)
                    for campo, errores in form.errors.items()
                }
            )

        return attrs

    def create(self, validated_data):
        validated_data["accion"] = None
        return super().create(validated_data)

