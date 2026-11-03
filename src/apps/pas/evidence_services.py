"""Mutaciones auditadas compartidas por formularios y API."""
from django.db import transaction

from .models import Evidencia, EventoEvidencia
from .permissions import es_normativo_ejecucion


def instantanea(evidence):
    return {
        "ejecucion": evidence.ejecucion_id,
        "descripcion": evidence.descripcion,
        "fecha": str(evidence.fecha),
        "archivo": evidence.archivo.name or "",
        "autor": evidence.user_id,
        "modificada_por": evidence.modificada_por_id,
    }


def registrar_evento(evidence, actor, operacion, anterior, posterior):
    EventoEvidencia.objects.create(
        ejecucion=evidence.ejecucion,
        evidencia_id=evidence.pk,
        actor=actor,
        identidad=actor.get_username(),
        rol=("normativo" if es_normativo_ejecucion(actor, evidence.ejecucion)
             else "operativo"),
        operacion=operacion,
        anterior=anterior,
        posterior=posterior,
    )


def retirar_archivo(storage, name):
    if name:
        # Una transacción revertida conserva el archivo; referencias compartidas
        # heredadas tampoco deben perderlo.
        def eliminar():
            if not Evidencia.objects.filter(archivo=name).exists():
                storage.delete(name)
        transaction.on_commit(eliminar)


@transaction.atomic
def guardar_evidencia(evidence, actor):
    anterior = {}
    if evidence.pk:
        original = Evidencia.objects.select_for_update().get(pk=evidence.pk)
        anterior = instantanea(original)
        evidence.user_id = original.user_id
    else:
        evidence.user = actor
    evidence.modificada_por = actor
    evidence.save()
    registrar_evento(
        evidence, actor, "editar" if anterior else "crear",
        anterior, instantanea(evidence),
    )
    if anterior and anterior["archivo"] != (evidence.archivo.name or ""):
        retirar_archivo(evidence.archivo.storage, anterior["archivo"])
    return evidence


@transaction.atomic
def eliminar_evidencia(evidence, actor):
    evidence = Evidencia.objects.select_for_update().get(pk=evidence.pk)
    registrar_evento(evidence, actor, "eliminar", instantanea(evidence), {})
    storage, name = evidence.archivo.storage, evidence.archivo.name
    evidence.delete()
    retirar_archivo(storage, name)
