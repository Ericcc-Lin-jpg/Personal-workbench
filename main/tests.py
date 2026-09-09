from datetime import datetime, time, timedelta
from io import BytesIO
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from PIL import Image
from django.contrib.auth import get_user_model
from django.core import signing
from django.core import mail
from django.test import Client, TestCase
from django.test import override_settings
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from .models import (
    AnnualPlanTask,
    ClassGroup,
    ClassSubscription,
    Checkin,
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
    Course,
    Deadline,
    Notification,
    PersonalTask,
    School,
    StudentFriendship,
    StudentProfile,
    StudentNotificationSettings,
    StudentDeadlineState,
    TaskReminder,
    TeacherApplication,
    Term,
)
from .consumers import ChatConsumer, ChatGroupConsumer


class CoreFlowTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="测试国际学校", code="test-school")
        self.term = Term.objects.create(
            school=self.school,
            name="2026 秋季学期",
            start_date="2026-08-25",
            end_date="2027-01-20",
        )
        self.student = get_user_model().objects.create_user(
            username="student@test.local",
            email="student@test.local",
            password="student-pass",
            first_name="测试学生",
        )
        StudentProfile.objects.create(user=self.student, school=self.school, term=self.term)

    def test_healthz_checks_database(self):
        response = self.client.get("/healthz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["timezone"], "Asia/Shanghai")

    def test_teacher_publication_syncs_to_subscribed_student(self):
        registration = self.client.post(
            "/api/auth/teacher-register/",
            data={
                "name": "测试教师",
                "email": "teacher@test.local",
                "password": "teacher-pass",
                "schoolId": self.school.id,
                "proof": "自动化测试申请",
            },
            content_type="application/json",
        )
        self.assertEqual(registration.status_code, 201)

        self.client.post("/api/auth/logout/")
        pending_login = self.client.post(
            "/api/auth/teacher-login/",
            data={"email": "teacher@test.local", "password": "teacher-pass"},
            content_type="application/json",
        )
        self.assertEqual(pending_login.status_code, 403)

        application = TeacherApplication.objects.get(user__username="teacher@test.local")
        application.status = "approved"
        application.save(update_fields=["status"])
        teacher_login = self.client.post(
            "/api/auth/teacher-login/",
            data={"email": "teacher@test.local", "password": "teacher-pass"},
            content_type="application/json",
        )
        self.assertEqual(teacher_login.status_code, 200)

        created_class = self.client.post(
            "/api/teacher/classes/",
            data={
                "courseName": "AP 微积分",
                "termId": self.term.id,
                "name": "A 班",
            },
            content_type="application/json",
        )
        self.assertEqual(created_class.status_code, 201)
        class_id = created_class.json()["id"]

        created_deadline = self.client.post(
            "/api/teacher/deadlines/",
            data={
                "classId": class_id,
                "title": "单元一作业",
                "description": "完成习题并上传。",
                "kind": "formative",
                "dueAt": "2026-09-15T20:00",
            },
            content_type="application/json",
        )
        self.assertEqual(created_deadline.status_code, 201)
        deadline_id = created_deadline.json()["id"]
        self.assertTrue(Deadline.objects.filter(pk=deadline_id).exists())
        updated_deadline = self.client.post(
            f"/api/teacher/deadlines/{deadline_id}/",
            data={
                "title": "单元一作业（已更新）",
                "description": "完成习题并上传最终版本。",
                "kind": "summative",
                "dueAt": "2026-09-16T20:00",
            },
            content_type="application/json",
        )
        self.assertEqual(updated_deadline.status_code, 200)
        self.assertEqual(updated_deadline.json()["title"], "单元一作业（已更新）")

        self.client.post("/api/auth/logout/")
        student_login = self.client.post(
            "/api/auth/login/",
            data={"email": "student@test.local", "password": "student-pass"},
            content_type="application/json",
        )
        self.assertEqual(student_login.status_code, 200)
        subscription = self.client.post(f"/api/subscriptions/{class_id}/toggle/")
        self.assertEqual(subscription.status_code, 200)

        bootstrap = self.client.get("/api/bootstrap/")
        self.assertEqual(bootstrap.status_code, 200)
        task = next(item for item in bootstrap.json()["tasks"] if item.get("deadlineId") == deadline_id)
        self.assertEqual(task["title"], "单元一作业（已更新）")
        self.assertEqual(task["sourceName"], "AP 微积分 · A 班")

        saved_state = self.client.post(
            f"/api/deadlines/{deadline_id}/state/",
            data={
                "status": "doing",
                "priority": "high",
                "note": "先完成这一项。",
                "reminders": ["2026-09-14T20:00", "2026-09-15T09:00"],
            },
            content_type="application/json",
        )
        self.assertEqual(saved_state.status_code, 200)
        self.assertEqual(saved_state.json()["status"], "doing")
        self.assertEqual(saved_state.json()["priority"], "high")
        self.assertEqual(len(saved_state.json()["reminders"]), 2)

        reloaded_task = next(
            item
            for item in self.client.get("/api/bootstrap/").json()["tasks"]
            if item.get("deadlineId") == deadline_id
        )
        self.assertEqual(reloaded_task["note"], "先完成这一项。")
        self.assertEqual(len(reloaded_task["reminders"]), 2)

    def test_student_can_only_subscribe_to_one_class_per_course(self):
        course = Course.objects.create(school=self.school, term=self.term, name="化学")
        class_a = ClassGroup.objects.create(course=course, name="A 班", teacher_name="老师甲")
        class_b = ClassGroup.objects.create(course=course, name="B 班", teacher_name="老师乙")
        self.client.login(username="student@test.local", password="student-pass")

        first = self.client.post(f"/api/subscriptions/{class_a.id}/toggle/")
        second = self.client.post(f"/api/subscriptions/{class_b.id}/toggle/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            ClassSubscription.objects.filter(student=self.student, class_group__course=course).count(),
            1,
        )
        cards = {
            item["classId"]: item
            for item in self.client.get("/api/bootstrap/").json()["subscriptions"]
        }
        self.assertTrue(cards[class_a.id]["courseSubscribed"])
        self.assertEqual(cards[class_a.id]["currentClassName"], "A 班")
        self.assertTrue(cards[class_b.id]["courseSubscribed"])
        self.assertFalse(cards[class_b.id]["subscribed"])

    def test_notifications_include_due_soon_and_custom_reminders(self):
        course = Course.objects.create(school=self.school, term=self.term, name="物理")
        class_group = ClassGroup.objects.create(course=course, name="A 班", teacher_name="老师甲")
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        deadline = Deadline.objects.create(
            class_group=class_group,
            title="实验报告",
            due_at=timezone.now() + timedelta(hours=8),
            created_by=self.student,
        )
        personal_task = PersonalTask.objects.create(
            student=self.student,
            title="复习笔记",
            due_at=timezone.now() + timedelta(hours=10),
        )
        TaskReminder.objects.create(
            student=self.student,
            personal_task=personal_task,
            remind_at=timezone.now() - timedelta(minutes=5),
        )
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unreadCount"], 3)
        self.assertEqual(Notification.objects.filter(student=self.student).count(), 3)
        notification_id = response.json()["notifications"][0]["id"]
        read_response = self.client.post(
            "/api/notifications/read/",
            data={"ids": [notification_id]},
            content_type="application/json",
        )
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["updated"], 1)
        self.assertTrue(Notification.objects.get(pk=notification_id).read_at)

    def test_personal_task_can_be_edited_with_custom_time_and_deleted(self):
        self.client.login(username="student@test.local", password="student-pass")
        created = self.client.post(
            "/api/personal-tasks/",
            data={
                "title": "初始待办",
                "dueAt": "2026-09-05T09:30",
                "note": "初始备注",
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["personalTaskId"]
        self.assertEqual(created.json()["time"], "09:30")

        updated = self.client.patch(
            f"/api/personal-tasks/{task_id}/",
            data={
                "title": "更新后的待办",
                "dueAt": "2026-09-06T18:45",
                "note": "更新备注",
            },
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "更新后的待办")
        self.assertEqual(updated.json()["time"], "18:45")

        deleted = self.client.delete(f"/api/personal-tasks/{task_id}/")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(PersonalTask.objects.filter(pk=task_id).exists())

    def test_tasks_can_save_personal_schedule_without_changing_official_due_time(self):
        course = Course.objects.create(school=self.school, term=self.term, name="计划时间课程")
        class_group = ClassGroup.objects.create(course=course, name="A 班", teacher_name="老师")
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        due_at = timezone.make_aware(
            datetime.combine(timezone.localdate(), time(hour=23, minute=30)),
        )
        deadline = Deadline.objects.create(
            class_group=class_group,
            title="官方作业",
            due_at=due_at,
            created_by=self.student,
        )
        self.client.login(username="student@test.local", password="student-pass")

        official = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T19:00",
                "plannedEnd": f"{timezone.localdate().isoformat()}T20:30",
            },
            content_type="application/json",
        )
        self.assertEqual(official.status_code, 200)
        self.assertEqual(official.json()["time"], "23:30")
        self.assertEqual(official.json()["plannedStart"]["time"], "19:00")
        self.assertEqual(official.json()["plannedEnd"]["time"], "20:30")
        self.assertEqual(Deadline.objects.get(pk=deadline.id).due_at, due_at)

        personal = self.client.post(
            "/api/personal-tasks/",
            data={
                "title": "个人复习",
                "dueAt": f"{timezone.localdate().isoformat()}T22:00",
                "plannedStart": f"{timezone.localdate().isoformat()}T20:30",
            },
            content_type="application/json",
        )
        self.assertEqual(personal.status_code, 201)
        self.assertEqual(personal.json()["scheduleType"], "point")
        self.assertEqual(personal.json()["plannedStart"]["time"], "20:30")

        scheduled_personal = self.client.post(
            f"/api/personal-tasks/{personal.json()['personalTaskId']}/state/",
            data={
                "plannedEnd": f"{timezone.localdate().isoformat()}T21:15",
            },
            content_type="application/json",
        )
        self.assertEqual(scheduled_personal.status_code, 200)
        self.assertEqual(scheduled_personal.json()["scheduleType"], "duration")
        self.assertEqual(scheduled_personal.json()["plannedStart"]["time"], "20:30")
        self.assertEqual(scheduled_personal.json()["plannedEnd"]["time"], "21:15")

        refreshed_personal = next(
            item
            for item in self.client.get("/api/bootstrap/").json()["tasks"]
            if item.get("personalTaskId") == personal.json()["personalTaskId"]
        )
        self.assertEqual(refreshed_personal["plannedStart"]["time"], "20:30")
        self.assertEqual(refreshed_personal["plannedEnd"]["time"], "21:15")

        cleared_personal = self.client.post(
            f"/api/personal-tasks/{personal.json()['personalTaskId']}/state/",
            data={"plannedStart": None, "plannedEnd": None},
            content_type="application/json",
        )
        self.assertEqual(cleared_personal.status_code, 200)
        self.assertEqual(cleared_personal.json()["scheduleType"], "unscheduled")
        self.assertIsNone(cleared_personal.json()["plannedStart"])
        self.assertIsNone(cleared_personal.json()["plannedEnd"])

        restored_personal = self.client.post(
            f"/api/personal-tasks/{personal.json()['personalTaskId']}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T20:30",
                "plannedEnd": f"{timezone.localdate().isoformat()}T21:15",
            },
            content_type="application/json",
        )
        self.assertEqual(restored_personal.status_code, 200)
        self.assertEqual(restored_personal.json()["scheduleType"], "duration")

        restored_to_point = self.client.post(
            f"/api/personal-tasks/{personal.json()['personalTaskId']}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T20:30",
                "plannedEnd": None,
            },
            content_type="application/json",
        )
        self.assertEqual(restored_to_point.status_code, 200)
        self.assertEqual(restored_to_point.json()["scheduleType"], "point")
        self.assertEqual(restored_to_point.json()["plannedStart"]["time"], "20:30")
        self.assertIsNone(restored_to_point.json()["plannedEnd"])

        off_grid = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T21:07",
            },
            content_type="application/json",
        )
        self.assertEqual(off_grid.status_code, 400)

        invalid = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T21:00",
                "plannedEnd": f"{timezone.localdate().isoformat()}T21:10",
            },
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)

        cross_day = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T23:45",
                "plannedEnd": f"{(timezone.localdate() + timedelta(days=1)).isoformat()}T00:15",
            },
            content_type="application/json",
        )
        self.assertEqual(cross_day.status_code, 400)

        end_of_day = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T23:45",
                "plannedEnd": f"{timezone.localdate().isoformat()}T24:00",
            },
            content_type="application/json",
        )
        self.assertEqual(end_of_day.status_code, 200)
        self.assertEqual(end_of_day.json()["scheduleType"], "duration")
        self.assertEqual(end_of_day.json()["plannedStart"]["time"], "23:45")
        self.assertEqual(end_of_day.json()["plannedEnd"]["time"], "24:00")

        end_of_day_with_offset = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={
                "plannedStart": f"{timezone.localdate().isoformat()}T23:45",
                "plannedEnd": f"{timezone.localdate().isoformat()}T24:00+08:00",
            },
            content_type="application/json",
        )
        self.assertEqual(end_of_day_with_offset.status_code, 200)
        self.assertEqual(end_of_day_with_offset.json()["plannedEnd"]["time"], "24:00")

        malformed = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={"plannedStart": "not-a-date"},
            content_type="application/json",
        )
        self.assertEqual(malformed.status_code, 400)

    def test_course_end_keeps_existing_subscription_but_blocks_new_subscription(self):
        teacher = get_user_model().objects.create_user(
            username="lifecycle-teacher@test.local",
            email="lifecycle-teacher@test.local",
            password="teacher-pass",
            first_name="课程老师",
        )
        application = TeacherApplication.objects.create(
            user=teacher,
            school=self.school,
            status="approved",
        )
        course = Course.objects.create(
            school=self.school,
            term=self.term,
            name="历史课程",
            created_by=teacher,
            start_date="2026-08-25",
            end_date="2026-09-01",
        )
        class_group = ClassGroup.objects.create(
            course=course,
            name="A 班",
            teacher_name="课程老师",
            created_by=teacher,
        )
        deadline = Deadline.objects.create(
            class_group=class_group,
            title="历史课程作业",
            due_at="2026-09-10T20:00+08:00",
            created_by=teacher,
        )
        ClassSubscription.objects.create(student=self.student, class_group=class_group)

        self.client.login(username="lifecycle-teacher@test.local", password="teacher-pass")
        end_response = self.client.post(f"/api/teacher/courses/{course.id}/end/")
        self.assertEqual(end_response.status_code, 200)
        self.assertEqual(end_response.json()["status"], "ended")

        self.client.logout()
        self.client.login(username="student@test.local", password="student-pass")
        bootstrap = self.client.get("/api/bootstrap/").json()
        task_ids = {item.get("deadlineId") for item in bootstrap["tasks"]}
        self.assertIn(deadline.id, task_ids)

        ClassSubscription.objects.filter(student=self.student, class_group=class_group).delete()
        blocked = self.client.post(f"/api/subscriptions/{class_group.id}/toggle/")
        self.assertEqual(blocked.status_code, 409)

    def test_wechat_notification_setting_dispatches_once_in_development_mode(self):
        course = Course.objects.create(school=self.school, term=self.term, name="英语")
        class_group = ClassGroup.objects.create(course=course, name="A 班", teacher_name="老师甲")
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        Deadline.objects.create(
            class_group=class_group,
            title="英语演讲",
            due_at=timezone.now() + timedelta(hours=6),
            created_by=self.student,
        )
        self.client.login(username="student@test.local", password="student-pass")

        settings_response = self.client.patch(
            "/api/notification-settings/",
            data={
                "wechatEnabled": True,
                "wechatOpenid": "openid-for-test",
            },
            content_type="application/json",
        )
        self.assertEqual(settings_response.status_code, 200)
        self.assertEqual(settings_response.json()["dispatch"]["sent"], 1)
        self.assertTrue(
            StudentNotificationSettings.objects.get(student=self.student).wechat_enabled
        )
        notification = Notification.objects.get(student=self.student)
        self.assertIsNotNone(notification.wechat_sent_at)

        second = self.client.get("/api/notifications/")
        self.assertEqual(second.status_code, 200)
        self.assertFalse(
            Notification.objects.filter(
                student=self.student,
                wechat_sent_at__isnull=True,
            ).exists()
        )

    def test_authenticated_user_can_change_password(self):
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.post(
            "/api/auth/password/",
            data={
                "currentPassword": "student-pass",
                "newPassword": "NewSecurePassword2026!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.client.logout()
        self.assertTrue(
            self.client.login(
                username="student@test.local",
                password="NewSecurePassword2026!",
            )
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_email_can_reset_password_once(self):
        response = self.client.post(
            "/api/auth/password/reset/",
            data={"email": "student@test.local"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        uid = urlsafe_base64_encode(force_bytes(self.student.pk))
        token = default_token_generator.make_token(self.student)
        confirm = self.client.post(
            "/api/auth/password/reset/confirm/",
            data={
                "uid": uid,
                "token": token,
                "newPassword": "ResetSecurePassword2026!",
            },
            content_type="application/json",
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertTrue(self.client.login(
            username="student@test.local",
            password="ResetSecurePassword2026!",
        ))

        reused = self.client.post(
            "/api/auth/password/reset/confirm/",
            data={
                "uid": uid,
                "token": token,
                "newPassword": "AnotherSecurePassword2026!",
            },
            content_type="application/json",
        )
        self.assertEqual(reused.status_code, 400)

    @override_settings(SHOW_DEMO_ACCOUNTS=False)
    def test_production_options_do_not_expose_demo_accounts(self):
        response = self.client.get("/api/options/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["demo"])
        self.assertIsNone(response.json()["teacherDemo"])

    def test_disabling_due_reminders_cancels_unsent_notifications(self):
        personal_task = PersonalTask.objects.create(
            student=self.student,
            title="即将截止",
            due_at=timezone.now() + timedelta(hours=6),
        )
        self.client.login(username="student@test.local", password="student-pass")
        self.client.get("/api/notifications/")
        self.assertTrue(Notification.objects.filter(
            student=self.student,
            personal_task=personal_task,
            notification_type="due_24h",
        ).exists())

        response = self.client.patch(
            "/api/notification-settings/",
            data={"due24hEnabled": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notification.objects.filter(
            student=self.student,
            personal_task=personal_task,
            notification_type="due_24h",
            wechat_sent_at__isnull=True,
        ).exists())

    def test_completing_task_cancels_unsent_wechat_notification(self):
        personal_task = PersonalTask.objects.create(
            student=self.student,
            title="完成后不应提醒",
            due_at=timezone.now() + timedelta(hours=6),
        )
        self.client.login(username="student@test.local", password="student-pass")
        self.client.get("/api/notifications/")
        response = self.client.post(
            f"/api/personal-tasks/{personal_task.id}/state/",
            data={"status": "done"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notification.objects.filter(
            student=self.student,
            personal_task=personal_task,
            wechat_sent_at__isnull=True,
        ).exists())

    def test_write_api_requires_csrf_token(self):
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.login(username="student@test.local", password="student-pass")

        rejected = secure_client.post(
            "/api/personal-tasks/",
            data={"title": "CSRF 测试", "dueAt": "2026-09-02T18:00"},
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)

        secure_client.get("/api/options/")
        token = secure_client.cookies["csrftoken"].value
        accepted = secure_client.post(
            "/api/personal-tasks/",
            data={"title": "CSRF 测试", "dueAt": "2026-09-02T18:00"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, 201)

    @override_settings(
        WECHAT_PUSH_MODE="official_account",
        WECHAT_OFFICIAL_ACCOUNT_APP_ID="wx-test",
        WECHAT_OFFICIAL_ACCOUNT_APP_SECRET="test-secret",
        WECHAT_TEMPLATE_ID="template-test",
    )
    def test_wechat_oauth_binding_saves_openid_server_side(self):
        self.client.login(username="student@test.local", password="student-pass")
        with patch(
            "main.views.WeChatSender.oauth_url",
            return_value="https://wechat.example.test/authorize",
        ) as oauth_url:
            start = self.client.get("/api/wechat/bind/start/")
        self.assertEqual(start.status_code, 302)
        self.assertEqual(start["Location"], "https://wechat.example.test/authorize")
        state = oauth_url.call_args.kwargs["state"]
        self.assertEqual(
            signing.loads(state, salt="wechat-bind", max_age=600)["student_id"],
            self.student.id,
        )

        with patch(
            "main.views.WeChatSender.exchange_oauth_code",
            return_value="openid-bound-by-oauth",
        ):
            callback = self.client.get(
                "/api/wechat/bind/callback/",
                {"code": "wechat-code", "state": state},
            )
        self.assertEqual(callback.status_code, 302)
        self.assertIn("wechat=bound", callback["Location"])
        self.assertEqual(
            StudentNotificationSettings.objects.get(student=self.student).wechat_openid,
            "openid-bound-by-oauth",
        )

    @override_settings(
        WECHAT_PUSH_MODE="official_account",
        WECHAT_OFFICIAL_ACCOUNT_APP_ID="wx-test",
        WECHAT_OFFICIAL_ACCOUNT_APP_SECRET="test-secret",
        WECHAT_TEMPLATE_ID="template-test",
    )
    def test_wechat_oauth_cannot_bind_openid_to_two_students(self):
        other = get_user_model().objects.create_user(
            username="other-wechat@test.local",
            email="other-wechat@test.local",
            password="other-pass",
            first_name="另一个学生",
        )
        StudentProfile.objects.create(user=other, school=self.school, term=self.term)
        StudentNotificationSettings.objects.create(
            student=other,
            wechat_openid="openid-already-bound",
        )
        self.client.login(username="student@test.local", password="student-pass")
        with patch(
            "main.views.WeChatSender.oauth_url",
            return_value="https://wechat.example.test/authorize",
        ) as oauth_url:
            self.client.get("/api/wechat/bind/start/")
        state = oauth_url.call_args.kwargs["state"]
        with patch(
            "main.views.WeChatSender.exchange_oauth_code",
            return_value="openid-already-bound",
        ):
            callback = self.client.get(
                "/api/wechat/bind/callback/",
                {"code": "wechat-code", "state": state},
            )
        self.assertIn("wechat=already_bound", callback["Location"])
        self.assertFalse(
            StudentNotificationSettings.objects.get(student=self.student).wechat_openid
        )

    def test_bound_student_can_send_wechat_test_message_in_log_mode(self):
        StudentNotificationSettings.objects.create(
            student=self.student,
            wechat_enabled=True,
            wechat_openid="openid-for-test",
        )
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.post("/api/wechat/test/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_wechat_test_requires_binding(self):
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.post("/api/wechat/test/")

        self.assertEqual(response.status_code, 400)

    def _create_today_course_deadline(self, title, *, done=False):
        course = Course.objects.create(
            school=self.school,
            term=self.term,
            name=f"课程-{title}",
        )
        class_group = ClassGroup.objects.create(
            course=course,
            name="A班",
            teacher_name="老师",
        )
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        due_at = timezone.make_aware(
            datetime.combine(timezone.localdate(), time(hour=20)),
        )
        deadline = Deadline.objects.create(
            class_group=class_group,
            title=title,
            due_at=due_at,
            created_by=self.student,
        )
        if done:
            StudentDeadlineState.objects.create(
                student=self.student,
                deadline=deadline,
                status="done",
            )
        return deadline

    def test_dashboard_empty_day_is_zero_percent_without_checkin(self):
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["today"]["percent"], 0)
        self.assertFalse(response.json()["checkin"]["checkedIn"])
        self.assertFalse(Checkin.objects.filter(student=self.student).exists())

    def test_dashboard_creates_one_checkin_when_all_today_tasks_are_done(self):
        self._create_today_course_deadline("已完成作业", done=True)
        PersonalTask.objects.create(
            student=self.student,
            title="个人复习",
            due_at=timezone.make_aware(
                datetime.combine(timezone.localdate(), time(hour=21)),
            ),
            status="done",
        )
        self.client.login(username="student@test.local", password="student-pass")

        first = self.client.get("/api/dashboard/")
        second = self.client.get("/api/dashboard/")

        self.assertEqual(first.json()["today"]["percent"], 100)
        self.assertTrue(first.json()["checkin"]["checkedIn"])
        self.assertEqual(second.json()["checkin"]["streak"], 1)
        self.assertEqual(Checkin.objects.filter(student=self.student).count(), 1)
        self.assertEqual(
            first.json()["checkin"]["completedAt"],
            second.json()["checkin"]["completedAt"],
        )

    def test_unchecking_today_task_removes_checkin_and_recalculates_progress(self):
        deadline = self._create_today_course_deadline("需要重新完成", done=True)
        self.client.login(username="student@test.local", password="student-pass")
        self.client.get("/api/dashboard/")
        self.assertTrue(Checkin.objects.filter(student=self.student).exists())

        response = self.client.post(
            f"/api/deadlines/{deadline.id}/state/",
            data={"done": False},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        dashboard = self.client.get("/api/dashboard/").json()
        self.assertEqual(dashboard["today"]["percent"], 0)
        self.assertFalse(dashboard["checkin"]["checkedIn"])
        self.assertFalse(Checkin.objects.filter(student=self.student).exists())

    def test_moving_completed_personal_task_recalculates_both_dates(self):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        task = PersonalTask.objects.create(
            student=self.student,
            title="移动后的待办",
            due_at=timezone.make_aware(datetime.combine(today, time(hour=20))),
            status="done",
        )
        self.client.login(username="student@test.local", password="student-pass")
        self.client.get("/api/dashboard/")
        self.assertTrue(Checkin.objects.filter(student=self.student, date=today).exists())

        response = self.client.patch(
            f"/api/personal-tasks/{task.id}/",
            data={
                "title": task.title,
                "dueAt": f"{tomorrow.isoformat()}T20:00",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Checkin.objects.filter(student=self.student, date=today).exists())
        self.assertFalse(Checkin.objects.filter(student=self.student, date=tomorrow).exists())

    def test_dashboard_uses_monday_to_sunday_for_week_tasks(self):
        course = Course.objects.create(
            school=self.school,
            term=self.term,
            name="周视图课程",
        )
        class_group = ClassGroup.objects.create(
            course=course,
            name="A班",
            teacher_name="老师",
        )
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        Deadline.objects.create(
            class_group=class_group,
            title="本周任务",
            due_at=timezone.make_aware(
                datetime.combine(monday, time(hour=12)),
            ),
            created_by=self.student,
        )
        self.client.login(username="student@test.local", password="student-pass")

        week = self.client.get("/api/dashboard/").json()["week"]

        self.assertEqual(week["start"], monday.isoformat())
        self.assertEqual(week["end"], (monday + timedelta(days=6)).isoformat())
        self.assertEqual(week["total"], 1)

    def test_dashboard_separates_personal_tasks_from_weekly_official_tasks(self):
        self._create_today_course_deadline("官方今日任务")
        PersonalTask.objects.create(
            student=self.student,
            title="个人今日任务",
            due_at=timezone.make_aware(
                datetime.combine(timezone.localdate(), time(hour=18)),
            ),
        )
        self.client.login(username="student@test.local", password="student-pass")

        data = self.client.get("/api/dashboard/").json()

        self.assertEqual(data["today"]["total"], 2)
        self.assertEqual(len(data["today"]["tasks"]), 2)
        self.assertEqual(data["week"]["total"], 1)
        self.assertEqual(data["week"]["tasks"][0]["kind"], "formative")

    def test_dashboard_returns_normal_urgent_expired_and_completed_levels(self):
        course = Course.objects.create(school=self.school, term=self.term, name="紧迫度课程")
        class_group = ClassGroup.objects.create(course=course, name="A班", teacher_name="老师")
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        now = timezone.now()
        entries = [
            ("普通", now + timedelta(hours=48), "normal"),
            ("紧急", now + timedelta(hours=6), "urgent"),
            ("过期", now - timedelta(hours=1), "expired"),
            ("完成", now + timedelta(hours=48), "completed"),
        ]
        for title, due_at, expected in entries:
            deadline = Deadline.objects.create(
                class_group=class_group,
                title=title,
                due_at=due_at,
                created_by=self.student,
            )
            if expected == "completed":
                StudentDeadlineState.objects.create(
                    student=self.student,
                    deadline=deadline,
                    status="done",
                )
        self.client.login(username="student@test.local", password="student-pass")

        tasks = {
            item["title"]: item["level"]
            for item in self.client.get("/api/bootstrap/").json()["tasks"]
        }

        self.assertEqual(tasks, {title: expected for title, _, expected in entries})

    def test_student_can_update_and_read_dashboard_motto(self):
        self.client.login(username="student@test.local", password="student-pass")

        update = self.client.patch(
            "/api/student-profile/",
            data={"motto": "先完成最重要的一件事"},
            content_type="application/json",
        )
        dashboard = self.client.get("/api/dashboard/")

        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["motto"], "先完成最重要的一件事")
        self.assertEqual(
            dashboard.json()["identity"]["motto"],
            "先完成最重要的一件事",
        )

    def test_student_can_manage_private_annual_plan_and_subtasks(self):
        self.client.login(username="student@test.local", password="student-pass")

        created = self.client.post(
            "/api/annual-plan/",
            data={
                "category": "application",
                "type": "period",
                "title": "牛剑申请季",
                "startDate": "2026-06-01",
                "endDate": "2026-09-30",
                "description": "完成选校、文书和申请提交。",
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["id"]
        self.assertEqual(created.json()["status"], "in_progress")

        edited_task = self.client.patch(
            f"/api/annual-plan/{task_id}/",
            data={
                "startDate": "2026-07-01",
                "endDate": "2026-11-20",
            },
            content_type="application/json",
        )
        self.assertEqual(edited_task.status_code, 200)
        self.assertEqual(edited_task.json()["startDate"], "2026-07-01")
        self.assertEqual(edited_task.json()["endDate"], "2026-11-20")

        added_subtask = self.client.post(
            f"/api/annual-plan/{task_id}/subtasks/",
            data={"title": "完成个人陈述初稿", "dueDate": "2026-08-15"},
            content_type="application/json",
        )
        self.assertEqual(added_subtask.status_code, 201)
        subtask_id = added_subtask.json()["subtasks"][0]["id"]

        completed = self.client.patch(
            f"/api/annual-plan/{task_id}/subtasks/{subtask_id}/",
            data={"completed": True},
            content_type="application/json",
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["subtaskCompleted"], 1)
        self.assertEqual(completed.json()["subtaskTotal"], 1)

        edited_subtask = self.client.patch(
            f"/api/annual-plan/{task_id}/subtasks/{subtask_id}/",
            data={"title": "完成个人陈述终稿", "dueDate": "2026-08-20"},
            content_type="application/json",
        )
        self.assertEqual(edited_subtask.status_code, 200)
        self.assertEqual(edited_subtask.json()["subtasks"][0]["title"], "完成个人陈述终稿")

        deleted_subtask = self.client.delete(
            f"/api/annual-plan/{task_id}/subtasks/{subtask_id}/",
        )
        self.assertEqual(deleted_subtask.status_code, 200)
        self.assertEqual(deleted_subtask.json()["subtaskTotal"], 0)

        node = self.client.post(
            "/api/annual-plan/",
            data={
                "category": "competition",
                "type": "node",
                "title": "AMC 12 报名截止",
                "nodeDate": "2026-09-20",
            },
            content_type="application/json",
        )
        self.assertEqual(node.status_code, 201)
        self.assertEqual(node.json()["type"], "node")

        plan = self.client.get("/api/annual-plan/?year=2026")
        self.assertEqual(plan.status_code, 200)
        self.assertEqual(plan.json()["summary"]["total"], 2)
        self.assertEqual(plan.json()["tasks"][0]["title"], "牛剑申请季")

        deleted = self.client.delete(f"/api/annual-plan/{task_id}/")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(AnnualPlanTask.objects.filter(pk=task_id).exists())

    def test_annual_plan_is_private_to_each_student(self):
        other_student = get_user_model().objects.create_user(
            username="other@test.local",
            email="other@test.local",
            password="other-pass",
        )
        StudentProfile.objects.create(
            user=other_student,
            school=self.school,
            term=self.term,
        )
        private_task = AnnualPlanTask.objects.create(
            student=other_student,
            category="personal",
            task_type="node",
            title="另一个学生的计划",
            node_date="2026-10-01",
        )
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.patch(
            f"/api/annual-plan/{private_task.id}/",
            data={"title": "不应被修改"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        private_task.refresh_from_db()
        self.assertEqual(private_task.title, "另一个学生的计划")

    def test_student_friend_request_lifecycle(self):
        other_student = get_user_model().objects.create_user(
            username="friend@test.local",
            email="friend@test.local",
            password="friend-pass",
            first_name="好友同学",
        )
        StudentProfile.objects.create(
            user=other_student,
            school=self.school,
            term=self.term,
            grade="G11",
            motto="一起准备申请季",
        )
        self.client.login(username="student@test.local", password="student-pass")

        discovered = self.client.get("/api/friends/")
        self.assertEqual(discovered.status_code, 200)
        friend_data = next(item for item in discovered.json()["users"] if item["id"] == other_student.id)
        self.assertEqual(friend_data["status"], "not_friend")

        requested = self.client.post(f"/api/friends/{other_student.id}/request/")
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(requested.json()["user"]["status"], "pending_sent")
        self.assertEqual(StudentFriendship.objects.count(), 1)

        self.client.logout()
        self.client.login(username="friend@test.local", password="friend-pass")
        incoming = self.client.get("/api/friends/")
        self.assertEqual(incoming.status_code, 200)
        incoming_data = next(item for item in incoming.json()["users"] if item["id"] == self.student.id)
        self.assertEqual(incoming_data["status"], "pending_received")

        accepted = self.client.post(f"/api/friends/{self.student.id}/accept/")
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["user"]["status"], "friend")

        self.client.logout()
        self.client.login(username="student@test.local", password="student-pass")
        duplicate = self.client.post(f"/api/friends/{other_student.id}/request/")
        self.assertEqual(duplicate.status_code, 400)
        deleted = self.client.post(f"/api/friends/{other_student.id}/delete/")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(StudentFriendship.objects.exists())

    def _create_chat_friend(self, *, first_name="聊天好友", username="chat-friend@test.local"):
        other = get_user_model().objects.create_user(
            username=username,
            email=username,
            password="friend-pass",
            first_name=first_name,
        )
        StudentProfile.objects.create(user=other, school=self.school, term=self.term)
        user_a, user_b = (
            (self.student, other)
            if self.student.id < other.id
            else (other, self.student)
        )
        StudentFriendship.objects.create(
            user_a=user_a,
            user_b=user_b,
            requested_by=self.student,
            status="accepted",
        )
        return other

    def _chat_image_upload(self, name, image_format, content_type):
        data = BytesIO()
        Image.new("RGB", (4, 4), "#6e8cba").save(data, format=image_format)
        return SimpleUploadedFile(name, data.getvalue(), content_type=content_type)

    def test_chat_requires_accepted_friendship(self):
        other = get_user_model().objects.create_user(
            username="not-friend-chat@test.local",
            email="not-friend-chat@test.local",
            password="friend-pass",
            first_name="非好友",
        )
        StudentProfile.objects.create(user=other, school=self.school, term=self.term)
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "你好"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ChatConversation.objects.exists())

    def test_friend_can_send_message_and_conversation_is_reused(self):
        other = self._create_chat_friend()
        self.client.login(username="student@test.local", password="student-pass")

        first = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "一起复习吗？"},
            content_type="application/json",
        )
        second = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "可以，晚上八点。"},
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(ChatConversation.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 2)
        self.assertEqual(second.json()["peer"]["lastMessage"], "可以，晚上八点。")

    def test_chat_list_shows_unread_and_opening_chat_marks_messages_read(self):
        other = self._create_chat_friend(
            first_name="发消息的人",
            username="chat-sender@test.local",
        )
        user_a, user_b = (
            (self.student, other)
            if self.student.id < other.id
            else (other, self.student)
        )
        conversation = ChatConversation.objects.create(user_a=user_a, user_b=user_b)
        message = ChatMessage.objects.create(
            conversation=conversation,
            sender=other,
            content="记得看申请材料。",
        )
        self.client.login(username="student@test.local", password="student-pass")

        chat_list = self.client.get("/api/chats/")
        self.assertEqual(chat_list.status_code, 200)
        chat = next(item for item in chat_list.json()["chats"] if item["id"] == other.id)
        self.assertEqual(chat["unread"], 1)
        self.assertEqual(chat_list.json()["unread"], 1)

        opened = self.client.get(f"/api/chats/{other.id}/messages/")
        self.assertEqual(opened.status_code, 200)
        self.assertTrue(opened.json()["messages"][0]["read"])
        message.refresh_from_db()
        self.assertIsNotNone(message.read_at)

        refreshed = self.client.get("/api/chats/").json()
        chat = next(item for item in refreshed["chats"] if item["id"] == other.id)
        self.assertEqual(chat["unread"], 0)

    def test_chat_message_appears_in_unified_notifications_and_can_be_read(self):
        other = self._create_chat_friend(username="chat-notification@test.local")
        sender = Client()
        sender.login(username="chat-notification@test.local", password="friend-pass")
        sent = sender.post(
            f"/api/chats/{self.student.id}/messages/",
            data={"content": "记得看一下申请材料。"},
            content_type="application/json",
        )
        self.assertEqual(sent.status_code, 201)
        notification = ChatNotification.objects.get(student=self.student)

        self.client.login(username="student@test.local", password="student-pass")
        listed = self.client.get("/api/notifications/")
        self.assertEqual(listed.status_code, 200)
        chat_item = next(
            item for item in listed.json()["notifications"]
            if item["id"] == f"chat-{notification.id}"
        )
        self.assertEqual(chat_item["kind"], "chat")
        self.assertFalse(chat_item["read"])
        self.assertEqual(chat_item["chatId"], other.id)

        marked = self.client.post(
            "/api/notifications/read/",
            data={"chatIds": [notification.id]},
            content_type="application/json",
        )
        self.assertEqual(marked.status_code, 200)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_chat_rejects_empty_and_oversized_messages(self):
        other = self._create_chat_friend(username="chat-validation@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        empty = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "   "},
            content_type="application/json",
        )
        oversized = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "x" * 2001},
            content_type="application/json",
        )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(oversized.status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_friend_can_send_image_only_message(self):
        other = self._create_chat_friend(username="chat-image-only@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        image = self._chat_image_upload("study.png", "PNG", "image/png")
        response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"image": image},
        )

        self.assertEqual(response.status_code, 201)
        message = ChatMessage.objects.get()
        self.assertEqual(message.content, "")
        self.assertTrue(message.image.name.startswith("chat_images/"))
        self.assertTrue(response.json()["message"]["imageUrl"])
        self.assertEqual(response.json()["peer"]["lastMessage"], "图片")

    def test_friend_can_send_image_with_text(self):
        other = self._create_chat_friend(username="chat-image-text@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        image = self._chat_image_upload("schedule.jpg", "JPEG", "image/jpeg")
        response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "这是我的复习安排。", "image": image},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"]["content"], "这是我的复习安排。")
        self.assertEqual(ChatMessage.objects.get().content, "这是我的复习安排。")

    def test_friend_can_send_document_or_audio_attachment(self):
        other = self._create_chat_friend(username="chat-attachment@test.local")
        self.client.login(username="student@test.local", password="student-pass")
        document = SimpleUploadedFile(
            "application.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "申请材料", "attachment": document},
        )

        self.assertEqual(response.status_code, 201)
        attachment = response.json()["message"]["attachment"]
        self.assertTrue(attachment["name"].endswith(".pdf"))
        self.assertEqual(response.json()["peer"]["lastMessage"], "申请材料")

        audio = SimpleUploadedFile(
            "voice.m4a",
            b"\x00\x00\x00\x18ftypM4A audio-content",
            content_type="audio/mp4",
        )
        audio_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"attachment": audio},
        )
        self.assertEqual(audio_response.status_code, 201, audio_response.content.decode())
        self.assertTrue(audio_response.json()["message"]["attachment"]["name"].endswith(".m4a"))

        recording = SimpleUploadedFile(
            "voice.webm",
            b"\x1a\x45\xdf\xa3recorded-audio-content",
            content_type="audio/webm",
        )
        recording_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"attachment": recording},
        )
        self.assertEqual(recording_response.status_code, 201, recording_response.content.decode())
        self.assertTrue(recording_response.json()["message"]["attachment"]["name"].endswith(".webm"))

    def test_chat_rejects_invalid_attachment_and_two_uploaded_files(self):
        other = self._create_chat_friend(username="chat-attachment-validation@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        invalid = SimpleUploadedFile(
            "script.exe",
            b"executable",
            content_type="application/octet-stream",
        )
        invalid_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"attachment": invalid},
        )
        self.assertEqual(invalid_response.status_code, 400)

        image = SimpleUploadedFile(
            "one.png",
            b"\x89PNG\r\n\x1a\n",
            content_type="image/png",
        )
        document = SimpleUploadedFile(
            "two.pdf",
            b"%PDF-1.4",
            content_type="application/pdf",
        )
        both_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"image": image, "attachment": document},
        )
        self.assertEqual(both_response.status_code, 400)

    def test_chat_rejects_unsupported_or_oversized_images(self):
        other = self._create_chat_friend(username="chat-image-validation@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        unsupported = SimpleUploadedFile(
            "notes.pdf",
            b"pdf-content",
            content_type="application/pdf",
        )
        unsupported_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"image": unsupported},
        )
        self.assertEqual(unsupported_response.status_code, 400)

        oversized = SimpleUploadedFile(
            "large.png",
            b"x" * (10 * 1024 * 1024 + 1),
            content_type="image/png",
        )
        oversized_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"image": oversized},
        )
        self.assertEqual(oversized_response.status_code, 400)
        self.assertFalse(ChatMessage.objects.exists())

    def test_friend_can_share_owned_personal_task_or_subscribed_deadline(self):
        other = self._create_chat_friend(username="chat-task-card@test.local")
        course = Course.objects.create(school=self.school, term=self.term, name="卡片课程")
        class_group = ClassGroup.objects.create(course=course, name="A 班", teacher_name="老师")
        ClassSubscription.objects.create(student=self.student, class_group=class_group)
        deadline = Deadline.objects.create(
            class_group=class_group,
            title="卡片官方 DDL",
            due_at=timezone.now() + timedelta(days=2),
            created_by=self.student,
        )
        personal_task = PersonalTask.objects.create(
            student=self.student,
            title="我的卡片待办",
            due_at=timezone.now() + timedelta(days=1),
        )
        self.client.login(username="student@test.local", password="student-pass")

        deadline_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"shareType": "deadline", "shareId": str(deadline.id)},
            content_type="application/json",
        )
        personal_response = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"shareType": "personal", "shareId": str(personal_task.id)},
            content_type="application/json",
        )

        self.assertEqual(deadline_response.status_code, 201)
        self.assertEqual(personal_response.status_code, 201)
        self.assertEqual(deadline_response.json()["peer"]["lastMessage"], "任务")
        self.assertEqual(deadline_response.json()["message"]["taskCard"]["type"], "deadline")
        self.assertEqual(personal_response.json()["message"]["taskCard"]["type"], "personal")

        other_task = PersonalTask.objects.create(
            student=other,
            title="不能分享的待办",
            due_at=timezone.now() + timedelta(days=1),
        )
        forbidden = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"shareType": "personal", "shareId": str(other_task.id)},
            content_type="application/json",
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_deleting_friend_blocks_existing_chat(self):
        other = self._create_chat_friend(username="chat-delete@test.local")
        self.client.login(username="student@test.local", password="student-pass")
        sent = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "先留在这里。"},
            content_type="application/json",
        )
        self.assertEqual(sent.status_code, 201)

        deleted = self.client.post(f"/api/friends/{other.id}/delete/")
        self.assertEqual(deleted.status_code, 200)
        blocked = self.client.get(f"/api/chats/{other.id}/messages/")
        self.assertEqual(blocked.status_code, 403)

    def test_chat_message_can_be_recalled_only_by_sender_within_two_minutes(self):
        other = self._create_chat_friend(username="chat-recall@test.local")
        self.client.login(username="student@test.local", password="student-pass")
        sent = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "这条消息稍后撤回。"},
            content_type="application/json",
        )
        message_id = sent.json()["message"]["id"]

        recalled = self.client.post(f"/api/chat-messages/{message_id}/recall/")

        self.assertEqual(recalled.status_code, 200)
        self.assertTrue(recalled.json()["message"]["recalled"])
        self.assertEqual(recalled.json()["message"]["content"], "消息已撤回")
        self.assertFalse(recalled.json()["message"]["imageUrl"])
        self.assertIsNotNone(ChatMessage.objects.get(pk=message_id).recalled_at)

        old_message = ChatMessage.objects.create(
            conversation=ChatMessage.objects.get(pk=message_id).conversation,
            sender=self.student,
            content="这条消息已经过期。",
        )
        ChatMessage.objects.filter(pk=old_message.pk).update(
            created_at=timezone.now() - timedelta(minutes=3),
        )
        too_late = self.client.post(f"/api/chat-messages/{old_message.id}/recall/")
        self.assertEqual(too_late.status_code, 400)

    def test_chat_mute_toggles_and_block_removes_conversation(self):
        other = self._create_chat_friend(username="chat-mute-block@test.local")
        self.client.login(username="student@test.local", password="student-pass")
        sent = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "设置聊天。"},
            content_type="application/json",
        )
        self.assertEqual(sent.status_code, 201)

        muted = self.client.post(f"/api/chats/{other.id}/mute/")
        self.assertEqual(muted.status_code, 200)
        self.assertTrue(muted.json()["muted"])
        self.assertEqual(ChatMute.objects.count(), 1)

        unmuted = self.client.post(f"/api/chats/{other.id}/mute/")
        self.assertEqual(unmuted.status_code, 200)
        self.assertFalse(unmuted.json()["muted"])
        self.assertFalse(ChatMute.objects.exists())

        blocked = self.client.post(f"/api/chats/{other.id}/block/")
        self.assertEqual(blocked.status_code, 200)
        self.assertTrue(ChatBlock.objects.filter(blocker=self.student, blocked=other).exists())
        self.assertFalse(self.client.get("/api/chats/").json()["chats"])
        self.assertEqual(self.client.get(f"/api/chats/{other.id}/messages/").status_code, 403)

    def test_chat_report_creates_moderation_record(self):
        other = self._create_chat_friend(username="chat-report@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        response = self.client.post(
            f"/api/chats/{other.id}/report/",
            data={"reason": "发送不相关的骚扰内容。"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        report = ChatReport.objects.get()
        self.assertEqual(report.reporter, self.student)
        self.assertEqual(report.target, other)
        self.assertEqual(report.reason, "发送不相关的骚扰内容。")

    def test_chat_websocket_accepts_friend_and_receives_message_event(self):
        other = self._create_chat_friend(username="chat-websocket@test.local")
        self.client.login(username="student@test.local", password="student-pass")
        sent = self.client.post(
            f"/api/chats/{other.id}/messages/",
            data={"content": "实时消息"},
            content_type="application/json",
        )
        message_id = sent.json()["message"]["id"]
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chats/")
        communicator.scope["user"] = self.student
        communicator.scope["url_route"] = {"kwargs": {"user_id": other.id}}

        async def exercise():
            connected, _ = await communicator.connect()
            ready = await communicator.receive_json_from()
            await get_channel_layer().group_send(
                f"chat_{min(self.student.id, other.id)}_{max(self.student.id, other.id)}",
                {"type": "chat.message", "messageId": message_id},
            )
            event = await communicator.receive_json_from()
            await communicator.disconnect()
            return connected, ready, event

        connected, ready, event = async_to_sync(exercise)()
        self.assertTrue(connected)
        self.assertEqual(ready["type"], "ready")
        self.assertEqual(event["type"], "message")
        self.assertEqual(event["message"]["content"], "实时消息")

    def test_chat_websocket_rejects_non_friend(self):
        other = get_user_model().objects.create_user(
            username="chat-websocket-blocked@test.local",
            email="chat-websocket-blocked@test.local",
            password="friend-pass",
        )
        StudentProfile.objects.create(user=other, school=self.school, term=self.term)
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chats/")
        communicator.scope["user"] = self.student
        communicator.scope["url_route"] = {"kwargs": {"user_id": other.id}}

        async def exercise():
            connected, _ = await communicator.connect()
            await communicator.disconnect()
            return connected

        self.assertFalse(async_to_sync(exercise)())

    def test_student_can_create_join_leave_and_message_in_chat_group(self):
        other = self._create_chat_friend(username="group-member@test.local")
        self.client.login(username="student@test.local", password="student-pass")

        created = self.client.post(
            "/api/chat-groups/",
            data={
                "name": "AP 申请互助组",
                "kind": "learning",
                "description": "一起拆解每周任务。",
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        group_id = created.json()["group"]["id"]
        self.assertTrue(
            ChatGroupMember.objects.filter(
                group_id=group_id,
                student=self.student,
                role="owner",
            ).exists()
        )

        message = self.client.post(
            f"/api/chat-groups/{group_id}/messages/",
            data={"content": "今天先完成文书提纲。"},
            content_type="application/json",
        )
        self.assertEqual(message.status_code, 201)
        self.assertEqual(message.json()["message"]["content"], "今天先完成文书提纲。")

        group_image = self._chat_image_upload("group.png", "PNG", "image/png")
        image_message = self.client.post(
            f"/api/chat-groups/{group_id}/messages/",
            data={"image": group_image},
        )
        self.assertEqual(image_message.status_code, 201, image_message.content.decode())
        self.assertTrue(image_message.json()["message"]["imageUrl"])

        group_file = SimpleUploadedFile(
            "group.pdf",
            b"%PDF-1.4 group file",
            content_type="application/pdf",
        )
        file_message = self.client.post(
            f"/api/chat-groups/{group_id}/messages/",
            data={"attachment": group_file},
        )
        self.assertEqual(file_message.status_code, 201, file_message.content.decode())
        self.assertTrue(file_message.json()["message"]["attachment"]["name"].endswith(".pdf"))

        communicator = WebsocketCommunicator(ChatGroupConsumer.as_asgi(), "/ws/chat-groups/")
        communicator.scope["user"] = self.student
        communicator.scope["url_route"] = {"kwargs": {"group_id": group_id}}

        async def exercise():
            connected, _ = await communicator.connect()
            ready = await communicator.receive_json_from()
            await get_channel_layer().group_send(
                f"chat_group_{group_id}",
                {
                    "type": "chat.group_message",
                    "messageId": message.json()["message"]["id"],
                },
            )
            event = await communicator.receive_json_from()
            await communicator.disconnect()
            return connected, ready, event

        connected, ready, event = async_to_sync(exercise)()
        self.assertTrue(connected)
        self.assertEqual(ready["type"], "ready")
        self.assertEqual(event["message"]["content"], "今天先完成文书提纲。")

        self.client.logout()
        self.client.login(username="group-member@test.local", password="friend-pass")
        before_join = self.client.get(f"/api/chat-groups/{group_id}/messages/")
        self.assertEqual(before_join.status_code, 403)

        joined = self.client.post(f"/api/chat-groups/{group_id}/join/")
        self.assertEqual(joined.status_code, 200)
        received = self.client.get(f"/api/chat-groups/{group_id}/messages/")
        self.assertEqual(received.status_code, 200)
        self.assertEqual(received.json()["messages"][0]["content"], "今天先完成文书提纲。")

        left = self.client.post(f"/api/chat-groups/{group_id}/leave/")
        self.assertEqual(left.status_code, 200)
        self.assertFalse(
            ChatGroupMember.objects.filter(group_id=group_id, student=other).exists()
        )

    def test_chat_group_validates_kind_and_owner_cannot_leave(self):
        self.client.login(username="student@test.local", password="student-pass")
        invalid = self.client.post(
            "/api/chat-groups/",
            data={"name": "无效群组", "kind": "unknown"},
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)

        created = self.client.post(
            "/api/chat-groups/",
            data={"name": "课程群", "kind": "course"},
            content_type="application/json",
        )
        group_id = created.json()["group"]["id"]
        cannot_leave = self.client.post(f"/api/chat-groups/{group_id}/leave/")
        self.assertEqual(cannot_leave.status_code, 400)
        self.assertTrue(ChatGroup.objects.filter(pk=group_id).exists())

    def test_chat_group_owner_can_invite_friend_and_friend_can_accept(self):
        invited_friend = self._create_chat_friend(
            first_name="受邀同学",
            username="group-invitee@test.local",
        )
        declined_friend = self._create_chat_friend(
            first_name="暂不加入",
            username="group-declined@test.local",
        )
        non_friend = get_user_model().objects.create_user(
            username="group-non-friend@test.local",
            email="group-non-friend@test.local",
            password="friend-pass",
        )
        StudentProfile.objects.create(user=non_friend, school=self.school, term=self.term)

        self.client.login(username="student@test.local", password="student-pass")
        created = self.client.post(
            "/api/chat-groups/",
            data={"name": "文书互助小组", "kind": "learning"},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        group_id = created.json()["group"]["id"]

        invite_options = self.client.get(f"/api/chat-groups/{group_id}/invites/")
        self.assertEqual(invite_options.status_code, 200)
        candidate_ids = {item["id"] for item in invite_options.json()["candidates"]}
        self.assertIn(invited_friend.id, candidate_ids)
        self.assertNotIn(non_friend.id, candidate_ids)

        forbidden = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": non_friend.id},
            content_type="application/json",
        )
        self.assertEqual(forbidden.status_code, 403)

        invited = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": invited_friend.id},
            content_type="application/json",
        )
        self.assertEqual(invited.status_code, 201, invited.content.decode())
        invitation_id = invited.json()["invitation"]["id"]
        duplicate = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": invited_friend.id},
            content_type="application/json",
        )
        self.assertEqual(duplicate.status_code, 400)

        self.client.logout()
        self.client.login(username="group-invitee@test.local", password="friend-pass")
        group_list = self.client.get("/api/chat-groups/")
        self.assertEqual(group_list.status_code, 200)
        self.assertEqual(group_list.json()["invitations"][0]["id"], invitation_id)
        accepted = self.client.post(
            f"/api/chat-group-invites/{invitation_id}/accept/",
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(
            ChatGroupMember.objects.filter(
                group_id=group_id,
                student=invited_friend,
            ).exists()
        )
        self.assertEqual(
            ChatGroupInvitation.objects.get(pk=invitation_id).status,
            "accepted",
        )
        member_cannot_invite = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": self.student.id},
            content_type="application/json",
        )
        self.assertEqual(member_cannot_invite.status_code, 403)

        self.client.logout()
        self.client.login(username="student@test.local", password="student-pass")
        already_member = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": invited_friend.id},
            content_type="application/json",
        )
        self.assertEqual(already_member.status_code, 400)
        declined = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": declined_friend.id},
            content_type="application/json",
        )
        self.assertEqual(declined.status_code, 201)
        declined_invitation_id = declined.json()["invitation"]["id"]

        self.client.logout()
        self.client.login(username="group-declined@test.local", password="friend-pass")
        rejected = self.client.post(
            f"/api/chat-group-invites/{declined_invitation_id}/reject/",
        )
        self.assertEqual(rejected.status_code, 200)

        self.client.logout()
        self.client.login(username="student@test.local", password="student-pass")
        reinvited = self.client.post(
            f"/api/chat-groups/{group_id}/invites/",
            data={"targetId": declined_friend.id},
            content_type="application/json",
        )
        self.assertEqual(reinvited.status_code, 201)
        self.assertEqual(reinvited.json()["invitation"]["status"], "pending")
