import json
import logging
import os
import re
import zipfile
from datetime import datetime, time, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings as django_settings
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db import connection
from django.db.utils import OperationalError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.core import signing
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from PIL import Image, UnidentifiedImageError

from .models import (
    AnnualPlanSubtask,
    AnnualPlanTask,
    ChatConversation,
    ChatBlock,
    ChatGroup,
    ChatGroupInvitation,
    ChatGroupMember,
    ChatGroupMessage,
    ChatMessage,
    ChatNotification,
    ChatMute,
    ChatReport,
    ClassGroup,
    ClassSubscription,
    Checkin,
    Course,
    Deadline,
    Notification,
    PersonalTask,
    School,
    StudentFriendship,
    StudentDeadlineState,
    StudentNotificationSettings,
    StudentProfile,
    TaskReminder,
    TeacherApplication,
    Term,
)
from .wechat import WeChatDeliveryError, WeChatSender

User = get_user_model()
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
CHAT_IMAGE_MAX_BYTES = 10 * 1024 * 1024
CHAT_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
CHAT_ATTACHMENT_MAX_BYTES = 50 * 1024 * 1024
CHAT_ATTACHMENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".zip": {"application/zip", "application/x-zip-compressed", "application/octet-stream"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".webm": {"audio/webm", "video/webm"},
    ".ogg": {"audio/ogg", "application/ogg"},
}
logger = logging.getLogger(__name__)


def _uploaded_file_head(upload, size=32):
    upload.seek(0)
    data = upload.read(size)
    upload.seek(0)
    return data


def _validate_chat_image(image):
    extension = os.path.splitext(image.name or "")[1].lower()
    expected_type = CHAT_IMAGE_TYPES.get(extension)
    if not expected_type or image.content_type != expected_type:
        raise ValidationError("仅支持 JPG、PNG、GIF 和 WEBP 图片。")
    if image.size > CHAT_IMAGE_MAX_BYTES:
        raise ValidationError("图片不能超过 10MB。")
    expected_format = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".gif": "GIF",
        ".webp": "WEBP",
    }[extension]
    try:
        image.seek(0)
        with Image.open(image) as decoded:
            if decoded.format != expected_format:
                raise ValidationError("图片内容与文件类型不匹配。")
            if decoded.width * decoded.height > 40_000_000:
                raise ValidationError("图片分辨率过大。")
            decoded.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValidationError("图片文件已损坏或不是有效图片。") from exc
    finally:
        image.seek(0)


def _validate_zip_attachment(upload):
    try:
        upload.seek(0)
        with zipfile.ZipFile(upload) as archive:
            files = archive.infolist()
            total_size = sum(item.file_size for item in files)
            compressed_size = sum(item.compress_size for item in files)
            if len(files) > 1_000 or total_size > 250 * 1024 * 1024:
                raise ValidationError("压缩文件内容过大。")
            if total_size > 0 and compressed_size > 0 and total_size / compressed_size > 100:
                raise ValidationError("压缩文件压缩率异常。")
    except zipfile.BadZipFile as exc:
        raise ValidationError("压缩文件已损坏或格式无效。") from exc
    finally:
        upload.seek(0)


def _validate_chat_attachment(attachment):
    extension = os.path.splitext(attachment.name or "")[1].lower()
    allowed_types = CHAT_ATTACHMENT_TYPES.get(extension)
    if not allowed_types or attachment.content_type not in allowed_types:
        raise ValidationError("暂不支持该文件类型。")
    if attachment.size > CHAT_ATTACHMENT_MAX_BYTES:
        raise ValidationError("文件不能超过 50MB。")

    head = _uploaded_file_head(attachment)
    signatures = {
        ".pdf": lambda value: value.startswith(b"%PDF-"),
        ".zip": lambda value: value.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")),
        ".doc": lambda value: value.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ".xls": lambda value: value.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ".ppt": lambda value: value.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ".docx": lambda value: value.startswith(b"PK"),
        ".xlsx": lambda value: value.startswith(b"PK"),
        ".pptx": lambda value: value.startswith(b"PK"),
        ".mp3": lambda value: value.startswith(b"ID3") or value.startswith(b"\xff"),
        ".wav": lambda value: value.startswith(b"RIFF") and value[8:12] == b"WAVE",
        ".m4a": lambda value: value[4:8] == b"ftyp",
        ".webm": lambda value: value.startswith(b"\x1a\x45\xdf\xa3"),
        ".ogg": lambda value: value.startswith(b"OggS"),
    }
    validator = signatures.get(extension)
    if validator and not validator(head):
        raise ValidationError("文件内容与扩展名不匹配。")
    if extension == ".txt" and b"\x00" in _uploaded_file_head(attachment, 8 * 1024):
        raise ValidationError("文本文件包含无效二进制内容。")
    if extension in {".zip", ".docx", ".xlsx", ".pptx"}:
        _validate_zip_attachment(attachment)


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _account_password_error(password, user=None):
    try:
        validate_password(password, user)
    except ValidationError as exc:
        return " ".join(exc.messages)
    return ""


