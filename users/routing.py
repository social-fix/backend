# chat/routing.py
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^wss/updateService/(?P<service_id>[0-9]+)/$', consumers.ServiceConsummer),
]