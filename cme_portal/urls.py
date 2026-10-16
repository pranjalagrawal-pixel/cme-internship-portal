from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from portal import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("programs/", views.programs, name="programs"),
    path("programs/create/", views.program_create, name="program_create"),
    path("programs/<int:program_id>/edit/", views.program_edit, name="program_edit"),
    path("programs/<int:program_id>/batches/create/", views.batch_create, name="batch_create"),
    path("core-team/", views.core_team_dashboard, name="core_team_dashboard"),
    path("tasks/", views.tasks, name="tasks"),
    path("tasks/create/", views.task_create, name="task_create"),
    path("tasks/<int:task_id>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:task_id>/submit/", views.submit_task, name="submit_task"),
    path("submissions/<int:submission_id>/review/", views.submission_review, name="submission_review"),
    path("announcements/", views.announcements, name="announcements"),
    path("attendance/", views.attendance, name="attendance"),
    path("certificates/", views.certificates, name="certificates"),
    path("verify/<str:code>/", views.verify_certificate, name="verify_certificate"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