@require_http_methods(["GET"])
def healthz(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({
        "status": "ok",
        "database": "ok",
        "timezone": django_settings.TIME_ZONE,
    })


def _local_fields(value):
    local = timezone.localtime(value, SHANGHAI_TZ)
    return {
        "date": local.strftime("%Y-%m-%d"),
        "time": local.strftime("%H:%M"),
        "iso": local.isoformat(),
    }


def _parse_reminder(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def _parse_schedule_datetime(value):
    raw_value = str(value or "").strip().replace("Z", "+00:00")
    date_value, separator, time_value = raw_value.partition("T")
    if separator and re.fullmatch(r"24:00(?::00)?(?:[+-]\d{2}:\d{2})?", time_value):
        parsed_date = _parse_date(date_value)
        if parsed_date is not None:
            return timezone.make_aware(
                datetime.combine(parsed_date + timedelta(days=1), time.min),
                SHANGHAI_TZ,
            )
    return _parse_reminder(value)


def _schedule_payload(payload, current_start=None, current_end=None):
    start = current_start
    end = current_end
    if "plannedStart" in payload:
        raw_start = payload.get("plannedStart")
        start = _parse_schedule_datetime(raw_start) if raw_start else None
        if raw_start and start is None:
            raise ValidationError("计划开始时间格式不正确。")
    if "plannedEnd" in payload:
        raw_end = payload.get("plannedEnd")
        end = _parse_schedule_datetime(raw_end) if raw_end else None
        if raw_end and end is None:
            raise ValidationError("计划结束时间格式不正确。")
    if end and not start:
        raise ValidationError("时间段任务需要先设置开始时间。")
    if start and end:
        local_start = timezone.localtime(start, SHANGHAI_TZ)
        local_end = timezone.localtime(end, SHANGHAI_TZ)
        ends_at_midnight = (
            local_end.date() == local_start.date() + timedelta(days=1)
            and local_end.time() == time.min
        )
        if local_start.date() != local_end.date() and not ends_at_midnight:
            raise ValidationError("第一版暂不支持跨天安排。")
        if local_start.minute % 15 or local_end.minute % 15:
            raise ValidationError("计划时间必须按 15 分钟设置。")
        if end <= start:
            raise ValidationError("结束时间必须晚于开始时间。")
        if end - start < timedelta(minutes=15):
            raise ValidationError("时间段最短为 15 分钟。")
    elif start:
        local_start = timezone.localtime(start, SHANGHAI_TZ)
        if local_start.minute % 15:
            raise ValidationError("计划时间必须按 15 分钟设置。")
    return start, end


def _schedule_data(start, end):
    planned_end = _local_fields(end) if end else None
    if start and end:
        local_start = timezone.localtime(start, SHANGHAI_TZ)
        local_end = timezone.localtime(end, SHANGHAI_TZ)
        if (
            local_end.date() == local_start.date() + timedelta(days=1)
            and local_end.time() == time.min
        ):
            date_value = local_start.strftime("%Y-%m-%d")
            planned_end = {
                "date": date_value,
                "time": "24:00",
                "iso": f"{date_value}T24:00:00+08:00",
            }
    return {
        "scheduleType": "duration" if start and end else "point" if start else "unscheduled",
        "plannedStart": _local_fields(start) if start else None,
        "plannedEnd": planned_end,
    }


def _parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _replace_reminders(student, *, deadline=None, personal_task=None, reminders=None):
    if deadline is None and personal_task is None:
        return
    filters = {"student": student}
    if deadline is not None:
        filters["deadline"] = deadline
    else:
        filters["personal_task"] = personal_task
    TaskReminder.objects.filter(**filters).delete()
    for value in reminders or []:
        remind_at = _parse_reminder(value)
        if remind_at:
            TaskReminder.objects.create(
                student=student,
                deadline=deadline,
                personal_task=personal_task,
                remind_at=remind_at,
            )


def _state_for(student, deadline):
    state, _ = StudentDeadlineState.objects.get_or_create(
        student=student,
        deadline=deadline,
    )
    return state


def _task_level(due_at, priority, status):
    if status == "done":
        return "completed"
    now = timezone.now()
    if due_at < now:
        return "expired"
    if priority == "high" or due_at <= now + timedelta(hours=24):
        return "urgent"
    return "normal"


def _local_date_bounds(target_date):
    start = timezone.make_aware(datetime.combine(target_date, time.min), SHANGHAI_TZ)
    return start, start + timedelta(days=1)


def _student_deadlines_for_range(student, start, end):
    subscribed_classes = ClassSubscription.objects.filter(
        student=student,
    ).values_list("class_group_id", flat=True)
    return Deadline.objects.filter(
        class_group_id__in=subscribed_classes,
        is_active=True,
        due_at__gte=start,
        due_at__lt=end,
    ).select_related("class_group__course", "created_by").distinct()


def _student_tasks_for_date(student, target_date, *, official_only=False):
    start, end = _local_date_bounds(target_date)
    deadlines = list(_student_deadlines_for_range(student, start, end))
    tasks = [_deadline_data(deadline, student) for deadline in deadlines]
    if not official_only:
        tasks.extend(
            _personal_task_data(task)
            for task in student.personal_tasks.filter(
                due_at__gte=start,
                due_at__lt=end,
            ).prefetch_related("reminders")
        )
    tasks.sort(key=lambda item: (item["time"], item["id"]))
    return tasks


def _student_tasks_for_period(student, start_date, end_date, *, official_only=False):
    start, _ = _local_date_bounds(start_date)
    _, end = _local_date_bounds(end_date + timedelta(days=1))
    deadlines = list(_student_deadlines_for_range(student, start, end))
    tasks = [_deadline_data(deadline, student) for deadline in deadlines]
    if not official_only:
        tasks.extend(
            _personal_task_data(task)
            for task in student.personal_tasks.filter(
                due_at__gte=start,
                due_at__lt=end,
            ).prefetch_related("reminders")
        )
    tasks.sort(key=lambda item: (item["date"], item["time"], item["id"]))
    return tasks


def _sync_checkin(student, target_date=None):
    today = timezone.localtime(timezone.now(), SHANGHAI_TZ).date()
    target_date = target_date or today
    tasks = _student_tasks_for_date(student, target_date)
    total = len(tasks)
    completed = sum(task["done"] for task in tasks)
    checkin = Checkin.objects.filter(student=student, date=target_date).first()

    if total == 0 or completed != total:
        if checkin:
            checkin.delete()
        return None
    if target_date != today and not checkin:
        return None

    checkin, created = Checkin.objects.get_or_create(
        student=student,
        date=target_date,
        defaults={
            "completed_at": timezone.now(),
            "task_total": total,
            "completed_total": completed,
        },
    )
    if not created and (
        checkin.task_total != total
        or checkin.completed_total != completed
    ):
        checkin.task_total = total
        checkin.completed_total = completed
        checkin.save(update_fields=["task_total", "completed_total"])
    return checkin


def _checkin_streak(student, target_date):
    if not Checkin.objects.filter(student=student, date=target_date).exists():
        return 0
    streak = 0
    cursor = target_date
    while Checkin.objects.filter(student=student, date=cursor).exists():
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _dashboard_data(student):
    today = timezone.localtime(timezone.now(), SHANGHAI_TZ).date()
    checkin = _sync_checkin(student, today)
    recent_start = today - timedelta(days=6)
    recent_checkins = {
        item.date: item
        for item in Checkin.objects.filter(
            student=student,
            date__gte=recent_start,
            date__lte=today,
        )
    }
    today_tasks = _student_tasks_for_date(student, today)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_tasks = _student_tasks_for_period(
        student,
        week_start,
        week_end,
        official_only=True,
    )
    completed = sum(task["done"] for task in today_tasks)
    total = len(today_tasks)
    local_hour = timezone.localtime(timezone.now(), SHANGHAI_TZ).hour
    greeting = "早上好" if local_hour < 12 else "下午好" if local_hour < 18 else "晚上好"
    profile = student.student_profile

    return {
        "identity": {
            "name": student.get_full_name() or student.username,
            "email": student.email,
            "school": profile.school.name,
            "term": profile.term.name,
            "grade": profile.grade,
            "curriculum": profile.curriculum,
            "motto": profile.motto,
            "avatarKey": "default-student",
            "greeting": greeting,
        },
        "today": {
            "date": today.isoformat(),
            "total": total,
            "completed": completed,
            "percent": round(completed / total * 100) if total else 0,
            "urgent": sum(
                task["level"] == "urgent" and not task["done"]
                for task in today_tasks
            ),
            "tasks": today_tasks,
        },
        "week": {
            "start": week_start.isoformat(),
            "end": week_end.isoformat(),
            "total": len(week_tasks),
            "tasks": week_tasks,
        },
        "checkin": {
            "checkedIn": checkin is not None,
            "streak": _checkin_streak(student, today),
            "completedAt": checkin.completed_at.isoformat() if checkin else None,
            "recent": [
                {
                    "date": (recent_start + timedelta(days=offset)).isoformat(),
                    "checkedIn": (recent_start + timedelta(days=offset)) in recent_checkins,
                    "percent": (
                        round(
                            recent_checkins[recent_start + timedelta(days=offset)].completed_total
                            / recent_checkins[recent_start + timedelta(days=offset)].task_total
                            * 100,
                        )
                        if recent_start + timedelta(days=offset) in recent_checkins
                        and recent_checkins[recent_start + timedelta(days=offset)].task_total
                        else 0
                    ),
                }
                for offset in range(7)
            ],
        },
    }


def _annual_plan_task_data(task):
    today = timezone.localtime(timezone.now(), SHANGHAI_TZ).date()
    subtasks = list(task.subtasks.all())
    completed_subtasks = sum(item.completed for item in subtasks)
    if task.task_type == "node":
        status = "completed" if task.node_date < today else "upcoming"
    elif task.end_date < today:
        status = "completed"
    elif task.start_date > today:
        status = "upcoming"
    else:
        status = "in_progress"
    return {
        "id": task.id,
        "category": task.category,
        "type": task.task_type,
        "title": task.title,
        "startDate": task.start_date.isoformat() if task.start_date else None,
        "endDate": task.end_date.isoformat() if task.end_date else None,
        "nodeDate": task.node_date.isoformat() if task.node_date else None,
        "description": task.description,
        "status": status,
        "subtaskTotal": len(subtasks),
        "subtaskCompleted": completed_subtasks,
        "subtasks": [
            {
                "id": subtask.id,
                "title": subtask.title,
                "dueDate": subtask.due_date.isoformat() if subtask.due_date else None,
                "completed": subtask.completed,
            }
            for subtask in subtasks
        ],
        "createdAt": task.created_at.isoformat(),
        "updatedAt": task.updated_at.isoformat(),
    }


def _annual_plan_task_from_payload(student, payload, task=None):
    task = task or AnnualPlanTask(student=student)
    if payload.get("category") in {
        "academic",
        "test",
        "competition",
        "application",
        "personal",
    }:
        task.category = payload["category"]
    if payload.get("type") in {"period", "node"}:
        task.task_type = payload["type"]
    if "title" in payload:
        task.title = str(payload["title"]).strip()[:200]
    if "description" in payload:
        task.description = str(payload["description"]).strip()[:4000]
    if "startDate" in payload:
        task.start_date = _parse_date(payload["startDate"])
    if "endDate" in payload:
        task.end_date = _parse_date(payload["endDate"])
    if "nodeDate" in payload:
        task.node_date = _parse_date(payload["nodeDate"])
    task.full_clean()
    return task


def _deadline_data(deadline, student):
    state = _state_for(student, deadline)
    due = _local_fields(deadline.due_at)
    reminders = [
        _local_fields(reminder.remind_at)
        for reminder in deadline.reminders.filter(student=student)
    ]
    return {
        "id": f"deadline-{deadline.id}",
        "deadlineId": deadline.id,
        **due,
        "title": deadline.title,
        "source": {"course": "📚", "admissions": "🎓", "competition": "🏆"}.get(deadline.source_type, "📌"),
        "sourceName": (
            f"{deadline.class_group.course.name} · {deadline.class_group.name}"
            if deadline.class_group else "官方安排"
        ),
        "publisher": (
            deadline.class_group.teacher_name
            if deadline.class_group
            else deadline.created_by.get_full_name() or deadline.created_by.username
        ),
        "kind": deadline.kind,
        "description": deadline.description,
        "level": _task_level(deadline.due_at, state.priority, state.status),
        "status": state.status,
        **_schedule_data(state.planned_start_at, state.planned_end_at),
        "done": state.status == "done",
        "priority": state.priority,
        "note": state.note,
        "reminders": reminders,
        "officialUpdatedAt": deadline.updated_at.isoformat(),
    }


def _personal_task_data(task):
    due = _local_fields(task.due_at)
    reminders = [
        _local_fields(reminder.remind_at)
        for reminder in task.reminders.all()
    ]
    return {
        "id": f"personal-{task.id}",
        "personalTaskId": task.id,
        **due,
        "title": task.title,
        "source": "✏️",
        "sourceName": "我的待办",
        "publisher": "我",
        "kind": "personal",
        "description": task.note or "个人创建的待办事项。",
        "level": _task_level(task.due_at, task.priority, task.status),
        "status": task.status,
        **_schedule_data(task.planned_start_at, task.planned_end_at),
        "done": task.status == "done",
        "priority": task.priority,
        "note": task.note,
        "reminders": reminders,
    }


def _personal_task_due_at(payload):
    due_at_value = payload.get("dueAt")
    if due_at_value:
        return _parse_reminder(due_at_value)
    due_date = str(payload.get("due", "")).strip()
    due_time = str(payload.get("dueTime", "23:59")).strip() or "23:59"
    if not due_date:
        return None
    return _parse_reminder(f"{due_date}T{due_time}")


def _notification_data(notification):
    task_id = (
        f"deadline-{notification.deadline_id}"
        if notification.deadline_id
        else f"personal-{notification.personal_task_id}"
    )
    return {
        "id": notification.id,
        "taskId": task_id,
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "scheduledAt": _local_fields(notification.scheduled_at),
        "read": notification.read_at is not None,
        "wechatSent": notification.wechat_sent_at is not None,
    }


def _chat_notification_data(notification):
    message = notification.message
    sender = message.sender
    local = timezone.localtime(notification.created_at, SHANGHAI_TZ)
    preview = (
        message.content
        if message.content
        else "图片"
        if message.image
        else "任务卡片"
        if message.shared_deadline_id or message.shared_personal_task_id
        else "文件"
        if message.attachment
        else "新消息"
    )
    return {
        "id": f"chat-{notification.id}",
        "kind": "chat",
        "chatId": sender.id,
        "chatName": sender.get_full_name() or sender.username,
        "type": "chat_message",
        "title": f"{sender.get_full_name() or sender.username} 发来新消息",
        "message": preview[:300],
        "scheduledAt": {
            "date": local.strftime("%Y-%m-%d"),
            "time": local.strftime("%H:%M"),
        },
        "read": notification.read_at is not None,
        "wechatSent": False,
    }


def _create_notification(
    student,
    *,
    deadline=None,
    personal_task=None,
    reminder=None,
    notification_type,
    scheduled_at,
    title,
    message,
):
    return Notification.objects.get_or_create(
        student=student,
        deadline=deadline,
        personal_task=personal_task,
        notification_type=notification_type,
        scheduled_at=scheduled_at,
        defaults={
            "reminder": reminder,
            "title": title[:200],
            "message": message[:300],
        },
    )


def sync_student_notifications(student, now=None):
    now = now or timezone.now()
    settings, _ = StudentNotificationSettings.objects.get_or_create(student=student)
    subscribed_classes = ClassSubscription.objects.filter(student=student).values_list(
        "class_group_id",
        flat=True,
    )
    deadlines = Deadline.objects.filter(
        class_group_id__in=subscribed_classes,
        is_active=True,
    ).prefetch_related("reminders")

    for deadline in deadlines:
        state = _state_for(student, deadline)
        if state.status == "done":
            Notification.objects.filter(
                student=student,
                deadline=deadline,
                wechat_sent_at__isnull=True,
            ).delete()
            continue
        due = _local_fields(deadline.due_at)
        if settings.due_24h_enabled and now < deadline.due_at <= now + timedelta(hours=24):
            _create_notification(
                student,
                deadline=deadline,
                notification_type="due_24h",
                scheduled_at=deadline.due_at - timedelta(hours=24),
                title=f"24 小时内截止：{deadline.title}",
                message=f"{due['date']} {due['time']} 前提交 · {deadline.class_group.course.name}",
            )
        for reminder in deadline.reminders.filter(student=student, remind_at__lte=now):
            _create_notification(
                student,
                deadline=deadline,
                reminder=reminder,
                notification_type="custom_reminder",
                scheduled_at=reminder.remind_at,
                title=f"提醒：{deadline.title}",
                message=f"你设置的提醒时间已到 · 截止 {due['date']} {due['time']}",
            )

    personal_tasks = student.personal_tasks.prefetch_related("reminders").filter(
        status__in=["todo", "doing"],
    )
    for task in personal_tasks:
        due = _local_fields(task.due_at)
        if settings.due_24h_enabled and now < task.due_at <= now + timedelta(hours=24):
            _create_notification(
                student,
                personal_task=task,
                notification_type="due_24h",
                scheduled_at=task.due_at - timedelta(hours=24),
                title=f"24 小时内截止：{task.title}",
                message=f"{due['date']} {due['time']} 前完成 · 个人待办",
            )
        for reminder in task.reminders.filter(student=student, remind_at__lte=now):
            _create_notification(
                student,
                personal_task=task,
                reminder=reminder,
                notification_type="custom_reminder",
                scheduled_at=reminder.remind_at,
                title=f"提醒：{task.title}",
                message=f"你设置的提醒时间已到 · 截止 {due['date']} {due['time']}",
            )

    completed_personal_ids = student.personal_tasks.filter(status="done").values_list("id", flat=True)
    Notification.objects.filter(
        student=student,
        personal_task_id__in=completed_personal_ids,
        wechat_sent_at__isnull=True,
    ).delete()


def dispatch_student_wechat_notifications(student, now=None):
    now = now or timezone.now()
    settings, _ = StudentNotificationSettings.objects.get_or_create(student=student)
    if not settings.wechat_enabled:
        return {"sent": 0, "failed": 0, "skipped": 0}
    sender = WeChatSender()
    notifications = Notification.objects.filter(
        student=student,
        scheduled_at__lte=now,
        wechat_sent_at__isnull=True,
    ).filter(
        Q(wechat_claimed_at__isnull=True)
        | Q(wechat_claimed_at__lt=now - timedelta(minutes=10))
    ).order_by("scheduled_at", "id")
    sent = failed = skipped = 0
    for notification in notifications:
        if not settings.wechat_openid:
            skipped += 1
            continue
        claimed = Notification.objects.filter(
            pk=notification.pk,
            wechat_sent_at__isnull=True,
        ).filter(
            Q(wechat_claimed_at__isnull=True)
            | Q(wechat_claimed_at__lt=now - timedelta(minutes=10))
        ).update(wechat_claimed_at=now)
        if not claimed:
            skipped += 1
            continue
        try:
            sender.send(
                openid=settings.wechat_openid,
                title=notification.title,
                message=notification.message,
                scheduled_at=notification.scheduled_at,
            )
        except WeChatDeliveryError as exc:
            notification.wechat_error = str(exc)
            notification.wechat_claimed_at = None
            notification.save(update_fields=["wechat_error", "wechat_claimed_at"])
            failed += 1
        else:
            notification.wechat_sent_at = now
            notification.wechat_claimed_at = None
            notification.wechat_error = ""
            notification.save(update_fields=["wechat_sent_at", "wechat_claimed_at", "wechat_error"])
            sent += 1
    return {"sent": sent, "failed": failed, "skipped": skipped}


def _notification_settings_data(student):
    notification_settings, _ = StudentNotificationSettings.objects.get_or_create(student=student)
    sender = WeChatSender()
    return {
        "due24hEnabled": notification_settings.due_24h_enabled,
        "wechatEnabled": notification_settings.wechat_enabled,
        "wechatBound": bool(notification_settings.wechat_openid),
        "wechatMode": django_settings.WECHAT_PUSH_MODE,
        "wechatConfigured": (
            sender.is_official_account_ready
            if django_settings.WECHAT_PUSH_MODE == "official_account"
            else django_settings.WECHAT_PUSH_MODE in {"log", "webhook"}
        ),
        "wechatBindingAvailable": (
            django_settings.WECHAT_PUSH_MODE == "official_account"
            and sender.is_official_account_ready
        ),
        # 日志模式保留测试 OpenID；生产环境的正式通道只能通过 OAuth 写入。
        "wechatOpenid": (
            notification_settings.wechat_openid
            if django_settings.WECHAT_PUSH_MODE == "log"
            else ""
        ),
    }


def _get_demo_student():
    school, _ = School.objects.get_or_create(
        code="demo-school",
        defaults={"name": "示范国际学校"},
    )
    term, _ = Term.objects.get_or_create(
        school=school,
        name="2026-2027 秋季学期",
        defaults={
            "start_date": datetime(2026, 8, 25).date(),
            "end_date": datetime(2027, 1, 20).date(),
        },
    )
    student, created = User.objects.get_or_create(
        username="student@demo.local",
        defaults={"first_name": "林瑞轩", "email": "student@demo.local"},
    )
    if created:
        student.set_password("demo123456")
        student.save(update_fields=["password"])
    StudentProfile.objects.get_or_create(
        user=student,
        defaults={"school": school, "term": term, "grade": "12年级", "curriculum": "AP"},
    )
    profile = student.student_profile
    for name, teacher, class_name in [
        ("AP 微积分", "张老师", "A班"),
        ("数据库原理", "王老师", "B班"),
        ("数据结构", "陈老师", "C班"),
    ]:
        course, _ = Course.objects.get_or_create(
            school=school,
            term=term,
            name=name,
            defaults={
                "start_date": term.start_date,
                "end_date": term.end_date,
            },
        )
        if not course.start_date or not course.end_date:
            course.start_date = course.start_date or term.start_date
            course.end_date = course.end_date or term.end_date
            course.save(update_fields=["start_date", "end_date"])
        class_group, _ = ClassGroup.objects.get_or_create(
            course=course,
            name=class_name,
            defaults={"teacher_name": teacher},
        )
        if created:
            ClassSubscription.objects.get_or_create(student=student, class_group=class_group)

    course_map = {
        class_group.course.name: class_group
        for class_group in ClassGroup.objects.filter(
            course__school=school,
            course__term=term,
        ).select_related("course")
    }
    now = timezone.localtime()
    seed_deadlines = [
        ("AP 微积分", "作业：积分应用练习", now.replace(hour=9, minute=0, second=0, microsecond=0), "formative", "完成课本第 3 章练习并上传答案。"),
        ("数据库原理", "第三章阅读与思考题", now.replace(hour=14, minute=0, second=0, microsecond=0), "formative", "阅读第三章并完成课后思考题。"),
        ("数据结构", "实验报告提交", now + timedelta(days=2, hours=5), "summative", "整理实验过程、结果和复杂度分析。"),
    ]
    for course_name, title, due_at, kind, description in seed_deadlines:
        deadline, created_deadline = Deadline.objects.get_or_create(
            class_group=course_map[course_name],
            title=title,
            defaults={
                "source_type": "course",
                "kind": kind,
                "due_at": due_at,
                "description": description,
                "created_by": student,
            },
        )
    return student


def _get_demo_teacher():
    school = School.objects.get(code="demo-school")
    teacher, created = User.objects.get_or_create(
        username="teacher.demo@ddl.local",
        defaults={"first_name": "王老师", "email": "teacher.demo@ddl.local"},
    )
    if created:
        teacher.set_password("Teacher2026!")
        teacher.save(update_fields=["password"])
    application, _ = TeacherApplication.objects.get_or_create(
        user=teacher,
        defaults={
            "school": school,
            "proof": "系统内置教师演示账号。",
            "status": "approved",
        },
    )
    if application.status != "approved":
        application.status = "approved"
        application.save(update_fields=["status"])
    return teacher


def _student_for_request(request):
    if request.user.is_authenticated and hasattr(request.user, "student_profile"):
        return request.user
    return None


def _auth_error():
    return JsonResponse({"error": "请先登录学生账号。"}, status=401)


def _friend_pair(first, second):
    return (first, second) if first.pk < second.pk else (second, first)


def _friend_user_data(user, viewer, relation=None):
    profile = user.student_profile
    status = "not_friend"
    if relation:
        if relation.status == "accepted":
            status = "friend"
        elif relation.requested_by_id == viewer.id:
            status = "pending_sent"
        else:
            status = "pending_received"
    name = user.get_full_name() or user.username
    return {
        "id": user.id,
        "name": name,
        "initials": name[:1] or "?",
        "school": profile.school.name,
        "grade": profile.grade or "学生",
        "bio": profile.motto or "还没有填写个人介绍",
        "status": status,
        "mutual": 0,
        "online": False,
        "verified": False,
    }


@require_http_methods(["GET"])
def api_friends(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    keyword = request.GET.get("q", "").strip()
    relations = StudentFriendship.objects.filter(
        Q(user_a=student) | Q(user_b=student)
    ).select_related("user_a", "user_b")
    relation_by_user = {}
    for relation in relations:
        other = relation.user_b if relation.user_a_id == student.id else relation.user_a
        relation_by_user[other.id] = relation

    users = User.objects.filter(
        student_profile__isnull=False,
    ).exclude(pk=student.pk).select_related(
        "student_profile__school",
    ).order_by("first_name", "username")
    if keyword:
        users = users.filter(
            Q(first_name__icontains=keyword)
            | Q(last_name__icontains=keyword)
            | Q(username__icontains=keyword)
            | Q(student_profile__school__name__icontains=keyword)
            | Q(student_profile__grade__icontains=keyword)
            | Q(student_profile__motto__icontains=keyword)
        )
    user_data = [
        _friend_user_data(user, student, relation_by_user.get(user.id))
        for user in users
    ]
    return JsonResponse({
        "users": user_data,
        "counts": {
            "friends": sum(item["status"] == "friend" for item in user_data),
            "incoming": sum(item["status"] == "pending_received" for item in user_data),
            "outgoing": sum(item["status"] == "pending_sent" for item in user_data),
        },
    })


@require_http_methods(["POST"])
def api_friend_action(request, user_id, action):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    target = User.objects.filter(
        pk=user_id,
        student_profile__isnull=False,
    ).select_related("student_profile__school").first()
    if not target or target.pk == student.pk:
        return JsonResponse({"error": "好友对象不存在。"}, status=404)
    user_a, user_b = _friend_pair(student, target)

    with transaction.atomic():
        relation = StudentFriendship.objects.select_for_update().filter(
            user_a=user_a,
            user_b=user_b,
        ).first()
        if action == "request":
            if relation and relation.status == "accepted":
                return JsonResponse({"error": "你们已经是好友。"}, status=400)
            if relation and relation.requested_by_id == student.id:
                return JsonResponse({"user": _friend_user_data(target, student, relation)})
            if relation and relation.requested_by_id == target.id:
                return JsonResponse({"error": "对方已经向你发送好友申请，请先处理申请。"}, status=400)
            relation = StudentFriendship.objects.create(
                user_a=user_a,
                user_b=user_b,
                requested_by=student,
                status="pending",
            )
        elif action == "accept":
            if not relation or relation.status != "pending" or relation.requested_by_id != target.id:
                return JsonResponse({"error": "这条好友申请不存在或已处理。"}, status=400)
            relation.status = "accepted"
            relation.save(update_fields=["status", "updated_at"])
        elif action == "reject":
            if not relation or relation.status != "pending" or relation.requested_by_id != target.id:
                return JsonResponse({"error": "这条好友申请不存在或已处理。"}, status=400)
            relation.delete()
            relation = None
        elif action == "cancel":
            if not relation or relation.status != "pending" or relation.requested_by_id != student.id:
                return JsonResponse({"error": "这条好友申请不存在或已处理。"}, status=400)
            relation.delete()
            relation = None
        elif action == "delete":
            if not relation or relation.status != "accepted":
                return JsonResponse({"error": "你们目前不是好友。"}, status=400)
            relation.delete()
            relation = None
        else:
            return JsonResponse({"error": "不支持的好友操作。"}, status=400)

    return JsonResponse({
        "user": _friend_user_data(target, student, relation),
    })


def _chat_task_card(message):
    task_card = None
    if getattr(message, "recalled_at", None) is None and message.shared_deadline:
        deadline = message.shared_deadline
        task_card = {
            "type": "deadline",
            "id": deadline.id,
            "title": deadline.title,
            "date": _local_fields(deadline.due_at)["date"],
            "time": _local_fields(deadline.due_at)["time"],
            "source": {"course": "📚", "admissions": "🎓", "competition": "🏆"}.get(deadline.source_type, "📌"),
            "sourceName": (
                f"{deadline.class_group.course.name} · {deadline.class_group.name}"
                if deadline.class_group else "官方安排"
            ),
        }
    elif getattr(message, "recalled_at", None) is None and message.shared_personal_task:
        task = message.shared_personal_task
        due = _local_fields(task.due_at)
        task_card = {
            "type": "personal",
            "id": task.id,
            "title": task.title,
            "date": due["date"],
            "time": due["time"],
            "source": "✏️",
            "sourceName": "我的待办",
        }
    return task_card


def _chat_message_data(message, viewer):
    local = timezone.localtime(message.created_at, SHANGHAI_TZ)
    return {
        "id": message.id,
        "senderId": message.sender_id,
        "senderName": message.sender.get_full_name() or message.sender.username,
        "content": "消息已撤回" if message.recalled_at else message.content,
        "imageUrl": "" if message.recalled_at else message.image.url if message.image else "",
        "attachment": (
            {
                "url": message.attachment.url,
                "name": os.path.basename(message.attachment.name),
                "size": message.attachment.size,
            }
            if not message.recalled_at and message.attachment
            else None
        ),
        "createdAt": message.created_at.isoformat(),
        "date": local.strftime("%Y-%m-%d"),
        "time": local.strftime("%H:%M"),
        "isMine": message.sender_id == viewer.id,
        "read": message.read_at is not None,
        "recalled": message.recalled_at is not None,
        "taskCard": _chat_task_card(message),
    }


def _chat_relation(student, target):
    if ChatBlock.objects.filter(
        Q(blocker=student, blocked=target) | Q(blocker=target, blocked=student)
    ).exists():
        return None
    user_a, user_b = _friend_pair(student, target)
    return StudentFriendship.objects.filter(
        user_a=user_a,
        user_b=user_b,
        status="accepted",
    ).first()


def _chat_peer_data(target, viewer, conversation=None):
    data = _friend_user_data(target, viewer, _chat_relation(viewer, target))
    messages = conversation.messages.select_related("sender") if conversation else []
    last_message = messages.order_by("-created_at", "-id").first() if conversation else None
    data.update({
        "lastMessage": (
            last_message.content
            if last_message and last_message.content
            else "图片"
            if last_message and last_message.image
            else "任务"
            if last_message and (
                last_message.shared_deadline_id or last_message.shared_personal_task_id
            )
            else "文件"
            if last_message and last_message.attachment
            else ""
        ),
        "lastAt": (
            timezone.localtime(last_message.created_at, SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M")
            if last_message else ""
        ),
        "unread": (
            conversation.messages.filter(
                sender=target,
                read_at__isnull=True,
            ).count()
            if conversation else 0
        ),
        "conversationId": conversation.id if conversation else None,
        "muted": bool(
            conversation
            and ChatMute.objects.filter(student=viewer, conversation=conversation).exists()
        ),
        "blocked": ChatBlock.objects.filter(blocker=viewer, blocked=target).exists(),
    })
    return data


def _chat_conversation_for(student, target, *, create=False):
    if not _chat_relation(student, target):
        return None
    user_a, user_b = _friend_pair(student, target)
    conversation = ChatConversation.objects.filter(user_a=user_a, user_b=user_b).first()
    if conversation is None and create:
        conversation = ChatConversation.objects.create(user_a=user_a, user_b=user_b)
    return conversation


@require_http_methods(["GET"])
def api_chats(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    relations = StudentFriendship.objects.filter(
        Q(user_a=student) | Q(user_b=student),
        status="accepted",
    ).select_related("user_a", "user_b")
    chats = []
    for relation in relations:
        target = relation.user_b if relation.user_a_id == student.id else relation.user_a
        if ChatBlock.objects.filter(
            Q(blocker=student, blocked=target) | Q(blocker=target, blocked=student)
        ).exists():
            continue
        conversation = _chat_conversation_for(student, target)
        chats.append(_chat_peer_data(target, student, conversation))
    chats.sort(
        key=lambda item: (bool(item["lastAt"]), item["lastAt"] or item["name"]),
        reverse=True,
    )
    return JsonResponse({
        "chats": chats,
        "unread": sum(item["unread"] for item in chats),
    })


@require_http_methods(["GET", "POST"])
def api_chat_messages(request, user_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    target = User.objects.filter(
        pk=user_id,
        student_profile__isnull=False,
    ).select_related("student_profile__school").first()
    if not target or target.pk == student.pk:
        return JsonResponse({"error": "聊天对象不存在。"}, status=404)
    conversation = _chat_conversation_for(student, target, create=request.method == "POST")
    if conversation is None:
        return JsonResponse({"error": "只有好友之间可以发送消息。"}, status=403)

    if request.method == "POST":
        if request.content_type and request.content_type.startswith("multipart/"):
            content = request.POST.get("content", "").strip()
            share_type = request.POST.get("shareType", "").strip()
            share_id = request.POST.get("shareId", "").strip()
        else:
            payload = _json_body(request)
            content = str(payload.get("content", "")).strip()
            share_type = str(payload.get("shareType", "")).strip()
            share_id = str(payload.get("shareId", "")).strip()
        image = request.FILES.get("image")
        attachment = request.FILES.get("attachment")
        if image and attachment:
            return JsonResponse({"error": "一条消息只能上传一个文件。"}, status=400)
        shared_deadline = None
        shared_personal_task = None
        if share_type or share_id:
            if share_type not in {"deadline", "personal"} or not share_id.isdigit():
                return JsonResponse({"error": "分享的任务无效。"}, status=400)
            if share_type == "deadline":
                shared_deadline = Deadline.objects.filter(
                    pk=int(share_id),
                    is_active=True,
                    class_group__subscriptions__student=student,
                ).select_related("class_group__course").first()
            else:
                shared_personal_task = PersonalTask.objects.filter(
                    pk=int(share_id),
                    student=student,
                ).first()
            if not shared_deadline and not shared_personal_task:
                return JsonResponse({"error": "你无权分享这个任务。"}, status=403)
        if (
            not content
            and not image
            and not attachment
            and not shared_deadline
            and not shared_personal_task
        ):
            return JsonResponse({"error": "消息内容不能为空。"}, status=400)
        if len(content) > 2000:
            return JsonResponse({"error": "消息不能超过 2000 个字符。"}, status=400)
        if image:
            try:
                _validate_chat_image(image)
            except ValidationError as exc:
                return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        if attachment:
            try:
                _validate_chat_attachment(attachment)
            except ValidationError as exc:
                return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        message = ChatMessage(
            conversation=conversation,
            sender=student,
            content=content,
            image=image,
            attachment=attachment,
            shared_deadline=shared_deadline,
            shared_personal_task=shared_personal_task,
        )
        try:
            message.full_clean()
            message.save()
        except ValidationError as exc:
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        ChatNotification.objects.create(student=target, message=message)
        conversation.save(update_fields=["updated_at"])
        channel_layer = get_channel_layer()
        if channel_layer:
            group_name = f"chat_{min(student.pk, target.pk)}_{max(student.pk, target.pk)}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "chat.message",
                    "messageId": message.id,
                },
            )
        return JsonResponse({
            "peer": _chat_peer_data(target, student, conversation),
            "message": _chat_message_data(message, student),
        }, status=201)

    conversation.messages.filter(
        sender=target,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    ChatNotification.objects.filter(
        student=student,
        message__conversation=conversation,
        message__sender=target,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    messages = list(
        conversation.messages.select_related("sender").order_by("created_at", "id")[:100]
    )
    return JsonResponse({
        "peer": _chat_peer_data(target, student, conversation),
        "messages": [_chat_message_data(message, student) for message in messages],
    })


@require_http_methods(["POST"])
def api_chat_message_recall(request, message_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    message = ChatMessage.objects.select_related("conversation").filter(
        pk=message_id,
        sender=student,
    ).first()
    if not message:
        return JsonResponse({"error": "只能撤回自己发送的消息。"}, status=404)
    if message.recalled_at:
        return JsonResponse({"message": _chat_message_data(message, student)})
    if timezone.now() - message.created_at > timedelta(minutes=2):
        return JsonResponse({"error": "消息发送超过 2 分钟，无法撤回。"}, status=400)
    message.recalled_at = timezone.now()
    message.save(update_fields=["recalled_at"])
    return JsonResponse({"message": _chat_message_data(message, student)})


@require_http_methods(["POST"])
def api_chat_mute(request, user_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    target = User.objects.filter(pk=user_id, student_profile__isnull=False).first()
    if not target or target.pk == student.pk:
        return JsonResponse({"error": "聊天对象不存在。"}, status=404)
    conversation = _chat_conversation_for(student, target)
    if not conversation:
        return JsonResponse({"error": "当前没有可设置的聊天会话。"}, status=404)
    mute, created = ChatMute.objects.get_or_create(student=student, conversation=conversation)
    if not created:
        mute.delete()
    return JsonResponse({
        "muted": created,
        "peer": _chat_peer_data(target, student, conversation),
    })


@require_http_methods(["POST"])
def api_chat_block(request, user_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    target = User.objects.filter(pk=user_id, student_profile__isnull=False).first()
    if not target or target.pk == student.pk:
        return JsonResponse({"error": "聊天对象不存在。"}, status=404)
    ChatBlock.objects.get_or_create(blocker=student, blocked=target)
    return JsonResponse({"blocked": True})


@require_http_methods(["POST"])
def api_chat_report(request, user_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    target = User.objects.filter(pk=user_id, student_profile__isnull=False).first()
    if not target or target.pk == student.pk:
        return JsonResponse({"error": "聊天对象不存在。"}, status=404)
    payload = _json_body(request)
    reason = str(payload.get("reason", "")).strip()
    if not reason:
        return JsonResponse({"error": "请填写举报原因。"}, status=400)
    ChatReport.objects.create(reporter=student, target=target, reason=reason[:300])
    return JsonResponse({"reported": True}, status=201)


def _chat_group_data(group, student):
    membership = group.members.filter(student=student).first()
    last_message = group.messages.select_related("sender").order_by("-created_at", "-id").first()
    return {
        "id": group.id,
        "name": group.name,
        "kind": group.kind,
        "kindLabel": group.get_kind_display(),
        "description": group.description,
        "memberCount": group.members.count(),
        "joined": membership is not None,
        "role": membership.role if membership else "",
        "lastMessage": (
            last_message.content
            if last_message and last_message.content
            else "图片"
            if last_message and last_message.image
            else "任务"
            if last_message and (
                last_message.shared_deadline_id or last_message.shared_personal_task_id
            )
            else "文件"
            if last_message and last_message.attachment
            else ""
        ),
        "lastAt": (
            timezone.localtime(last_message.created_at, SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M")
            if last_message else ""
        ),
    }


def _chat_group_invitation_data(invitation, viewer):
    inviter_name = invitation.inviter.get_full_name() or invitation.inviter.username
    invitee_name = invitation.invitee.get_full_name() or invitation.invitee.username
    return {
        "id": invitation.id,
        "status": invitation.status,
        "group": _chat_group_data(invitation.group, viewer),
        "inviter": {
            "id": invitation.inviter_id,
            "name": inviter_name,
            "initials": inviter_name[:1] or "?",
        },
        "invitee": {
            "id": invitation.invitee_id,
            "name": invitee_name,
            "initials": invitee_name[:1] or "?",
        },
        "createdAt": timezone.localtime(
            invitation.created_at,
            SHANGHAI_TZ,
        ).strftime("%Y-%m-%d %H:%M"),
    }


def _chat_group_message_data(message, viewer):
    local = timezone.localtime(message.created_at, SHANGHAI_TZ)
    return {
        "id": message.id,
        "senderId": message.sender_id,
        "senderName": message.sender.get_full_name() or message.sender.username,
        "content": message.content,
        "imageUrl": message.image.url if message.image else "",
        "attachment": (
            {
                "url": message.attachment.url,
                "name": os.path.basename(message.attachment.name),
                "size": message.attachment.size,
            }
            if message.attachment
            else None
        ),
        "taskCard": _chat_task_card(message),
        "createdAt": message.created_at.isoformat(),
        "date": local.strftime("%Y-%m-%d"),
        "time": local.strftime("%H:%M"),
        "isMine": message.sender_id == viewer.id,
    }


@require_http_methods(["GET", "POST"])
def api_chat_groups(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    if request.method == "POST":
        payload = _json_body(request)
        name = str(payload.get("name", "")).strip()
        kind = str(payload.get("kind", "learning")).strip()
        description = str(payload.get("description", "")).strip()
        if not name:
            return JsonResponse({"error": "请填写小组名称。"}, status=400)
        if kind not in dict(ChatGroup.KIND_CHOICES):
            return JsonResponse({"error": "小组类型无效。"}, status=400)
        if len(name) > 120 or len(description) > 500:
            return JsonResponse({"error": "小组信息超出长度限制。"}, status=400)
        group = ChatGroup.objects.create(
            name=name,
            kind=kind,
            description=description,
            created_by=student,
        )
        ChatGroupMember.objects.create(group=group, student=student, role="owner")
        return JsonResponse({"group": _chat_group_data(group, student)}, status=201)
    groups = ChatGroup.objects.all().prefetch_related("members", "messages__sender")
    invitations = ChatGroupInvitation.objects.filter(
        invitee=student,
        status="pending",
    ).select_related("group", "inviter")
    return JsonResponse({
        "groups": [_chat_group_data(group, student) for group in groups],
        "invitations": [
            _chat_group_invitation_data(invitation, student)
            for invitation in invitations
        ],
    })


@require_http_methods(["GET", "POST"])
def api_chat_group_invites(request, group_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    group = ChatGroup.objects.filter(pk=group_id).first()
    if not group:
        return JsonResponse({"error": "小组不存在。"}, status=404)
    membership = ChatGroupMember.objects.filter(group=group, student=student).first()
    if not membership or membership.role not in {"owner", "admin"}:
        return JsonResponse({"error": "只有小组创建者或管理员可以邀请成员。"}, status=403)

    if request.method == "POST":
        payload = _json_body(request)
        target_id = payload.get("targetId")
        try:
            target_id = int(target_id)
        except (TypeError, ValueError):
            return JsonResponse({"error": "请选择要邀请的好友。"}, status=400)
        target = User.objects.filter(
            pk=target_id,
            student_profile__isnull=False,
        ).first()
        if not target or target.pk == student.pk:
            return JsonResponse({"error": "邀请对象不存在。"}, status=404)
        if not _chat_relation(student, target):
            return JsonResponse({"error": "只能邀请已添加的好友。"}, status=403)
        if ChatGroupMember.objects.filter(group=group, student=target).exists():
            return JsonResponse({"error": "对方已经是小组成员。"}, status=400)

        with transaction.atomic():
            invitation, created = ChatGroupInvitation.objects.select_for_update().get_or_create(
                group=group,
                invitee=target,
                defaults={
                    "inviter": student,
                    "status": "pending",
                },
            )
            if not created:
                if invitation.status == "pending":
                    return JsonResponse({"error": "邀请已经发出，等待对方确认。"}, status=400)
                invitation.inviter = student
                invitation.status = "pending"
                invitation.save(update_fields=["inviter", "status", "updated_at"])
        return JsonResponse({
            "invitation": _chat_group_invitation_data(invitation, target),
        }, status=201)

    friend_relations = StudentFriendship.objects.filter(
        Q(user_a=student) | Q(user_b=student),
        status="accepted",
    ).select_related("user_a", "user_b", "user_a__student_profile__school", "user_b__student_profile__school")
    member_ids = set(group.members.values_list("student_id", flat=True))
    pending_ids = set(
        ChatGroupInvitation.objects.filter(
            group=group,
            status="pending",
        ).values_list("invitee_id", flat=True)
    )
    candidates = []
    for relation in friend_relations:
        friend = relation.user_b if relation.user_a_id == student.id else relation.user_a
        if friend.id in member_ids:
            continue
        profile = friend.student_profile
        candidates.append({
            "id": friend.id,
            "name": friend.get_full_name() or friend.username,
            "initials": (friend.get_full_name() or friend.username)[:1] or "?",
            "school": profile.school.name,
            "grade": profile.grade or "学生",
            "pending": friend.id in pending_ids,
        })
    pending = ChatGroupInvitation.objects.filter(
        group=group,
        status="pending",
    ).select_related("group", "inviter", "invitee")
    return JsonResponse({
        "candidates": candidates,
        "pending": [
            _chat_group_invitation_data(invitation, invitation.invitee)
            for invitation in pending
        ],
    })


@require_http_methods(["POST"])
def api_chat_group_invitation_action(request, invitation_id, action):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    if action not in {"accept", "reject"}:
        return JsonResponse({"error": "不支持的邀请操作。"}, status=400)

    with transaction.atomic():
        invitation = ChatGroupInvitation.objects.select_for_update().select_related(
            "group",
            "inviter",
        ).filter(pk=invitation_id, invitee=student).first()
        if not invitation:
            return JsonResponse({"error": "小组邀请不存在。"}, status=404)
        if invitation.status != "pending":
            return JsonResponse({"error": "该邀请已经处理。"}, status=400)
        if action == "accept":
            ChatGroupMember.objects.get_or_create(
                group=invitation.group,
                student=student,
                defaults={"role": "member"},
            )
            invitation.status = "accepted"
        else:
            invitation.status = "rejected"
        invitation.save(update_fields=["status", "updated_at"])
        group_data = _chat_group_data(invitation.group, student)
    return JsonResponse({
        "group": group_data,
        "invitation": _chat_group_invitation_data(invitation, student),
    })


@require_http_methods(["POST"])
def api_chat_group_action(request, group_id, action):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    group = ChatGroup.objects.filter(pk=group_id).first()
    if not group:
        return JsonResponse({"error": "小组不存在。"}, status=404)
    membership = ChatGroupMember.objects.filter(group=group, student=student).first()
    if action == "join":
        if membership:
            return JsonResponse({"group": _chat_group_data(group, student)})
        membership = ChatGroupMember.objects.create(group=group, student=student)
    elif action == "leave":
        if not membership:
            return JsonResponse({"error": "你还不是小组成员。"}, status=400)
        if membership.role == "owner":
            return JsonResponse({"error": "创建者不能直接退出小组。"}, status=400)
        membership.delete()
    else:
        return JsonResponse({"error": "不支持的小组操作。"}, status=400)
    return JsonResponse({"group": _chat_group_data(group, student)})


@require_http_methods(["GET", "POST"])
def api_chat_group_messages(request, group_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    group = ChatGroup.objects.filter(pk=group_id).first()
    if not group:
        return JsonResponse({"error": "小组不存在。"}, status=404)
    if not ChatGroupMember.objects.filter(group=group, student=student).exists():
        return JsonResponse({"error": "加入小组后才能查看消息。"}, status=403)
    if request.method == "POST":
        if request.content_type and request.content_type.startswith("multipart/"):
            content = request.POST.get("content", "").strip()
            share_type = request.POST.get("shareType", "").strip()
            share_id = request.POST.get("shareId", "").strip()
        else:
            payload = _json_body(request)
            content = str(payload.get("content", "")).strip()
            share_type = str(payload.get("shareType", "")).strip()
            share_id = str(payload.get("shareId", "")).strip()
        image = request.FILES.get("image")
        attachment = request.FILES.get("attachment")
        if image and attachment:
            return JsonResponse({"error": "一条消息只能上传一个文件。"}, status=400)
        shared_deadline = None
        shared_personal_task = None
        if share_type or share_id:
            if share_type not in {"deadline", "personal"} or not share_id.isdigit():
                return JsonResponse({"error": "分享的任务无效。"}, status=400)
            if share_type == "deadline":
                shared_deadline = Deadline.objects.filter(
                    pk=int(share_id),
                    is_active=True,
                    class_group__subscriptions__student=student,
                ).select_related("class_group__course").first()
            else:
                shared_personal_task = PersonalTask.objects.filter(
                    pk=int(share_id),
                    student=student,
                ).first()
            if not shared_deadline and not shared_personal_task:
                return JsonResponse({"error": "你无权分享这个任务。"}, status=403)
        if not content and not image and not attachment and not shared_deadline and not shared_personal_task:
            return JsonResponse({"error": "消息内容不能为空。"}, status=400)
        if len(content) > 2000:
            return JsonResponse({"error": "消息不能超过 2000 个字符。"}, status=400)
        if image:
            try:
                _validate_chat_image(image)
            except ValidationError as exc:
                return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        if attachment:
            try:
                _validate_chat_attachment(attachment)
            except ValidationError as exc:
                return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        message = ChatGroupMessage(
            group=group,
            sender=student,
            content=content,
            image=image,
            attachment=attachment,
            shared_deadline=shared_deadline,
            shared_personal_task=shared_personal_task,
        )
        try:
            message.full_clean()
            message.save()
        except ValidationError as exc:
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        group.save(update_fields=["updated_at"])
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"chat_group_{group.id}",
                {
                    "type": "chat.group_message",
                    "messageId": message.id,
                },
            )
        return JsonResponse({
            "group": _chat_group_data(group, student),
            "message": _chat_group_message_data(message, student),
        }, status=201)
    messages = group.messages.select_related(
        "sender",
        "shared_deadline__class_group__course",
        "shared_personal_task",
    ).order_by("-created_at", "-id")[:100]
    return JsonResponse({
        "group": _chat_group_data(group, student),
        "messages": [
            _chat_group_message_data(message, student)
            for message in reversed(list(messages))
        ],
    })


def _teacher_for_request(request):
    if not request.user.is_authenticated:
        return None
    application = getattr(request.user, "teacher_application", None)
    if application and application.status == "approved":
        return request.user
    return None


def _teacher_auth_error(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "请先登录教师账号。"}, status=401)
    application = getattr(request.user, "teacher_application", None)
    if application and application.status == "pending":
        return JsonResponse({"error": "教师账号正在审核中，请等待管理员通过。"}, status=403)
    if application and application.status == "rejected":
        return JsonResponse({"error": "教师申请未通过，请联系管理员。"}, status=403)
    return JsonResponse({"error": "当前账号没有教师权限。"}, status=403)


def _course_status(course):
    if not course.is_active:
        return "ended"
    if course.end_date and course.end_date <= timezone.localdate():
        return "needs_confirmation"
    return "active"


def _teacher_course_data(course):
    status = _course_status(course)
    return {
        "id": course.id,
        "name": course.name,
        "code": course.code,
        "termId": course.term_id,
        "termName": course.term.name,
        "startDate": course.start_date.isoformat() if course.start_date else "",
        "endDate": course.end_date.isoformat() if course.end_date else "",
        "isActive": course.is_active,
        "status": status,
        "needsEndConfirmation": status == "needs_confirmation",
        "canEnd": course.created_by_id is not None,
        "classes": [
            {
                "id": class_group.id,
                "name": class_group.name,
                "teacherName": class_group.teacher_name,
                "owned": class_group.created_by_id == course.created_by_id,
            }
            for class_group in course.classes.all()
        ],
    }


def _teacher_deadline_data(deadline):
    due = _local_fields(deadline.due_at)
    return {
        "id": deadline.id,
        "title": deadline.title,
        "description": deadline.description,
        "kind": deadline.kind,
        "sourceType": deadline.source_type,
        **due,
        "classId": deadline.class_group_id,
        "className": deadline.class_group.name,
        "courseName": deadline.class_group.course.name,
        "updatedAt": deadline.updated_at.isoformat(),
    }

@ensure_csrf_cookie
@require_http_methods(["GET"])
def api_options(request):
    demo_student = _get_demo_student() if django_settings.SHOW_DEMO_ACCOUNTS else None
    demo_teacher = _get_demo_teacher() if django_settings.SHOW_DEMO_ACCOUNTS else None
    schools = School.objects.prefetch_related("terms").order_by("name")
    return JsonResponse({
        "schools": [
            {
                "id": school.id,
                "name": school.name,
                "terms": [
                    {
                        "id": term.id,
                        "name": term.name,
                    }
                    for term in school.terms.all()
                ],
            }
            for school in schools
        ],
        "demo": (
            {
                "email": demo_student.username,
                "password": "demo123456",
            }
            if demo_student
            else None
        ),
        "teacherDemo": (
            {
                "email": demo_teacher.username,
                "password": "Teacher2026!",
            }
            if demo_teacher
            else None
        ),
    })


@require_http_methods(["GET"])
def api_bootstrap(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    subscriptions = list(
        ClassSubscription.objects.filter(student=student)
        .select_related("class_group__course")
    )
    subscribed_classes = {item.class_group_id for item in subscriptions}
    deadlines = Deadline.objects.filter(
        class_group_id__in=subscribed_classes,
        is_active=True,
    ).select_related("class_group__course", "created_by")
    task_data = [_deadline_data(deadline, student) for deadline in deadlines]
    task_data.extend(
        _personal_task_data(task)
        for task in student.personal_tasks.prefetch_related("reminders").all()
    )
    task_data.sort(key=lambda task: (task["date"], task["time"]))

    school = student.student_profile.school
    term = student.student_profile.term
    classes = ClassGroup.objects.filter(
        course__school=school,
        course__term=term,
    ).select_related("course")
    subscription_data = []
    subscribed_course_ids = {item.class_group.course_id for item in subscriptions}
    subscribed_class_by_course = {
        item.class_group.course_id: item.class_group
        for item in subscriptions
    }
    for class_group in classes:
        subscribed_class = subscribed_class_by_course.get(class_group.course_id)
        subscription_data.append({
            "id": class_group.id,
            "classId": class_group.id,
            "courseId": class_group.course_id,
            "name": class_group.course.name,
            "publisher": f"{class_group.teacher_name} · {class_group.name}",
            "type": "课程",
            "count": class_group.deadlines.filter(is_active=True).count(),
            "subscribed": class_group.id in subscribed_classes,
            "color": ["coral", "blue", "yellow"][class_group.course_id % 3],
            "courseSubscribed": class_group.course_id in subscribed_course_ids,
            "currentClassName": subscribed_class.name if subscribed_class else "",
            "currentPublisher": subscribed_class.teacher_name if subscribed_class else "",
            "courseStartDate": (
                class_group.course.start_date.isoformat()
                if class_group.course.start_date else ""
            ),
            "courseEndDate": (
                class_group.course.end_date.isoformat()
                if class_group.course.end_date else ""
            ),
            "courseActive": class_group.course.is_active,
            "courseStatus": _course_status(class_group.course),
        })

    return JsonResponse({
        "student": {
            "name": student.get_full_name() or student.username,
            "email": student.email,
            "school": school.name,
            "term": term.name,
        },
        "today": timezone.localtime().strftime("%Y-%m-%d"),
        "tasks": task_data,
        "subscriptions": subscription_data,
    })


@require_http_methods(["GET"])
def api_dashboard(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    return JsonResponse(_dashboard_data(student))


@require_http_methods(["GET", "PATCH"])
def api_student_profile(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    profile = student.student_profile
    if request.method == "PATCH":
        payload = _json_body(request)
        if "motto" in payload:
            profile.motto = str(payload["motto"]).strip()[:120]
            profile.save(update_fields=["motto"])
    return JsonResponse({
        "name": student.get_full_name() or student.username,
        "school": profile.school.name,
        "term": profile.term.name,
        "grade": profile.grade,
        "curriculum": profile.curriculum,
        "motto": profile.motto,
    })


@require_http_methods(["GET", "POST"])
def api_annual_plan(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    if request.method == "POST":
        try:
            task = _annual_plan_task_from_payload(student, _json_body(request))
        except ValidationError as exc:
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        task.save()
        return JsonResponse(_annual_plan_task_data(task), status=201)

    try:
        year = int(request.GET.get("year", timezone.localdate().year))
        range_start = datetime(year, 1, 1).date()
        range_end = datetime(year, 12, 31).date()
    except (TypeError, ValueError):
        return JsonResponse({"error": "年份格式不正确。"}, status=400)
    tasks = AnnualPlanTask.objects.filter(student=student).prefetch_related("subtasks")
    task_data = [
        _annual_plan_task_data(task)
        for task in tasks
        if (
            task.task_type == "period"
            and task.start_date <= range_end
            and task.end_date >= range_start
        )
        or (
            task.task_type == "node"
            and range_start <= task.node_date <= range_end
        )
    ]
    task_data.sort(key=lambda item: item["startDate"] or item["nodeDate"])
    return JsonResponse({
        "year": year,
        "tasks": task_data,
        "summary": {
            "total": len(task_data),
            "inProgress": sum(item["status"] == "in_progress" for item in task_data),
            "completed": sum(item["status"] == "completed" for item in task_data),
        },
    })


@require_http_methods(["PATCH", "DELETE"])
def api_annual_plan_task_detail(request, task_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    task = AnnualPlanTask.objects.filter(
        pk=task_id,
        student=student,
    ).prefetch_related("subtasks").first()
    if not task:
        return JsonResponse({"error": "年度规划任务不存在。"}, status=404)
    if request.method == "DELETE":
        task.delete()
        return JsonResponse({"ok": True})
    try:
        task = _annual_plan_task_from_payload(student, _json_body(request), task)
    except ValidationError as exc:
        return JsonResponse({"error": "；".join(exc.messages)}, status=400)
    task.save()
    return JsonResponse(_annual_plan_task_data(task))


@require_http_methods(["POST"])
def api_annual_plan_subtask(request, task_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    task = AnnualPlanTask.objects.filter(pk=task_id, student=student).first()
    if not task:
        return JsonResponse({"error": "年度规划任务不存在。"}, status=404)
    payload = _json_body(request)
    title = str(payload.get("title", "")).strip()
    if not title:
        return JsonResponse({"error": "请填写子任务内容。"}, status=400)
    subtask = AnnualPlanSubtask.objects.create(
        task=task,
        title=title[:200],
        due_date=_parse_date(payload.get("dueDate")) if payload.get("dueDate") else None,
    )
    task = AnnualPlanTask.objects.prefetch_related("subtasks").get(pk=task.id)
    return JsonResponse(_annual_plan_task_data(task), status=201)


@require_http_methods(["PATCH", "DELETE"])
def api_annual_plan_subtask_detail(request, task_id, subtask_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    task = AnnualPlanTask.objects.filter(pk=task_id, student=student).first()
    if not task:
        return JsonResponse({"error": "年度规划任务不存在。"}, status=404)
    subtask = AnnualPlanSubtask.objects.filter(pk=subtask_id, task=task).first()
    if not subtask:
        return JsonResponse({"error": "子任务不存在。"}, status=404)
    if request.method == "DELETE":
        subtask.delete()
    else:
        payload = _json_body(request)
        if "title" in payload:
            title = str(payload["title"]).strip()
            if not title:
                return JsonResponse({"error": "请填写子任务内容。"}, status=400)
            subtask.title = title[:200]
        if "completed" in payload:
            subtask.completed = bool(payload["completed"])
        if "dueDate" in payload:
            subtask.due_date = _parse_date(payload["dueDate"]) if payload["dueDate"] else None
        subtask.save()
    task = AnnualPlanTask.objects.prefetch_related("subtasks").get(pk=task.id)
    return JsonResponse(_annual_plan_task_data(task))


@require_http_methods(["POST"])
def api_deadline_state(request, deadline_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    payload = _json_body(request)
    try:
        deadline = Deadline.objects.filter(
            pk=deadline_id,
            is_active=True,
            class_group__subscriptions__student=student,
        ).select_related("class_group__course", "created_by").get()
    except Deadline.DoesNotExist:
        return JsonResponse({"error": "DDL 不存在。"}, status=404)
    state = _state_for(student, deadline)
    if "done" in payload:
        state.status = "done" if payload["done"] else "doing"
    if payload.get("status") in {"todo", "doing", "done"}:
        state.status = payload["status"]
    if payload.get("priority") in {"low", "normal", "high"}:
        state.priority = payload["priority"]
    if "note" in payload:
        state.note = str(payload["note"])[:2000]
    if "plannedStart" in payload or "plannedEnd" in payload:
        try:
            state.planned_start_at, state.planned_end_at = _schedule_payload(
                payload,
                state.planned_start_at,
                state.planned_end_at,
            )
        except ValidationError as exc:
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
    state.save()
    if state.status == "done":
        Notification.objects.filter(
            student=student,
            deadline=deadline,
            wechat_sent_at__isnull=True,
        ).delete()
    if "reminders" in payload:
        _replace_reminders(student, deadline=deadline, reminders=payload["reminders"])
    _sync_checkin(student)
    return JsonResponse(_deadline_data(deadline, student))


@require_http_methods(["POST"])
def api_personal_task(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    payload = _json_body(request)
    title = str(payload.get("title", "")).strip()
    due_at = _personal_task_due_at(payload)
    if not title or not due_at:
        return JsonResponse({"error": "任务标题和截止时间不能为空，或格式不正确。"}, status=400)
    task = PersonalTask.objects.create(
        student=student,
        title=title,
        due_at=due_at,
        note=str(payload.get("note", ""))[:2000],
    )
    if "plannedStart" in payload or "plannedEnd" in payload:
        try:
            task.planned_start_at, task.planned_end_at = _schedule_payload(payload)
        except ValidationError as exc:
            task.delete()
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        task.save(update_fields=["planned_start_at", "planned_end_at"])
    if "reminders" in payload:
        _replace_reminders(student, personal_task=task, reminders=payload["reminders"])
    _sync_checkin(student)
    return JsonResponse(_personal_task_data(task), status=201)


@require_http_methods(["PUT", "PATCH", "DELETE"])
def api_personal_task_detail(request, task_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    try:
        task = PersonalTask.objects.get(pk=task_id, student=student)
    except PersonalTask.DoesNotExist:
        return JsonResponse({"error": "个人待办不存在。"}, status=404)
    if request.method == "DELETE":
        previous_date = timezone.localtime(task.due_at, SHANGHAI_TZ).date()
        task.delete()
        _sync_checkin(student, previous_date)
        return JsonResponse({"ok": True})

    payload = _json_body(request)
    previous_date = timezone.localtime(task.due_at, SHANGHAI_TZ).date()
    title = str(payload.get("title", task.title)).strip()
    due_at = _personal_task_due_at(payload) if ("dueAt" in payload or "due" in payload) else task.due_at
    if not title or not due_at:
        return JsonResponse({"error": "任务标题和截止时间不能为空，或格式不正确。"}, status=400)
    task.title = title[:200]
    task.due_at = due_at
    if "note" in payload:
        task.note = str(payload["note"])[:2000]
    task.save(update_fields=["title", "due_at", "note"])
    if "plannedStart" in payload or "plannedEnd" in payload:
        try:
            task.planned_start_at, task.planned_end_at = _schedule_payload(
                payload,
                task.planned_start_at,
                task.planned_end_at,
            )
        except ValidationError as exc:
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        task.save(update_fields=["planned_start_at", "planned_end_at"])
    Notification.objects.filter(student=student, personal_task=task).delete()
    _sync_checkin(student, previous_date)
    _sync_checkin(student, timezone.localtime(task.due_at, SHANGHAI_TZ).date())
    return JsonResponse(_personal_task_data(task), status=200)


@require_http_methods(["POST"])
def api_personal_task_state(request, task_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    payload = _json_body(request)
    try:
        task = PersonalTask.objects.get(pk=task_id, student=student)
    except PersonalTask.DoesNotExist:
        return JsonResponse({"error": "个人待办不存在。"}, status=404)
    if "done" in payload:
        task.status = "done" if payload["done"] else "doing"
    if payload.get("status") in {"todo", "doing", "done"}:
        task.status = payload["status"]
    if payload.get("priority") in {"low", "normal", "high"}:
        task.priority = payload["priority"]
    if "note" in payload:
        task.note = str(payload["note"])[:2000]
    schedule_fields = []
    if "plannedStart" in payload or "plannedEnd" in payload:
        try:
            task.planned_start_at, task.planned_end_at = _schedule_payload(
                payload,
                task.planned_start_at,
                task.planned_end_at,
            )
        except ValidationError as exc:
            return JsonResponse({"error": "；".join(exc.messages)}, status=400)
        schedule_fields = ["planned_start_at", "planned_end_at"]
    task.save(update_fields=["status", "priority", "note", *schedule_fields])
    if task.status == "done":
        Notification.objects.filter(
            student=student,
            personal_task=task,
            read_at__isnull=True,
        ).delete()
    if "reminders" in payload:
        _replace_reminders(student, personal_task=task, reminders=payload["reminders"])
    _sync_checkin(student)
    return JsonResponse(_personal_task_data(task))


@require_http_methods(["GET"])
def api_notifications(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    sync_student_notifications(student)
    dispatch_student_wechat_notifications(student)
    task_notifications = list(Notification.objects.filter(student=student)[:50])
    chat_notifications = list(
        ChatNotification.objects.filter(student=student)
        .select_related("message__sender")
        .order_by("-created_at", "-id")[:50]
    )
    notification_data = [_notification_data(notification) for notification in task_notifications]
    notification_data.extend(
        _chat_notification_data(notification)
        for notification in chat_notifications
    )
    notification_data.sort(
        key=lambda item: (item["scheduledAt"]["date"], item["scheduledAt"]["time"], item["id"]),
        reverse=True,
    )
    notification_data = notification_data[:50]
    return JsonResponse({
        "notifications": notification_data,
        "unreadCount": sum(item["read"] is False for item in notification_data),
    })


@require_http_methods(["GET", "PATCH"])
def api_notification_settings(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    if request.method == "GET":
        return JsonResponse(_notification_settings_data(student))

    payload = _json_body(request)
    notification_settings, _ = StudentNotificationSettings.objects.get_or_create(student=student)
    if "due24hEnabled" in payload:
        notification_settings.due_24h_enabled = bool(payload["due24hEnabled"])
    if "wechatEnabled" in payload:
        notification_settings.wechat_enabled = bool(payload["wechatEnabled"])
    if (
        "wechatOpenid" in payload
        and django_settings.WECHAT_PUSH_MODE == "log"
    ):
        notification_settings.wechat_openid = str(payload["wechatOpenid"]).strip()[:128]
    notification_settings.save()
    if not notification_settings.due_24h_enabled:
        Notification.objects.filter(
            student=student,
            notification_type="due_24h",
            wechat_sent_at__isnull=True,
        ).delete()
    sync_student_notifications(student)
    dispatch_result = dispatch_student_wechat_notifications(student)
    return JsonResponse({
        **_notification_settings_data(student),
        "dispatch": dispatch_result,
    })


@require_http_methods(["POST"])
def api_wechat_test(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    notification_settings, _ = StudentNotificationSettings.objects.get_or_create(student=student)
    if not notification_settings.wechat_openid:
        return JsonResponse({"error": "请先绑定微信账号。"}, status=400)
    try:
        WeChatSender().send(
            openid=notification_settings.wechat_openid,
            title="DDL. 微信测试提醒",
            message="微信提醒通道已连通。你可以安心接收任务提醒。",
            scheduled_at=timezone.now(),
        )
    except WeChatDeliveryError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    return JsonResponse({"ok": True, "message": "测试消息已提交，请检查微信。"})


@require_http_methods(["GET"])
def api_wechat_bind_start(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    sender = WeChatSender()
    redirect_uri = (
        django_settings.WECHAT_OAUTH_REDIRECT_URL
        or request.build_absolute_uri("/api/wechat/bind/callback/")
    )
    state = signing.dumps({"student_id": student.id}, salt="wechat-bind")
    request.session["wechat_bind_state"] = state
    try:
        return redirect(sender.oauth_url(redirect_uri=redirect_uri, state=state))
    except WeChatDeliveryError as exc:
        return JsonResponse({"error": str(exc)}, status=503)


def _wechat_binding_result(status):
    query = urlencode({"wechat": status})
    return redirect(f"{django_settings.FRONTEND_URL}/?{query}")


@require_http_methods(["GET"])
def api_wechat_bind_callback(request):
    code = request.GET.get("code", "")
    state = request.GET.get("state", "")
    expected_state = request.session.pop("wechat_bind_state", "")
    if not code or not state or state != expected_state:
        return _wechat_binding_result("failed")
    try:
        payload = signing.loads(state, salt="wechat-bind", max_age=600)
        student = User.objects.get(pk=payload["student_id"])
        if not hasattr(student, "student_profile"):
            return _wechat_binding_result("failed")
        openid = WeChatSender().exchange_oauth_code(code)
    except (KeyError, User.DoesNotExist, signing.BadSignature, WeChatDeliveryError):
        return _wechat_binding_result("failed")

    notification_settings, _ = StudentNotificationSettings.objects.get_or_create(student=student)
    if StudentNotificationSettings.objects.filter(
        wechat_openid=openid,
    ).exclude(student=student).exists():
        return _wechat_binding_result("already_bound")
    notification_settings.wechat_openid = openid
    notification_settings.save(update_fields=["wechat_openid", "updated_at"])
    return _wechat_binding_result("bound")


@require_http_methods(["POST"])
def api_change_password(request):
    if not request.user.is_authenticated:
        return _auth_error()
    payload = _json_body(request)
    current_password = str(payload.get("currentPassword", ""))
    new_password = str(payload.get("newPassword", ""))
    if not request.user.check_password(current_password):
        return JsonResponse({"error": "当前密码不正确。"}, status=400)
    try:
        validate_password(new_password, request.user)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)
    return JsonResponse({"ok": True, "message": "密码已更新。"})


@require_http_methods(["POST"])
def api_password_reset_request(request):
    payload = _json_body(request)
    email = str(payload.get("email", "")).strip().lower()
    user = User.objects.filter(
        username=email,
        email__iexact=email,
        is_active=True,
    ).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = (
            f"{django_settings.FRONTEND_URL}/?reset=1"
            f"&uid={uid}&token={token}"
        )
        try:
            send_mail(
                subject="DDL. 密码重置",
                message=(
                    "你请求重置 DDL. 账号密码。\n\n"
                    f"请在 3 天内打开以下地址设置新密码：\n{reset_url}\n\n"
                    "如果不是你本人操作，请忽略此邮件。"
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("密码重置邮件发送失败 user_id=%s", user.id)
    # 无论邮箱是否存在都返回相同结果，避免泄露账号注册状态。
    return JsonResponse({"ok": True, "message": "如果该邮箱已注册，重置邮件将发送到你的邮箱。"})


@require_http_methods(["POST"])
def api_password_reset_confirm(request):
    payload = _json_body(request)
    uid = str(payload.get("uid", ""))
    token = str(payload.get("token", ""))
    new_password = str(payload.get("newPassword", ""))
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if not user or not default_token_generator.check_token(user, token):
        return JsonResponse({"error": "重置链接无效或已过期，请重新申请。"}, status=400)
    try:
        validate_password(new_password, user)
    except ValidationError as exc:
        return JsonResponse({"error": " ".join(exc.messages)}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return JsonResponse({"ok": True, "message": "密码已重置，请使用新密码登录。"})


@require_http_methods(["POST"])
def api_notifications_read(request):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    payload = _json_body(request)
    notifications = Notification.objects.filter(student=student, read_at__isnull=True)
    ids = payload.get("ids")
    chat_ids = payload.get("chatIds")
    if payload.get("all"):
        updated = notifications.update(read_at=timezone.now())
        updated += ChatNotification.objects.filter(
            student=student,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return JsonResponse({"updated": updated})
    elif isinstance(ids, list):
        target = notifications.filter(pk__in=ids)
        updated = target.update(read_at=timezone.now())
        if isinstance(chat_ids, list):
            updated += ChatNotification.objects.filter(
                student=student,
                pk__in=[
                    int(value) for value in chat_ids
                    if str(value).isdigit()
                ],
                read_at__isnull=True,
            ).update(read_at=timezone.now())
        return JsonResponse({"updated": updated})
    elif isinstance(chat_ids, list):
        updated = ChatNotification.objects.filter(
            student=student,
            pk__in=[
                int(value) for value in chat_ids
                if str(value).isdigit()
            ],
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return JsonResponse({"updated": updated})
    else:
        return JsonResponse({"error": "请选择要标记的通知。"}, status=400)


@require_http_methods(["POST"])
def api_subscription_toggle(request, class_id):
    student = _student_for_request(request)
    if not student:
        return _auth_error()
    try:
        class_group = ClassGroup.objects.select_related("course").get(pk=class_id)
    except ClassGroup.DoesNotExist:
        return JsonResponse({"error": "班级不存在。"}, status=404)
    current = ClassSubscription.objects.filter(student=student, class_group=class_group).first()
    if current:
        current.delete()
        return JsonResponse({"subscribed": False, "classId": class_group.id})
    if not class_group.course.is_active:
        return JsonResponse({"error": "该课程已结束，不能重新订阅。"}, status=409)
    if ClassSubscription.objects.filter(student=student, class_group__course=class_group.course).exists():
        return JsonResponse({"error": "同一门课程只能订阅一个班级，请先取消原班级。"}, status=409)
    try:
        with transaction.atomic():
            ClassSubscription.objects.create(student=student, class_group=class_group)
    except (IntegrityError, ValueError) as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return JsonResponse({"subscribed": True, "classId": class_group.id})


@require_http_methods(["POST"])
def api_register(request):
    payload = _json_body(request)
    username = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    name = str(payload.get("name", "")).strip()
    if not username or not password or not name:
        return JsonResponse({"error": "姓名、邮箱和密码不能为空。"}, status=400)
    try:
        validate_email(username)
    except ValidationError:
        return JsonResponse({"error": "请输入有效的邮箱地址。"}, status=400)
    password_error = _account_password_error(password)
    if password_error:
        return JsonResponse({"error": password_error}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "该邮箱已经注册。"}, status=409)
    school = School.objects.filter(pk=payload.get("schoolId")).first()
    term = Term.objects.filter(pk=payload.get("termId"), school=school).first() if school else None
    if not school or not term:
        return JsonResponse({"error": "请选择有效的学校和学期。"}, status=400)
    user = User.objects.create_user(username=username, email=username, password=password, first_name=name)
    StudentProfile.objects.create(user=user, school=school, term=term)
    login(request, user)
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def api_login(request):
    payload = _json_body(request)
    username = str(payload.get("email", "")).strip().lower()
    user = authenticate(request, username=username, password=payload.get("password", ""))
    if not user:
        return JsonResponse({"error": "邮箱或密码不正确。"}, status=401)
    if not hasattr(user, "student_profile"):
        return JsonResponse({"error": "该账号不是学生账号。"}, status=403)
    login(request, user)
    return JsonResponse({"ok": True, "role": "student"})


@require_http_methods(["POST"])
def api_teacher_register(request):
    payload = _json_body(request)
    username = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    name = str(payload.get("name", "")).strip()
    proof = str(payload.get("proof", "")).strip()[:2000]
    if not username or not password or not name:
        return JsonResponse({"error": "姓名、邮箱和密码不能为空。"}, status=400)
    try:
        validate_email(username)
    except ValidationError:
        return JsonResponse({"error": "请输入有效的邮箱地址。"}, status=400)
    password_error = _account_password_error(password)
    if password_error:
        return JsonResponse({"error": password_error}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "该邮箱已经注册。"}, status=409)
    school = School.objects.filter(pk=payload.get("schoolId")).first()
    if not school:
        return JsonResponse({"error": "请选择有效的学校。"}, status=400)
    user = User.objects.create_user(
        username=username,
        email=username,
        password=password,
        first_name=name,
    )
    TeacherApplication.objects.create(user=user, school=school, proof=proof)
    login(request, user)
    return JsonResponse({
        "ok": True,
        "role": "teacher",
        "status": "pending",
        "message": "教师申请已提交，请等待管理员审核。",
    }, status=201)


@require_http_methods(["POST"])
def api_teacher_login(request):
    payload = _json_body(request)
    username = str(payload.get("email", "")).strip().lower()
    user = authenticate(request, username=username, password=payload.get("password", ""))
    if not user:
        return JsonResponse({"error": "邮箱或密码不正确。"}, status=401)
    application = getattr(user, "teacher_application", None)
    if not application:
        return JsonResponse({"error": "该账号不是教师账号。"}, status=403)
    if application.status != "approved":
        return _teacher_auth_error_for_application(application)
    login(request, user)
    return JsonResponse({"ok": True, "role": "teacher"})


def _teacher_auth_error_for_application(application):
    if application.status == "pending":
        return JsonResponse({"error": "教师账号正在审核中，请等待管理员通过。"}, status=403)
    return JsonResponse({"error": "教师申请未通过，请联系管理员。"}, status=403)


@require_http_methods(["GET"])
def api_teacher_bootstrap(request):
    teacher = _teacher_for_request(request)
    if not teacher:
        return _teacher_auth_error(request)
    application = teacher.teacher_application
    school = application.school
    terms = list(school.terms.filter(is_active=True))
    courses = list(
        Course.objects.filter(school=school)
        .select_related("term", "created_by")
        .prefetch_related("classes")
    )
    owned_classes = list(
        ClassGroup.objects.filter(
            created_by=teacher,
            course__school=school,
        )
        .select_related("course")
    )
    deadlines = list(
        Deadline.objects.filter(
            created_by=teacher,
            class_group__created_by=teacher,
            class_group__course__school=school,
            is_active=True,
        )
        .select_related("class_group__course")
    )
    return JsonResponse({
        "teacher": {
            "name": teacher.get_full_name() or teacher.username,
            "email": teacher.email,
            "school": school.name,
            "applicationStatus": application.status,
        },
        "terms": [
            {
                "id": term.id,
                "name": term.name,
                "startDate": term.start_date.isoformat(),
                "endDate": term.end_date.isoformat(),
            }
            for term in terms
        ],
        "courses": [_teacher_course_data(course) for course in courses],
        "classes": [
            {
                "id": class_group.id,
                "name": class_group.name,
                "teacherName": class_group.teacher_name,
                "courseId": class_group.course_id,
                "courseName": class_group.course.name,
            }
            for class_group in owned_classes
        ],
        "deadlines": [_teacher_deadline_data(deadline) for deadline in deadlines],
    })


@require_http_methods(["POST"])
def api_teacher_class(request):
    teacher = _teacher_for_request(request)
    if not teacher:
        return _teacher_auth_error(request)
    payload = _json_body(request)
    name = str(payload.get("name", "")).strip()
    course_name = str(payload.get("courseName", "")).strip()
    course_id = payload.get("courseId")
    term_id = payload.get("termId")
    start_date = str(payload.get("startDate", "")).strip()
    end_date = str(payload.get("endDate", "")).strip()
    if not name or (not course_id and not course_name):
        return JsonResponse({"error": "请填写课程和班级名称。"}, status=400)
    school = teacher.teacher_application.school
    term = Term.objects.filter(pk=term_id, school=school).first() if term_id else None
    course = Course.objects.filter(pk=course_id, school=school).first() if course_id else None
    if course:
        term = course.term
        if not course.is_active:
            return JsonResponse({"error": "该课程已结束，请创建新学期课程。"}, status=409)
    elif course_name and term:
        course, _ = Course.objects.get_or_create(
            school=school,
            term=term,
            name=course_name,
            defaults={
                "created_by": teacher,
                "start_date": term.start_date,
                "end_date": term.end_date,
            },
        )
        if not course.start_date or not course.end_date:
            course.start_date = course.start_date or term.start_date
            course.end_date = course.end_date or term.end_date
            course.save(update_fields=["start_date", "end_date"])
        if start_date or end_date:
            try:
                parsed_start = datetime.fromisoformat(start_date).date() if start_date else course.start_date
                parsed_end = datetime.fromisoformat(end_date).date() if end_date else course.end_date
            except ValueError:
                return JsonResponse({"error": "课程起止日期格式不正确。"}, status=400)
            if parsed_end and parsed_start and parsed_end < parsed_start:
                return JsonResponse({"error": "课程结束日期不能早于开始日期。"}, status=400)
            course.start_date = parsed_start
            course.end_date = parsed_end
            course.save(update_fields=["start_date", "end_date"])
    else:
        return JsonResponse({"error": "请选择有效的学期或课程。"}, status=400)
    try:
        class_group = ClassGroup.objects.create(
            course=course,
            name=name,
            teacher_name=teacher.get_full_name() or teacher.username,
            created_by=teacher,
        )
    except IntegrityError:
        return JsonResponse({"error": "该课程下已经有同名班级。"}, status=409)
    return JsonResponse({
        "id": class_group.id,
        "name": class_group.name,
        "teacherName": class_group.teacher_name,
        "courseId": course.id,
        "courseName": course.name,
    }, status=201)


@require_http_methods(["POST"])
def api_teacher_course_end(request, course_id):
    teacher = _teacher_for_request(request)
    if not teacher:
        return _teacher_auth_error(request)
    course = Course.objects.filter(
        pk=course_id,
        school=teacher.teacher_application.school,
        created_by=teacher,
    ).first()
    if not course:
        return JsonResponse({"error": "找不到可结束的课程。"}, status=404)
    course.is_active = False
    course.save(update_fields=["is_active"])
    return JsonResponse(_teacher_course_data(course))


@require_http_methods(["POST"])
def api_teacher_deadline(request):
    teacher = _teacher_for_request(request)
    if not teacher:
        return _teacher_auth_error(request)
    payload = _json_body(request)
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()[:4000]
    class_id = payload.get("classId")
    due_at = _parse_reminder(payload.get("dueAt"))
    kind = payload.get("kind") if payload.get("kind") in {"formative", "summative"} else "formative"
    class_group = ClassGroup.objects.filter(
        pk=class_id,
        created_by=teacher,
        course__school=teacher.teacher_application.school,
    ).select_related("course").first()
    if not title or not due_at or not class_group:
        return JsonResponse({"error": "请填写标题、截止时间，并选择你创建的班级。"}, status=400)
    deadline = Deadline.objects.create(
        class_group=class_group,
        source_type="course",
        kind=kind,
        title=title,
        description=description,
        due_at=due_at,
        created_by=teacher,
    )
    return JsonResponse(_teacher_deadline_data(deadline), status=201)


@require_http_methods(["POST"])
def api_teacher_deadline_update(request, deadline_id):
    teacher = _teacher_for_request(request)
    if not teacher:
        return _teacher_auth_error(request)
    deadline = Deadline.objects.filter(
        pk=deadline_id,
        created_by=teacher,
        class_group__created_by=teacher,
    ).select_related("class_group__course").first()
    if not deadline:
        return JsonResponse({"error": "找不到可编辑的 DDL。"}, status=404)
    payload = _json_body(request)
    if "title" in payload and str(payload["title"]).strip():
        deadline.title = str(payload["title"]).strip()[:200]
    if "description" in payload:
        deadline.description = str(payload["description"]).strip()[:4000]
    if "kind" in payload and payload["kind"] in {"formative", "summative"}:
        deadline.kind = payload["kind"]
    if "dueAt" in payload:
        due_at = _parse_reminder(payload["dueAt"])
        if not due_at:
            return JsonResponse({"error": "截止时间格式不正确。"}, status=400)
        deadline.due_at = due_at
    deadline.save()
    # 教师改动官方任务后，学生不能继续收到旧标题或旧时间的未发送提醒。
    Notification.objects.filter(
        deadline=deadline,
        wechat_sent_at__isnull=True,
    ).delete()
    return JsonResponse(_teacher_deadline_data(deadline))


@require_http_methods(["POST"])
def api_logout(request):
    logout(request)
    return JsonResponse({"ok": True})
