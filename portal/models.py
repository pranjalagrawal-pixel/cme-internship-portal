import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


# ==================================================
# PROFILE
# ==================================================

class Profile(models.Model):
    ROLE_CHOICES = [
        ("ADMIN", "Administrator"),
        ("FOUNDER", "Founder"),
        ("CO_FOUNDER", "Co-Founder"),
        ("INTERN_HEAD", "Intern Head"),
        ("HR", "HR / Evaluator"),
        ("CORE_TEAM", "Core Team"),
        ("INTERN", "Intern"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=16,
        choices=ROLE_CHOICES,
        default="INTERN",
    )

    intern_id = models.CharField(
        max_length=24,
        unique=True,
        blank=True,
    )

    domain = models.CharField(
        max_length=80,
        blank=True,
    )

    cohort = models.CharField(
        max_length=80,
        blank=True,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        # The field is unique, so every profile needs an ID.
        # Role-specific prefixes keep staff IDs distinguishable.
        if not self.intern_id:
            prefixes = {
                "ADMIN": "CME-ADM",
                "FOUNDER": "CME-FND",
                "CO_FOUNDER": "CME-CFND",
                "INTERN_HEAD": "CME-IH",
                "HR": "CME-HR",
                "CORE_TEAM": "CME-CORE",
                "INTERN": "CME-INT",
            }

            prefix = prefixes.get(
                self.role,
                "CME-MBR",
            )

            candidate = (
                f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
            )

            while Profile.objects.filter(
                intern_id=candidate
            ).exists():
                candidate = (
                    f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
                )

            self.intern_id = candidate

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username}"
            f" ({self.role})"
        )


# ==================================================
# TASK
# ==================================================

class Task(models.Model):
    PRIORITY = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]

    title = models.CharField(
        max_length=180,
    )

    description = models.TextField()

    domain = models.CharField(
        max_length=80,
        blank=True,
    )

    priority = models.CharField(
        max_length=8,
        choices=PRIORITY,
        default="MEDIUM",
    )

    points = models.PositiveIntegerField(
        default=10,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_tasks",
    )

    is_published = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "due_date",
            "-created_at",
        ]

    def __str__(self):
        return self.title


# ==================================================
# SUBMISSION
# ==================================================

class Submission(models.Model):
    STATUS = [
        ("SUBMITTED", "Submitted"),
        ("IN_REVIEW", "In review"),
        ("APPROVED", "Approved"),
        ("REVISION", "Needs revision"),
    ]

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    intern = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    response_text = models.TextField()

    # Existing external project/document URL
    attachment_url = models.URLField(
        blank=True,
    )

    # Uploaded file attachment
    attachment = models.FileField(
        upload_to="task_submissions/%Y/%m/",
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS,
        default="SUBMITTED",
    )

    evaluator_feedback = models.TextField(
        blank=True,
    )

    awarded_points = models.PositiveIntegerField(
        default=0,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-submitted_at",
        ]

    def __str__(self):
        return (
            f"{self.intern.username} — "
            f"{self.task.title}"
        )


# ==================================================
# ATTENDANCE
# ==================================================

class Attendance(models.Model):
    STATUS = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LEAVE", "Leave"),
    ]

    intern = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    date = models.DateField(
        default=timezone.localdate,
    )

    status = models.CharField(
        max_length=8,
        choices=STATUS,
        default="PRESENT",
    )

    note = models.CharField(
        max_length=240,
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_recorded",
    )

    class Meta:
        unique_together = [
            ("intern", "date"),
        ]

        ordering = [
            "-date",
        ]

    def __str__(self):
        return (
            f"{self.intern.username} — "
            f"{self.date}"
        )


# ==================================================
# ANNOUNCEMENT
# ==================================================

class Announcement(models.Model):
    title = models.CharField(
        max_length=180,
    )

    body = models.TextField()

    audience = models.CharField(
        max_length=12,
        choices=[
            ("ALL", "Everyone"),
            ("INTERN", "Interns"),
            ("HR", "HR / Evaluators"),
        ],
        default="ALL",
    )

    published = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return self.title


# ==================================================
# CERTIFICATE
# ==================================================

class Certificate(models.Model):
    intern = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificates",
    )

    certificate_code = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
    )

    program_title = models.CharField(
        max_length=160,
        default="CME Internship & Training Program",
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
    )

    is_issued = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):
        if not self.certificate_code:
            self.certificate_code = (
                "CME-CERT-"
                + uuid.uuid4().hex[:10].upper()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.certificate_code


# ==================================================
# INTERNSHIP PROGRAM
# ==================================================

class InternshipProgram(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("OPEN", "Open for applications"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
    ]

    title = models.CharField(
        max_length=180,
    )

    domain = models.CharField(
        max_length=80,
    )

    short_description = models.CharField(
        max_length=280,
    )

    description = models.TextField()

    duration_weeks = models.PositiveSmallIntegerField(
        default=4,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    eligibility = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return self.title