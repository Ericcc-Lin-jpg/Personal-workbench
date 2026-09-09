"""
URL configuration for ddl_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import path
from django.views.static import serve

from main import views as main_views

def frontend(request):
    index_path = settings.BASE_DIR / "frontend" / "dist" / "index.html"
    if index_path.exists():
        return serve(request, "index.html", document_root=index_path.parent)
    return redirect(f"{settings.FRONTEND_URL}/")


urlpatterns = [
    path("", frontend, name="frontend"),
    path(
        "assets/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "frontend" / "dist" / "assets"},
    ),
    path(
        "favicon.svg",
        serve,
        {"document_root": settings.BASE_DIR / "frontend" / "dist"},
    ),
    path(
        "icons.svg",
        serve,
        {"document_root": settings.BASE_DIR / "frontend" / "dist"},
    ),
    path("healthz/", main_views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/bootstrap/", main_views.api_bootstrap, name="api-bootstrap"),
    path("api/dashboard/", main_views.api_dashboard, name="api-dashboard"),
    path("api/student-profile/", main_views.api_student_profile, name="api-student-profile"),
    path("api/annual-plan/", main_views.api_annual_plan, name="api-annual-plan"),
    path("api/annual-plan/<int:task_id>/", main_views.api_annual_plan_task_detail, name="api-annual-plan-task-detail"),
    path("api/annual-plan/<int:task_id>/subtasks/", main_views.api_annual_plan_subtask, name="api-annual-plan-subtask"),
    path("api/annual-plan/<int:task_id>/subtasks/<int:subtask_id>/", main_views.api_annual_plan_subtask_detail, name="api-annual-plan-subtask-detail"),
    path("api/options/", main_views.api_options, name="api-options"),
    path("api/deadlines/<int:deadline_id>/state/", main_views.api_deadline_state, name="api-deadline-state"),
    path("api/personal-tasks/", main_views.api_personal_task, name="api-personal-task"),
    path("api/personal-tasks/<int:task_id>/", main_views.api_personal_task_detail, name="api-personal-task-detail"),
    path("api/personal-tasks/<int:task_id>/state/", main_views.api_personal_task_state, name="api-personal-task-state"),
    path("api/notifications/", main_views.api_notifications, name="api-notifications"),
    path("api/notification-settings/", main_views.api_notification_settings, name="api-notification-settings"),
    path("api/notifications/read/", main_views.api_notifications_read, name="api-notifications-read"),
    path("api/friends/", main_views.api_friends, name="api-friends"),
    path("api/friends/<int:user_id>/<str:action>/", main_views.api_friend_action, name="api-friend-action"),
    path("api/chats/", main_views.api_chats, name="api-chats"),
    path("api/chats/<int:user_id>/messages/", main_views.api_chat_messages, name="api-chat-messages"),
    path("api/chat-messages/<int:message_id>/recall/", main_views.api_chat_message_recall, name="api-chat-message-recall"),
    path("api/chats/<int:user_id>/mute/", main_views.api_chat_mute, name="api-chat-mute"),
    path("api/chats/<int:user_id>/block/", main_views.api_chat_block, name="api-chat-block"),
    path("api/chats/<int:user_id>/report/", main_views.api_chat_report, name="api-chat-report"),
    path("api/chat-groups/", main_views.api_chat_groups, name="api-chat-groups"),
    path("api/chat-groups/<int:group_id>/invites/", main_views.api_chat_group_invites, name="api-chat-group-invites"),
    path("api/chat-groups/<int:group_id>/messages/", main_views.api_chat_group_messages, name="api-chat-group-messages"),
    path("api/chat-groups/<int:group_id>/<str:action>/", main_views.api_chat_group_action, name="api-chat-group-action"),
    path("api/chat-group-invites/<int:invitation_id>/<str:action>/", main_views.api_chat_group_invitation_action, name="api-chat-group-invitation-action"),
    path("api/wechat/test/", main_views.api_wechat_test, name="api-wechat-test"),
    path("api/wechat/bind/start/", main_views.api_wechat_bind_start, name="api-wechat-bind-start"),
    path("api/wechat/bind/callback/", main_views.api_wechat_bind_callback, name="api-wechat-bind-callback"),
    path("api/subscriptions/<int:class_id>/toggle/", main_views.api_subscription_toggle, name="api-subscription-toggle"),
    path("api/auth/register/", main_views.api_register, name="api-register"),
    path("api/auth/login/", main_views.api_login, name="api-login"),
    path("api/auth/teacher-register/", main_views.api_teacher_register, name="api-teacher-register"),
    path("api/auth/teacher-login/", main_views.api_teacher_login, name="api-teacher-login"),
    path("api/auth/password/", main_views.api_change_password, name="api-change-password"),
    path("api/auth/password/reset/", main_views.api_password_reset_request, name="api-password-reset-request"),
    path("api/auth/password/reset/confirm/", main_views.api_password_reset_confirm, name="api-password-reset-confirm"),
    path("api/auth/logout/", main_views.api_logout, name="api-logout"),
    path("api/teacher/bootstrap/", main_views.api_teacher_bootstrap, name="api-teacher-bootstrap"),
    path("api/teacher/classes/", main_views.api_teacher_class, name="api-teacher-class"),
    path("api/teacher/courses/<int:course_id>/end/", main_views.api_teacher_course_end, name="api-teacher-course-end"),
    path("api/teacher/deadlines/", main_views.api_teacher_deadline, name="api-teacher-deadline"),
    path("api/teacher/deadlines/<int:deadline_id>/", main_views.api_teacher_deadline_update, name="api-teacher-deadline-update"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
