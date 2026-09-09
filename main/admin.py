from django.contrib import admin

from .models import (
    ClassGroup,
    ClassSubscription,
    Checkin,
    AnnualPlanSubtask,
    AnnualPlanTask,
    ChatConversation,
    ChatBlock,
    ChatGroup,
    ChatGroupInvitation,
    ChatGroupMember,
    ChatGroupMessage,
    ChatMessage,
    ChatMute,
    ChatReport,
    Course,
    Deadline,
    Notification,
    PersonalTask,
    School,
    StudentDeadlineState,
    StudentFriendship,
    StudentProfile,
    StudentNotificationSettings,
    TaskReminder,
    TeacherApplication,
    Term,
)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "start_date", "end_date", "is_active")
    list_filter = ("school", "is_active")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "term", "grade", "curriculum", "motto")
    list_filter = ("school", "term", "curriculum")
    search_fields = ("user__username", "user__email", "user__first_name")


@admin.register(StudentFriendship)
class StudentFriendshipAdmin(admin.ModelAdmin):
    list_display = ("user_a", "user_b", "requested_by", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = (
        "user_a__username",
        "user_a__email",
        "user_b__username",
        "user_b__email",
    )


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ("user_a", "user_b", "created_at", "updated_at")
    search_fields = (
        "user_a__username",
        "user_a__email",
        "user_b__username",
        "user_b__email",
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "content_preview", "has_image", "created_at", "read_at")
    list_filter = ("read_at",)
    search_fields = ("content", "sender__username")

    @admin.display(description="消息")
    def content_preview(self, obj):
        return obj.content[:50] or ("图片消息" if obj.image else "")

    @admin.display(boolean=True, description="图片")
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(ChatMute)
class ChatMuteAdmin(admin.ModelAdmin):
    list_display = ("student", "conversation", "created_at")
    search_fields = ("student__username", "student__email")


@admin.register(ChatBlock)
class ChatBlockAdmin(admin.ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
    search_fields = ("blocker__username", "blocked__username")


@admin.register(ChatReport)
class ChatReportAdmin(admin.ModelAdmin):
    list_display = ("reporter", "target", "reason", "created_at")
    search_fields = ("reporter__username", "target__username", "reason")


@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "created_by", "created_at", "updated_at")
    list_filter = ("kind",)
    search_fields = ("name", "description", "created_by__username")


@admin.register(ChatGroupMember)
class ChatGroupMemberAdmin(admin.ModelAdmin):
    list_display = ("group", "student", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("group__name", "student__username")


@admin.register(ChatGroupInvitation)
class ChatGroupInvitationAdmin(admin.ModelAdmin):
    list_display = ("group", "inviter", "invitee", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("group__name", "inviter__username", "invitee__username")


@admin.register(ChatGroupMessage)
class ChatGroupMessageAdmin(admin.ModelAdmin):
    list_display = ("group", "sender", "content_preview", "created_at")
    search_fields = ("group__name", "sender__username", "content")

    @admin.display(description="消息")
    def content_preview(self, obj):
        return obj.content[:80]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "term", "code")
    list_filter = ("school", "term")
    search_fields = ("name", "code")


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "teacher_name")
    list_filter = ("course__school", "course__term")
    search_fields = ("name", "teacher_name", "course__name")


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "class_group", "kind", "due_at", "updated_at", "is_active")
    list_filter = ("source_type", "kind", "is_active")
    search_fields = ("title", "description")
    date_hierarchy = "due_at"


@admin.register(ClassSubscription)
class ClassSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("student", "class_group", "created_at")
    list_filter = ("class_group__course__school",)
    search_fields = ("student__username", "class_group__course__name")


@admin.register(StudentDeadlineState)
class StudentDeadlineStateAdmin(admin.ModelAdmin):
    list_display = ("student", "deadline", "status", "priority", "remind_at", "updated_at")
    list_filter = ("status", "priority")
    search_fields = ("student__username", "deadline__title")


@admin.register(PersonalTask)
class PersonalTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "due_at", "status", "priority")
    list_filter = ("status", "priority")
    search_fields = ("title", "student__username")


@admin.register(TaskReminder)
class TaskReminderAdmin(admin.ModelAdmin):
    list_display = ("student", "deadline", "personal_task", "remind_at", "created_at")
    list_filter = ("remind_at",)
    search_fields = ("student__username", "deadline__title", "personal_task__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "notification_type", "scheduled_at", "read_at", "wechat_claimed_at", "wechat_sent_at")
    list_filter = ("notification_type", "read_at", "wechat_sent_at")
    search_fields = ("title", "message", "student__username")


@admin.register(StudentNotificationSettings)
class StudentNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ("student", "due_24h_enabled", "wechat_enabled", "wechat_openid", "updated_at")
    list_filter = ("due_24h_enabled", "wechat_enabled")
    search_fields = ("student__username", "student__email", "wechat_openid")


@admin.register(Checkin)
class CheckinAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "completed_total", "task_total", "completed_at")
    list_filter = ("date",)
    search_fields = ("student__username", "student__email")
    date_hierarchy = "date"


class AnnualPlanSubtaskInline(admin.TabularInline):
    model = AnnualPlanSubtask
    extra = 0


@admin.register(AnnualPlanTask)
class AnnualPlanTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "category", "task_type", "start_date", "end_date", "node_date")
    list_filter = ("category", "task_type")
    search_fields = ("title", "description", "student__username")
    inlines = (AnnualPlanSubtaskInline,)


@admin.register(TeacherApplication)
class TeacherApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "status", "submitted_at")
    list_filter = ("status", "school")
    search_fields = ("user__username", "user__email")
