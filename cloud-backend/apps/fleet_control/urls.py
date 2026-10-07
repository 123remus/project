from django.urls import path
from .views import SetBackupReserveView, SetOperationModeView, ControlLogListView

urlpatterns = [
    path('backup-reserve/', SetBackupReserveView.as_view(), name='set-backup-reserve'),
    path('operation-mode/', SetOperationModeView.as_view(), name='set-operation-mode'),
    path('logs/', ControlLogListView.as_view(), name='control-logs'),
]
