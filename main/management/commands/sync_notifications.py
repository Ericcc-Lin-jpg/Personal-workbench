from django.core.management.base import BaseCommand

from main.models import StudentProfile
from main.views import dispatch_student_wechat_notifications, sync_student_notifications


class Command(BaseCommand):
    help = "同步学生的站内提醒通知。"

    def handle(self, *args, **options):
        student_ids = StudentProfile.objects.values_list("user_id", flat=True)
        totals = {"sent": 0, "failed": 0, "skipped": 0}
        for student_id in student_ids:
            profile = StudentProfile.objects.select_related("user").get(user_id=student_id)
            sync_student_notifications(profile.user)
            result = dispatch_student_wechat_notifications(profile.user)
            for key in totals:
                totals[key] += result[key]
        self.stdout.write(
            self.style.SUCCESS(
                "站内提醒和微信推送同步完成。"
                f" 已发送 {totals['sent']}，失败 {totals['failed']}，跳过 {totals['skipped']}。"
            )
        )
