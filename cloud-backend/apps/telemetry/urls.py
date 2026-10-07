from django.urls import path
from .views import TelemetryLatestView, TelemetryHistoryView, TelemetrySummaryView

urlpatterns = [
    path('latest/<str:site_id>/', TelemetryLatestView.as_view(), name='telemetry-latest'),
    path('history/<str:site_id>/', TelemetryHistoryView.as_view(), name='telemetry-history'),
    path('summary/<str:site_id>/', TelemetrySummaryView.as_view(), name='telemetry-summary'),
]
