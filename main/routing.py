from django.urls import re_path

from .consumers import ChatConsumer, ChatGroupConsumer


websocket_urlpatterns = [
    re_path(r"^ws/chats/(?P<user_id>\d+)/$", ChatConsumer.as_asgi()),
    re_path(r"^ws/chat-groups/(?P<group_id>\d+)/$", ChatGroupConsumer.as_asgi()),
]
