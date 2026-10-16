from django.contrib import admin
from .models import Profile, Task, Submission, Attendance, Announcement, Certificate, InternshipProgram, InternshipBatch
admin.site.site_header = "CME Internship & Training Administration"
admin.site.site_title = "CME Portal Admin"
admin.site.index_title = "Program operations"
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin): list_display = ("user", "role", "intern_id", "domain", "cohort", "assigned_program", "assigned_batch"); list_filter = ("role", "domain", "cohort", "assigned_program", "assigned_batch"); search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "intern_id")
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin): list_display = ("title", "program", "batch", "domain", "priority", "points", "due_date", "is_published"); list_filter = ("program", "batch", "domain", "priority", "is_published"); search_fields = ("title", "description"); filter_horizontal = ("assigned_to",)
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin): list_display = ("task", "intern", "status", "awarded_points", "submitted_at"); list_filter = ("status",); search_fields = ("task__title", "intern__username"); readonly_fields = ("submitted_at",)
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin): list_display = ("intern", "program", "batch", "date", "status", "recorded_by"); list_filter = ("program", "batch", "status", "date"); search_fields = ("intern__username",)
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin): list_display = ("title", "program", "batch", "audience", "published", "created_at"); list_filter = ("program", "batch", "audience", "published")
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin): list_display = ("certificate_code", "intern", "program_title", "program", "batch", "issue_date", "is_issued"); list_filter = ("program", "batch", "is_issued"); search_fields = ("certificate_code", "intern__username")

# The Django admin console is reserved for superusers. Task management roles use the role-protected portal screens.
def _superuser_only_admin_access(request):
    return bool(request.user.is_active and request.user.is_superuser)

admin.site.has_permission = _superuser_only_admin_access


@admin.register(InternshipProgram)
class InternshipProgramAdmin(admin.ModelAdmin):
    list_display = ("title", "domain", "duration_weeks", "status", "start_date", "end_date", "updated_at")
    list_filter = ("status", "domain")
    search_fields = ("title", "domain", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InternshipBatch)
class InternshipBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "program", "status", "start_date", "end_date")
    list_filter = ("program", "status")
    search_fields = ("name", "code", "program__title")
    readonly_fields = ("created_at",)
