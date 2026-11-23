from django.urls import path
from apps.agenda.views import (
    AgendaListView, AgendaPDFView, CalendarEventsView, DashboardView,
    ICalendarView, PendingTasksView, TaskDetailView, TaskStateView,
)

app_name = "agenda"
urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("calendario/eventos/", CalendarEventsView.as_view(), name="calendar-events"),
    path("lista/", AgendaListView.as_view(), name="list"),
    path("pendientes/", PendingTasksView.as_view(), name="pending"),
    path("tarea/detalle/", TaskDetailView.as_view(), name="task-detail"),
    path("tarea/estado/", TaskStateView.as_view(), name="task-state"),
    path("pdf/", AgendaPDFView.as_view(), name="pdf"),
    path("ics/", ICalendarView.as_view(), name="ics"),
]
