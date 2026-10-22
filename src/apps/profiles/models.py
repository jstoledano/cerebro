# coding: utf-8
#         app: mx.ine.tlx.sgc.cerebro.profiles
#      módulo: profiles.models
# descripción: Add profile info to User model
#       autor: Javier Sanchez Toledano
#       fecha: lunes, mayo 21 de 2018

import uuid
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


TLAXCALA = 29
ENTIDADES = (
    (TLAXCALA, 'Tlaxcala'),
)

JL = 0
JD01 = 1
JD02 = 2
JD03 = 3
SITIO = (
    (JL, 'Junta Local'),
    (JD01, '01 Junta Distrital'),
    (JD02, '02 Junta Distrital'),
    (JD03, 'O3 Junta Distrital')
)

VEL = 'VEL'
VSL = 'VSL'
VRL = 'VRL'
VOL = 'VOL'
VCL = 'VCL'
VED = 'VED'
VSD = 'VSD'
VRD = 'VRD'
VOD = 'VOD'
VCD = 'VCD'
JMM = 'JMM'
JOSA = 'JOSA'
JOSAD = 'JOSAD'
JOCE = 'JOCE'
RA = 'RA'

PUESTOS = (
    (VEL, 'Vocal Ejecutivo de Junta Local'),
    (VSL, 'Vocal Secretario de Junta Local'),
    (VRL, 'Vocal del RFE de Junta Local'),
    (VCL, 'Vocal de Capacitación de Junta Local'),
    (VOL, 'Vocal de Organización de Junta Local'),
    (VED, 'Vocal Ejecutivo de Junta Distrital'),
    (VSD, 'Vocal Secretario de Junta Distrital'),
    (VRD, 'Vocal del RFE de Junta Distrital'),
    (VCD, 'Vocal de Capacitación de Junta Distrital'),
    (VOD, 'Vocal de Organización de Junta Distrital'),
    (JOSA, 'JOSA'),
    (JOSAD, 'JOSAD'),
    (JMM, 'Jefe de Monitoreo a Módulos'),
    (JOCE, 'Jefe de Cartografía'),
    (RA, 'Rama Administrativa')
)

class UnidadOrganizacional(models.Model):
    clave = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Clave",
        help_text=(
            "Clave jerárquica de la unidad. "
            "Ejemplos: 00, 50, 5099."
        ),
    )

    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre",
    )

    superior = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subordinadas",
        blank=True,
        null=True,
        verbose_name="Unidad superior",
    )

    site = models.PositiveSmallIntegerField(
        choices=SITIO,
        blank=True,
        null=True,
        verbose_name="Sede",
    )

    activa = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    class Meta:
        ordering = [
            "clave",
        ]
        verbose_name = "Unidad organizacional"
        verbose_name_plural = (
            "Unidades organizacionales"
        )

    def __str__(self):
        return (
            f"{self.clave} - "
            f"{self.nombre}"
        )

    def obtener_descendientes(
        self,
        incluir_self=False,
    ):
        unidades = []

        if incluir_self:
            unidades.append(
                self
            )

        pendientes = list(
            self.subordinadas
            .filter(
                activa=True
            )
            .order_by(
                "clave"
            )
        )

        visitadas = {
            self.pk,
        }

        while pendientes:
            unidad = pendientes.pop(0)

            if unidad.pk in visitadas:
                continue

            visitadas.add(
                unidad.pk
            )

            unidades.append(
                unidad
            )

            pendientes.extend(
                unidad.subordinadas
                .filter(
                    activa=True
                )
                .order_by(
                    "clave"
                )
            )

        return unidades

    def depende_de(
        self,
        unidad,
    ):
        actual = self.superior

        visitadas = set()

        while actual is not None:
            if actual.pk in visitadas:
                return False

            visitadas.add(
                actual.pk
            )

            if actual.pk == unidad.pk:
                return True

            actual = actual.superior

        return False

    def obtener_usuarios(
        self,
        incluir_self=True,
        activos=True,
    ):
        unidades = (
            self.obtener_descendientes(
                incluir_self=incluir_self
            )
        )

        queryset = (
            User.objects
            .filter(
                profile__unidad_organizacional__in=(
                    unidades
                )
            )
            .select_related(
                "profile",
                "profile__unidad_organizacional",
            )
            .order_by(
                "profile__unidad_organizacional__clave",
                "profile__order",
                "first_name",
                "last_name",
                "username",
            )
        )

        if activos:
            queryset = queryset.filter(
                is_active=True
            )

        return queryset


class Profile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )

    state = models.PositiveSmallIntegerField(
        choices=ENTIDADES,
        default=TLAXCALA,
    )

    site = models.PositiveSmallIntegerField(
        choices=SITIO,
        default=0,
    )

    position = models.CharField(
        choices=PUESTOS,
        max_length=5,
        default=RA,
    )

    unidad_organizacional = models.ForeignKey(
        UnidadOrganizacional,
        on_delete=models.SET_NULL,
        related_name="miembros",
        blank=True,
        null=True,
        verbose_name="Unidad organizacional",
        help_text=(
            "Ubicación del usuario dentro de la "
            "estructura organizacional."
        ),
    )

    order = models.PositiveSmallIntegerField(
        default=99,
        blank=True,
        null=True,
    )

    recibe_notificaciones = models.BooleanField(
        default=False,
    )

    def __str__(self):
        nombre = (
            self.user.get_full_name()
            or self.user.username
        )

        if self.unidad_organizacional:
            return (
                f"{nombre} - "
                f"{self.unidad_organizacional}"
            )

        return nombre


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
