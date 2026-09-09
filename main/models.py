from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class School(models.Model):
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=40, unique=True)

    def __str__(self):
        return self.name


class Term(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="terms")
    name = models.CharField(max_length=80)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.school.name} · {self.name}"


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="students")
    term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="students")
    grade = models.CharField(max_length=30, blank=True)
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    curriculum = models.CharField(max_length=50, blank=True)
    motto = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class StudentFriendship(models.Model):
    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("accepted", "已成为好友"),
    ]

    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_b",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_a", "user_b"],
                name="unique_student_friendship_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["user_a", "status"]),
            models.Index(fields=["user_b", "status"]),
        ]

    def clean(self):
        if self.user_a_id == self.user_b_id:
            raise ValidationError("不能添加自己为好友。")
        if self.requested_by_id not in {self.user_a_id, self.user_b_id}:
            raise ValidationError("好友申请发起人必须属于这段关系。")
        if self.user_a_id > self.user_b_id:
            raise ValidationError("好友关系需要按固定顺序保存。")

    def __str__(self):
        return f"{self.user_a} · {self.user_b} · {self.get_status_display()}"


class ChatConversation(models.Model):
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations_as_b",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_a", "user_b"],
                name="unique_chat_conversation_pair",
            ),
        ]
        ordering = ["-updated_at"]

    def clean(self):
        if self.user_a_id == self.user_b_id:
            raise ValidationError("不能和自己创建聊天。")
        if self.user_a_id > self.user_b_id:
            raise ValidationError("聊天会话需要按固定顺序保存。")

    def __str__(self):
        return f"{self.user_a} · {self.user_b}"


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_messages",
    )
    content = models.TextField(max_length=2000, blank=True)
    image = models.FileField(
        upload_to="chat_images/%Y/%m/",
        blank=True,
        null=True,
        max_length=255,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    recalled_at = models.DateTimeField(null=True, blank=True)
    shared_deadline = models.ForeignKey(
        "Deadline",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_chat_messages",
    )
    shared_personal_task = models.ForeignKey(
        "PersonalTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_chat_messages",
    )
    attachment = models.FileField(
        upload_to="chat_files/%Y/%m/",
        blank=True,
        null=True,
        max_length=255,
    )

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "read_at"]),
        ]

    def clean(self):
        if self.sender_id not in {self.conversation.user_a_id, self.conversation.user_b_id}:
            raise ValidationError("消息发送者必须属于当前会话。")
        if (
            not self.content.strip()
            and not self.image
            and not self.attachment
            and not self.shared_deadline_id
            and not self.shared_personal_task_id
        ):
            raise ValidationError("消息内容不能为空。")
        if self.image and self.attachment:
            raise ValidationError("一条消息只能上传一个文件。")
        if self.shared_deadline_id and self.shared_personal_task_id:
            raise ValidationError("一条消息只能分享一个任务。")

    def __str__(self):
        return f"{self.sender} · {self.content[:30]}"


class ChatNotification(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_notifications",
    )
    message = models.OneToOneField(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name="notification",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["student", "read_at"]),
            models.Index(fields=["student", "created_at"]),
        ]

    def __str__(self):
        return f"{self.student} · {self.message_id}"


class ChatMute(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="muted_chat_conversations",
    )
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="mutes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "conversation"],
                name="unique_chat_mute",
            ),
        ]


class ChatBlock(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_blocks_created",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_blocks_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_chat_block",
            ),
        ]


class ChatReport(models.Model):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_reports",
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_reports_received",
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)


class ChatGroup(models.Model):
    KIND_CHOICES = [
        ("learning", "学习小组"),
        ("course", "课程群"),
        ("event", "活动群"),
    ]

    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="learning")
    description = models.TextField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_chat_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.name


class ChatGroupMember(models.Model):
    ROLE_CHOICES = [
        ("owner", "创建者"),
        ("admin", "管理员"),
        ("member", "成员"),
    ]

    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="members")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_group_memberships",
    )
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "student"],
                name="unique_chat_group_member",
            ),
        ]


