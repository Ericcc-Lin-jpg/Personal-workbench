from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import ChatGroup, ChatGroupMember, ChatGroupMessage, ChatMessage, ChatNotification
from .views import (
    _chat_conversation_for,
    _chat_group_message_data,
    _chat_message_data,
    _chat_notification_data,
)

User = get_user_model()


class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.student = self.scope.get("user")
        self.target = User.objects.filter(
            pk=self.scope["url_route"]["kwargs"]["user_id"],
            student_profile__isnull=False,
        ).first()
        if (
            not self.student
            or not self.student.is_authenticated
            or not hasattr(self.student, "student_profile")
            or not self.target
            or self.target.pk == self.student.pk
        ):
            self.close(code=4401)
            return

        self.conversation = _chat_conversation_for(self.student, self.target)
        if self.conversation is None:
            self.close(code=4403)
            return

        self.group_name = f"chat_{min(self.student.pk, self.target.pk)}_{max(self.student.pk, self.target.pk)}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        self.send_json({"type": "ready"})

    def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name,
            )

    def receive_json(self, content, **kwargs):
        # Messages continue to use the authenticated HTTP endpoint so uploads,
        # validation and existing client retry behavior remain in one place.
        if content.get("type") == "ping":
            self.send_json({"type": "pong"})

    def chat_message(self, event):
        message = ChatMessage.objects.select_related(
            "sender",
            "shared_deadline__class_group__course",
            "shared_personal_task",
        ).filter(
            pk=event["messageId"],
            conversation=self.conversation,
        ).first()
        if message:
            notification = ChatNotification.objects.filter(
                student=self.student,
                message=message,
            ).select_related("message__sender").first()
            self.send_json({
                "type": "message",
                "message": _chat_message_data(message, self.student),
                "notification": (
                    _chat_notification_data(notification)
                    if notification
                    else None
                ),
            })


class ChatGroupConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.student = self.scope.get("user")
        self.group = ChatGroup.objects.filter(
            pk=self.scope["url_route"]["kwargs"]["group_id"],
        ).first()
        if (
            not self.student
            or not self.student.is_authenticated
            or not hasattr(self.student, "student_profile")
            or not self.group
            or not ChatGroupMember.objects.filter(
                group=self.group,
                student=self.student,
            ).exists()
        ):
            self.close(code=4403)
            return
        self.group_name = f"chat_group_{self.group.id}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        self.send_json({"type": "ready"})

    def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name,
            )

    def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            self.send_json({"type": "pong"})

    def chat_group_message(self, event):
        message = ChatGroupMessage.objects.select_related(
            "sender",
            "shared_deadline__class_group__course",
            "shared_personal_task",
        ).filter(
            pk=event["messageId"],
            group=self.group,
        ).first()
        if (
            message
            and ChatGroupMember.objects.filter(
                group=self.group,
                student=self.student,
            ).exists()
        ):
            self.send_json({
                "type": "message",
                "message": _chat_group_message_data(message, self.student),
            })
