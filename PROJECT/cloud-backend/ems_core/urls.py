from django.contrib import admin
from django.urls import path, include
from apps.telemetry.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/sites/', include('apps.sites.urls')),
    path('api/telemetry/', include('apps.telemetry.urls')),
    path('api/control/', include('apps.fleet_control.urls')),
    
    # 監控與控制前端儀表板 (Web Dashboard)
    path('', DashboardView.as_view(), name='dashboard'),
]