class ChatGroupInvitation(models.Model):
    STATUS_CHOICES = [
        ("pending", "待确认"),
        ("accepted", "已接受"),
        ("rejected", "已拒绝"),
    ]

    group = models.ForeignKey(
        ChatGroup,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_group_invitations",
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_chat_group_invitations",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "invitee"],
                name="unique_chat_group_invitation",
            ),
        ]
        indexes = [
            models.Index(fields=["invitee", "status"]),
            models.Index(fields=["group", "status"]),
        ]

    def clean(self):
        if self.inviter_id == self.invitee_id:
            raise ValidationError("不能邀请自己加入小组。")

    def __str__(self):
        return f"{self.group} · {self.invitee} · {self.get_status_display()}"


class ChatGroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_group_messages",
    )
    content = models.TextField(max_length=2000, blank=True)
    image = models.FileField(
        upload_to="chat_group_images/%Y/%m/",
        blank=True,
        null=True,
        max_length=255,
    )
    attachment = models.FileField(
        upload_to="chat_group_files/%Y/%m/",
        blank=True,
        null=True,
        max_length=255,
    )
    shared_deadline = models.ForeignKey(
        "Deadline",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_chat_group_messages",
    )
    shared_personal_task = models.ForeignKey(
        "PersonalTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_chat_group_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["group", "created_at"]),
        ]

    def __str__(self):
        return f"{self.sender} · {self.content[:30]}"

    def clean(self):
        if not (
            self.content.strip()
            or self.image
            or self.attachment
            or self.shared_deadline_id
            or self.shared_personal_task_id
        ):
            raise ValidationError("消息内容不能为空。")
        if self.image and self.attachment:
            raise ValidationError("一条消息只能上传一个文件。")
        if self.shared_deadline_id and self.shared_personal_task_id:
            raise ValidationError("一条消息只能分享一个任务。")


class Course(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="courses")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="courses")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_courses",
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "term", "name"], name="unique_course_per_term"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClassGroup(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_classes",
    )
    name = models.CharField(max_length=80)
    teacher_name = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "name"], name="unique_class_per_course"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.course.name} · {self.name}"


class ClassSubscription(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_subscriptions")
    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, related_name="subscriptions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "class_group"], name="unique_student_class_subscription"),
        ]

    def clean(self):
        existing = ClassSubscription.objects.filter(
            student=self.student,
            class_group__course=self.class_group.course,
        ).exclude(pk=self.pk)
        if existing.exists():
            raise ValidationError("同一门课程只能订阅一个班级。")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Deadline(models.Model):
    SOURCE_CHOICES = [
        ("course", "课程"),
        ("admissions", "升学"),
        ("competition", "竞赛"),
    ]
    KIND_CHOICES = [
        ("formative", "Formative"),
        ("summative", "Summative"),
        ("milestone", "节点"),
    ]

    class_group = models.ForeignKey(ClassGroup, on_delete=models.CASCADE, null=True, blank=True, related_name="deadlines")
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="course")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="formative")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_deadlines")
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["due_at"]

    def __str__(self):
        return self.title


class StudentDeadlineState(models.Model):
    STATUS_CHOICES = [
        ("todo", "未开始"),
        ("doing", "进行中"),
        ("done", "已完成"),
    ]
    PRIORITY_CHOICES = [
        ("low", "低"),
        ("normal", "中"),
        ("high", "高"),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deadline_states")
    deadline = models.ForeignKey(Deadline, on_delete=models.CASCADE, related_name="student_states")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    note = models.TextField(blank=True)
    remind_at = models.DateTimeField(null=True, blank=True)
    planned_start_at = models.DateTimeField(null=True, blank=True)
    planned_end_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "deadline"], name="unique_student_deadline_state"),
        ]


