import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer


class ServiceConsummer(JsonWebsocketConsumer):
    def connect(self):
        self.service_id = self.scope['url_route']['kwargs']['service_id']
        self.group_name = 'service_{}'.format(self.service_id)
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive_json(self, content):
        pass
        # async_to_sync(self.channel_layer.group_send)(
        #     self.group_name,
        #     {
        #         'type': 'subscription_message',
        #         'message': content 
        #     }
        # )

    def subscription_message(self, event):
        message=event['message']

        # Send message to WebSocket
        self.send_json(message)
