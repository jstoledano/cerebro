from django.urls import path

from apps.agenda.views import (
    AgendaListView, AgendaPDFView, CalendarEventsView, DashboardView, DoingView,
    ICalendarView,
)

app_name = "agenda"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("doing/", DoingView.as_view(), name="doing"),
    path("calendario/eventos/", CalendarEventsView.as_view(), name="calendar-events"),
    path("lista/", AgendaListView.as_view(), name="list"),
    path("pdf/", AgendaPDFView.as_view(), name="pdf"),
    path("ics/", ICalendarView.as_view(), name="ics"),
]
