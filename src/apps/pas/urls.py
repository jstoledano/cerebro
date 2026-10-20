from django.urls import path

from .views import (
    PASIndex,
    PASAdd,
    PASDetail,
    PlanSummaryView,
    PlanActivitiesView,
    PlanUpdateView,
    PlanClosureView,
    ActivityCreateView,
    ActivityUpdateView,
    ActivityDeleteView,
    FollowUpCreateView,
    FollowUpListView,
    EvidenceCreateView,
    EvidenceListView,
)

app_name = 'pas'

urlpatterns = [
    path('', PASIndex.as_view(), name='index'),
    path('add/', PASAdd.as_view(), name='add'),
    path('detalle/<int:pk>/', PASDetail.as_view(), name='detalle'),
    path('<int:pk>/summary/', PlanSummaryView.as_view(), name='plan-summary'),
    path('<int:pk>/activities/', PlanActivitiesView.as_view(), name='plan-activities'),
    path('<int:pk>/edit/', PlanUpdateView.as_view(), name='plan-edit'),
    path('<int:pk>/closure/', PlanClosureView.as_view(), name='plan-closure'),
    path('<int:pk>/activities/add/', ActivityCreateView.as_view(), name='activity-add'),
    path('activities/<int:pk>/edit/', ActivityUpdateView.as_view(), name='activity-edit'),
    path('activities/<int:pk>/delete/', ActivityDeleteView.as_view(), name='activity-delete'),
    path('activities/<int:pk>/followups/', FollowUpListView.as_view(), name='followup-list'),
    path('activities/<int:pk>/followups/add/', FollowUpCreateView.as_view(), name='followup-add'),
    path('activities/<int:pk>/evidences/', EvidenceListView.as_view(), name='evidence-list'),
    path('activities/<int:pk>/evidences/add/', EvidenceCreateView.as_view(), name='evidence-add'),
    path(
        "activities/<int:pk>/evidences/",
        EvidenceListView.as_view(),
        name="evidence-list",
    ),
    path(
        "activities/<int:pk>/evidences/add/",
        EvidenceCreateView.as_view(),
        name="evidence-add",
    ),
]