class PersonalTask(models.Model):
    STATUS_CHOICES = [
        ("todo", "未开始"),
        ("doing", "进行中"),
        ("done", "已完成"),
    ]
    PRIORITY_CHOICES = [
        ("low", "低"),
        ("normal", "中"),
        ("high", "高"),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_tasks")
    title = models.CharField(max_length=200)
    due_at = models.DateTimeField()
    note = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    remind_at = models.DateTimeField(null=True, blank=True)
    planned_start_at = models.DateTimeField(null=True, blank=True)
    planned_end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_at"]


class TaskReminder(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_reminders")
    deadline = models.ForeignKey(Deadline, on_delete=models.CASCADE, null=True, blank=True, related_name="reminders")
    personal_task = models.ForeignKey(PersonalTask, on_delete=models.CASCADE, null=True, blank=True, related_name="reminders")
    remind_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(deadline__isnull=False, personal_task__isnull=True)
                    | models.Q(deadline__isnull=True, personal_task__isnull=False)
                ),
                name="reminder_has_one_task_target",
            ),
            models.UniqueConstraint(
                fields=["student", "deadline", "remind_at"],
                name="unique_deadline_reminder",
            ),
            models.UniqueConstraint(
                fields=["student", "personal_task", "remind_at"],
                name="unique_personal_task_reminder",
            ),
        ]
        ordering = ["remind_at"]


class Notification(models.Model):
    TYPE_CHOICES = [
        ("due_24h", "截止前 24 小时"),
        ("custom_reminder", "自定义提醒"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    deadline = models.ForeignKey(
        Deadline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    personal_task = models.ForeignKey(
        PersonalTask,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    reminder = models.ForeignKey(
        TaskReminder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=24, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=300)
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    wechat_claimed_at = models.DateTimeField(null=True, blank=True)
    wechat_sent_at = models.DateTimeField(null=True, blank=True)
    wechat_error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(deadline__isnull=False, personal_task__isnull=True)
                    | models.Q(deadline__isnull=True, personal_task__isnull=False)
                ),
                name="notification_has_one_task_target",
            ),
            models.UniqueConstraint(
                fields=["student", "deadline", "notification_type", "scheduled_at"],
                name="unique_deadline_notification",
            ),
            models.UniqueConstraint(
                fields=["student", "personal_task", "notification_type", "scheduled_at"],
                name="unique_personal_task_notification",
            ),
        ]
        ordering = ["-scheduled_at", "-created_at"]


class StudentNotificationSettings(models.Model):
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
    )
    due_24h_enabled = models.BooleanField(default=True)
    wechat_enabled = models.BooleanField(default=False)
    wechat_openid = models.CharField(max_length=128, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["wechat_openid"],
                condition=~models.Q(wechat_openid=""),
                name="unique_nonempty_wechat_openid",
            ),
        ]


class Checkin(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    date = models.DateField()
    completed_at = models.DateTimeField()
    task_total = models.PositiveIntegerField()
    completed_total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"],
                name="unique_student_checkin_date",
            ),
        ]
        ordering = ["-date"]


class AnnualPlanTask(models.Model):
    CATEGORY_CHOICES = [
        ("academic", "学术"),
        ("test", "标化"),
        ("competition", "竞赛"),
        ("application", "申请"),
        ("personal", "个人"),
    ]
    TYPE_CHOICES = [
        ("period", "时间段"),
        ("node", "时间节点"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annual_plan_tasks",
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    task_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default="period")
    title = models.CharField(max_length=200)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    node_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "node_date", "created_at"]

    def clean(self):
        if self.task_type == "period":
            if not self.start_date or not self.end_date:
                raise ValidationError("时间段任务需要填写开始和结束日期。")
            if self.end_date < self.start_date:
                raise ValidationError("结束日期不能早于开始日期。")
        elif self.task_type == "node" and not self.node_date:
            raise ValidationError("时间节点任务需要填写日期。")


class AnnualPlanSubtask(models.Model):
    task = models.ForeignKey(
        AnnualPlanTask,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )
    title = models.CharField(max_length=200)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["completed", "due_date", "created_at"]


class TeacherApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher_application")
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="teacher_applications")
    proof = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
