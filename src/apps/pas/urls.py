from django.urls import path
from .notification_views import agenda_correo, calendario_correo

from .views import (
    PASIndex,
    AgendaView,
    PASAdd,
    PASDetail,
    PlanSummaryView,
    PlanActivitiesView,
    PlanUpdateView,
    PlanClosureView,
    PlanSourceDocumentView,
    ActivityCreateView,
    ActivityDetailView,
    ActivityUpdateView,
    ActivityDeleteView,
    EvidenceDownloadView,
    EvidenceListView,
    ExecutionEvidenceDetailView,
    ExecutionEvidenceCreateView,
    ExecutionEvidenceUpdateView,
    ExecutionEvidenceDeleteView,
    ExecutionCompleteView,
    CalendarEventsView,
)

app_name = "pas"


urlpatterns = [
    path("agenda/correo/", agenda_correo, name="agenda-correo"),
    path("agenda/calendario-correo/", calendario_correo, name="calendario-correo"),
    path("evidences/", EvidenceListView.as_view(), name="evidence-list"),
    path(
        "",
        AgendaView.as_view(),
        name="index",
    ),
    path(
        "agenda/",
        AgendaView.as_view(),
        name="agenda",
    ),
    path(
        "calendar/events/",
        CalendarEventsView.as_view(),
        name="calendar-events",
    ),
    path(
        "plans/",
        PASIndex.as_view(),
        name="plans",
    ),
    path(
        "add/",
        PASAdd.as_view(),
        name="add",
    ),
    path(
        "detalle/<int:pk>/",
        PASDetail.as_view(),
        name="detalle",
    ),
    path(
        "detalle/<int:pk>/documento-fuente/",
        PlanSourceDocumentView.as_view(),
        name="plan-source-document",
    ),
    path(
        "<int:pk>/summary/",
        PlanSummaryView.as_view(),
        name="plan-summary",
    ),
    path(
        "<int:pk>/activities/",
        PlanActivitiesView.as_view(),
        name="plan-activities",
    ),
    path(
        "<int:pk>/edit/",
        PlanUpdateView.as_view(),
        name="plan-edit",
    ),
    path(
        "<int:pk>/closure/",
        PlanClosureView.as_view(),
        name="plan-closure",
    ),
    path(
        "<int:pk>/activities/add/",
        ActivityCreateView.as_view(),
        name="activity-add",
    ),
    path(
        "activities/<int:pk>/detail/",
        ActivityDetailView.as_view(),
        name="activity-detail",
    ),
    path(
        "activities/<int:pk>/edit/",
        ActivityUpdateView.as_view(),
        name="activity-edit",
    ),
    path(
        "activities/<int:pk>/delete/",
        ActivityDeleteView.as_view(),
        name="activity-delete",
    ),
    path(
        "evidences/<int:pk>/download/",
        EvidenceDownloadView.as_view(),
        name="evidence-download",
    ),
    path(
        "evidences/<int:pk>/edit/",
        ExecutionEvidenceUpdateView.as_view(),
        name="evidence-edit",
    ),
    path(
        "evidences/<int:pk>/delete/",
        ExecutionEvidenceDeleteView.as_view(),
        name="evidence-delete",
    ),
    path(
        "executions/<int:pk>/evidence/",
        ExecutionEvidenceDetailView.as_view(),
        name="execution-evidence",
    ),
    path(
        "executions/<int:pk>/evidence/add/",
        ExecutionEvidenceCreateView.as_view(),
        name="execution-evidence-add",
    ),
    path(
        "executions/<int:pk>/complete/",
        ExecutionCompleteView.as_view(),
        name="execution-complete",
    ),
]


