from rest_framework import serializers
from apps.pusinex.models import (
    Entidad,
    Distrito,
    Municipio,
    Seccion,
    Pusinex,
)


class EntidadSerializer(serializers.ModelSerializer):

    class Meta:
        model = Entidad
        fields = '__all__'
        depth = 3


class DistritoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Distrito
        fields = '__all__'
        depth = 3


class MunicipioSerializer(serializers.ModelSerializer):

    class Meta:
        model = Municipio
        fields = '__all__'
        depth = 3


class SeccionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Seccion
        fields = '__all__'
        depth = 2

    def get_rev(self, obj):
        revision = Seccion.objects.filter(pusinex=obj).last()
        serializer = SeccionSerializer(revision, many=False)
        return serializer.data


class PusinexSerializer(serializers.ModelSerializer):
    rev = serializers.SerializerMethodField()

    class Meta:
        model = Pusinex
        fields = '__all__'
        depth = 3
