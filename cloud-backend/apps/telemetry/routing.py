from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/telemetry/(?P<site_id>[^/]+)/$", consumers.TelemetryConsumer.as_asgi()),
]
