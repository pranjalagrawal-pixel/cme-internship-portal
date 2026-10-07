from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from portal import views


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Home / Dashboard
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Internship Programs
    path("programs/", views.programs, name="programs"),

    # Core Team
    path(
        "core-team/",
        views.core_team_dashboard,
        name="core_team_dashboard",
    ),

    # Tasks
    path(
        "tasks/",
        views.tasks,
        name="tasks",
    ),
    path(
        "tasks/create/",
        views.task_create,
        name="task_create",
    ),
    path(
        "tasks/<int:task_id>/edit/",
        views.task_edit,
        name="task_edit",
    ),
    path(
        "tasks/<int:task_id>/submit/",
        views.submit_task,
        name="submit_task",
    ),

    # Submission Review
    path(
        "submissions/<int:submission_id>/review/",
        views.submission_review,
        name="submission_review",
    ),

    # Announcements
    path(
        "announcements/",
        views.announcements,
        name="announcements",
    ),

    # Attendance
    path(
        "attendance/",
        views.attendance,
        name="attendance",
    ),

    # Certificates
    path(
        "certificates/",
        views.certificates,
        name="certificates",
    ),

    # Certificate Verification
    path(
        "verify/<str:code>/",
        views.verify_certificate,
        name="verify_certificate",
    ),
]


# --------------------------------------------------
# MEDIA FILES
# --------------------------------------------------
# Used for uploaded submission attachments during
# local development.
# --------------------------------------------------

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )