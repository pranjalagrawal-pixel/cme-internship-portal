from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    LoginForm,
    SubmissionForm,
    TaskForm,
    SubmissionReviewForm,
)

from .models import (
    Profile,
    Task,
    Submission,
    Attendance,
    Announcement,
    Certificate,
    InternshipProgram,
)


# ==================================================
# ROLE / PERMISSION CONFIGURATION
# ==================================================

# Users allowed to create, edit and review tasks.
TASK_MANAGEMENT_ROLES = {
    "ADMIN",
    "FOUNDER",
    "INTERN_HEAD",
    "CORE_TEAM",
}

# Users allowed to access the Core Team workspace.
CORE_TEAM_ACCESS_ROLES = {
    "ADMIN",
    "FOUNDER",
    "CORE_TEAM",
}

# Users allowed to manage internship programs.
PROGRAM_MANAGEMENT_ROLES = {
    "ADMIN",
    "FOUNDER",
    "INTERN_HEAD",
}


# ==================================================
# ROLE HELPERS
# ==================================================

def role_of(user):
    """
    Return the CME role of the currently authenticated user.
    """

    if user.is_superuser:
        return "ADMIN"

    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return "INTERN"


def can_manage_tasks(user):
    """
    Check whether the user can create/edit tasks
    and review submissions.
    """

    return (
        user.is_authenticated
        and (
            user.is_superuser
            or role_of(user) in TASK_MANAGEMENT_ROLES
        )
    )


def models_q_for_user(user):
    """
    Interns can see:
    - tasks specifically assigned to them
    - tasks that are not assigned to anyone
    """

    return (
        Q(assigned_to__isnull=True)
        | Q(assigned_to=user)
    )


# ==================================================
# HOME
# ==================================================

def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return render(
        request,
        "portal/home.html",
    )


# ==================================================
# LOGIN
# ==================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        ident = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]

        if "@" in ident:
            user_obj = User.objects.filter(
                email__iexact=ident
            ).first()
        else:
            user_obj = User.objects.filter(
                username__iexact=ident
            ).first()

        user = authenticate(
            request,
            username=(
                user_obj.username
                if user_obj
                else ident
            ),
            password=password,
        )

        if user is not None and user.is_active:
            login(
                request,
                user,
            )

            return redirect("dashboard")

        messages.error(
            request,
            "Login details were not recognised. Please try again.",
        )

    return render(
        request,
        "portal/login.html",
        {
            "form": form,
        },
    )


# ==================================================
# LOGOUT
# ==================================================

def logout_view(request):

    if request.method == "POST":
        logout(request)

    return redirect("home")


# ==================================================
# DASHBOARD
# ==================================================

@login_required
def dashboard(request):

    role = role_of(request.user)

    # Core Team has its own workspace.
    if role == "CORE_TEAM":
        return redirect(
            "core_team_dashboard"
        )

    # Founder / Admin / Intern Head
    if (
        role in TASK_MANAGEMENT_ROLES
        or request.user.is_superuser
    ):

        interns = User.objects.filter(
            profile__role="INTERN",
            is_active=True,
        )

        context = {
            "role": role,
            "can_manage_tasks": True,

            "intern_count": interns.count(),

            "task_count": Task.objects.filter(
                is_published=True
            ).count(),

            "submission_count": Submission.objects.count(),

            "pending_count": Submission.objects.filter(
                status__in=[
                    "SUBMITTED",
                    "IN_REVIEW",
                ]
            ).count(),

            "recent_submissions": (
                Submission.objects
                .select_related(
                    "intern",
                    "task",
                )
                .all()[:6]
            ),

            "announcements": (
                Announcement.objects
                .filter(published=True)[:4]
            ),
        }

    # HR dashboard
    elif role == "HR":

        context = {
            "role": role,
            "can_manage_tasks": False,

            "task_count": Task.objects.filter(
                is_published=True
            ).count(),

            "announcements": (
                Announcement.objects
                .filter(
                    published=True,
                    audience__in=[
                        "ALL",
                        "HR",
                    ],
                )[:4]
            ),
        }

    # Intern dashboard
    else:

        tasks_qs = (
            Task.objects
            .filter(is_published=True)
            .filter(
                models_q_for_user(request.user)
            )
            .distinct()
        )

        subs = (
            Submission.objects
            .filter(intern=request.user)
        )

        approved_points = (
            subs
            .filter(status="APPROVED")
            .aggregate(
                total=Sum("awarded_points")
            )["total"]
            or 0
        )

        assigned_count = tasks_qs.count()

        completed = (
            subs
            .filter(status="APPROVED")
            .count()
        )

        total_days = (
            Attendance.objects
            .filter(intern=request.user)
            .count()
        )

        present_days = (
            Attendance.objects
            .filter(
                intern=request.user,
                status="PRESENT",
            )
            .count()
        )

        context = {
            "role": role,
            "can_manage_tasks": False,

            "tasks": tasks_qs[:5],

            "assigned_count": assigned_count,

            "completed_count": completed,

            "pending_count": (
                subs
                .filter(
                    status__in=[
                        "SUBMITTED",
                        "IN_REVIEW",
                    ]
                )
                .count()
            ),

            "points": approved_points,

            "attendance_percent": (
                round(
                    present_days * 100 / total_days
                )
                if total_days
                else 0
            ),

            "announcements": (
                Announcement.objects
                .filter(
                    published=True,
                    audience__in=[
                        "ALL",
                        "INTERN",
                    ],
                )[:4]
            ),

            "recent_submissions": (
                subs
                .select_related("task")[:4]
            ),
        }

    return render(
        request,
        "portal/dashboard.html",
        context,
    )


# ==================================================
# CORE TEAM DASHBOARD
# ==================================================

@login_required
def core_team_dashboard(request):

    role = role_of(request.user)

    if (
        role not in CORE_TEAM_ACCESS_ROLES
        and not request.user.is_superuser
    ):
        return HttpResponseForbidden(
            "This workspace is reserved for CME Core Team members and authorized leadership."
        )

    members = (
        User.objects
        .filter(
            profile__role="CORE_TEAM",
            is_active=True,
        )
        .select_related("profile")
        .order_by(
            "first_name",
            "username",
        )
    )

    context = {
        "role": role,

        "members": members,

        "member_count": members.count(),

        "active_tasks": (
            Task.objects
            .filter(is_published=True)
            .count()
        ),

        "submissions_count": (
            Submission.objects.count()
        ),

        "pending_submissions": (
            Submission.objects
            .filter(
                status__in=[
                    "SUBMITTED",
                    "IN_REVIEW",
                ]
            )
            .count()
        ),

        "announcements": (
            Announcement.objects
            .filter(
                published=True,
                audience="ALL",
            )[:5]
        ),

        "is_leadership": (
            role in {
                "ADMIN",
                "FOUNDER",
            }
            or request.user.is_superuser
        ),
    }

    return render(
        request,
        "portal/core_team.html",
        context,
    )


# ==================================================
# TASK LIST
# ==================================================

@login_required
def tasks(request):

    role = role_of(request.user)

    if can_manage_tasks(request.user):

        task_list = (
            Task.objects
            .all()
            .prefetch_related(
                "assigned_to"
            )
        )

        submissions = (
            Submission.objects
            .select_related(
                "intern",
                "task",
            )
            .all()
        )

    else:

        task_list = (
            Task.objects
            .filter(is_published=True)
        )

        if role == "INTERN":

            task_list = (
                task_list
                .filter(
                    models_q_for_user(
                        request.user
                    )
                )
            )

            submissions = (
                Submission.objects
                .filter(
                    intern=request.user
                )
                .select_related("task")
            )

        else:

            submissions = (
                Submission.objects.none()
            )

    task_list = list(
        task_list.distinct()
    )

    # Attach the intern's current submission directly
    # to each task so the template can show the
    # correct action/status.
    if role == "INTERN":

        submission_by_task = {
            submission.task_id: submission
            for submission in submissions
        }

        for task in task_list:
            task.user_submission = (
                submission_by_task.get(task.id)
            )

    return render(
        request,
        "portal/tasks.html",
        {
            "tasks": task_list,
            "submissions": submissions,
            "role": role,
            "can_manage_tasks": can_manage_tasks(
                request.user
            ),
        },
    )


# ==================================================
# CREATE TASK
# ==================================================

@login_required
def task_create(request):

    if not can_manage_tasks(request.user):

        return HttpResponseForbidden(
            "Only the Founder, Intern Head, Core Team, or Administrator can create tasks."
        )

    form = TaskForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        task = form.save()

        messages.success(
            request,
            f'Task "{task.title}" has been created.',
        )

        return redirect("tasks")

    return render(
        request,
        "portal/task_form.html",
        {
            "form": form,
            "page_title": "Create task",
            "button_label": "Publish task",
        },
    )


# ==================================================
# EDIT TASK
# ==================================================

@login_required
def task_edit(request, task_id):

    if not can_manage_tasks(request.user):

        return HttpResponseForbidden(
            "Only the Founder, Intern Head, Core Team, or Administrator can edit tasks."
        )

    task = get_object_or_404(
        Task,
        pk=task_id,
    )

    form = TaskForm(
        request.POST or None,
        instance=task,
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Task details and maximum points updated.",
        )

        return redirect("tasks")

    return render(
        request,
        "portal/task_form.html",
        {
            "form": form,
            "task": task,
            "page_title": "Edit task",
            "button_label": "Save changes",
        },
    )


# ==================================================
# SUBMIT / RESUBMIT TASK
# ==================================================

@login_required
def submit_task(request, task_id):

    task = get_object_or_404(
        Task,
        id=task_id,
        is_published=True,
    )

    if role_of(request.user) != "INTERN":
        raise Http404

    # Check assignment.
    if not (
        task.assigned_to.filter(
            id=request.user.id
        ).exists()
        or not task.assigned_to.exists()
    ):
        raise Http404

    # Look for the latest submission by this intern.
    existing = (
        Submission.objects
        .filter(
            task=task,
            intern=request.user,
        )
        .order_by("-submitted_at")
        .first()
    )

    # A submission can only be submitted again when
    # the evaluator has requested revision.
    if existing and existing.status != "REVISION":

        messages.info(
            request,
            "A submission already exists for this task. "
            "You can resubmit after CME task management requests a revision.",
        )

        return redirect("tasks")

    form = SubmissionForm(
        request.POST or None,
        request.FILES or None,
        instance=existing if existing else None,
    )

    if request.method == "POST" and form.is_valid():

        submission = form.save(
            commit=False
        )

        submission.task = task
        submission.intern = request.user

        # Resubmission after revision.
        if existing:

            submission.status = "SUBMITTED"

            submission.evaluator_feedback = ""

            submission.awarded_points = 0

            submission.reviewed_at = None

            # auto_now_add does not update existing records,
            # therefore explicitly refresh the submission time.
            submission.submitted_at = timezone.now()

        submission.save()

        messages.success(
            request,
            (
                "Your task has been resubmitted for review."
                if existing
                else "Your task submission has been received."
            ),
        )

        return redirect("tasks")

    return render(
        request,
        "portal/submit_task.html",
        {
            "task": task,
            "form": form,
            "submission": existing,
            "is_revision": (
                existing is not None
                and existing.status == "REVISION"
            ),
        },
    )


# ==================================================
# REVIEW SUBMISSION
# ==================================================

@login_required
def submission_review(request, submission_id):

    if not can_manage_tasks(request.user):

        return HttpResponseForbidden(
            "Only the Founder, Intern Head, Core Team, or Administrator can review submissions and award points."
        )

    submission = get_object_or_404(
        Submission.objects.select_related(
            "task",
            "intern",
        ),
        pk=submission_id,
    )

    form = SubmissionReviewForm(
        request.POST or None,
        instance=submission,
    )

    if request.method == "POST" and form.is_valid():

        reviewed = form.save(
            commit=False
        )

        # Make sure points can never exceed task maximum.
        if reviewed.awarded_points > reviewed.task.points:
            reviewed.awarded_points = (
                reviewed.task.points
            )

        # If revision is requested, remove awarded points.
        if reviewed.status == "REVISION":
            reviewed.awarded_points = 0

        reviewed.reviewed_at = timezone.now()

        reviewed.save()

        messages.success(
            request,
            (
                f"Review saved. "
                f"{reviewed.awarded_points} points "
                f"recorded for this submission."
            ),
        )

        return redirect("tasks")

    return render(
        request,
        "portal/submission_review.html",
        {
            "form": form,
            "submission": submission,
        },
    )


# ==================================================
# ANNOUNCEMENTS
# ==================================================

@login_required
def announcements(request):

    role = role_of(request.user)

    audience = (
        "INTERN"
        if role == "INTERN"
        else "HR"
    )

    items = (
        Announcement.objects
        .filter(
            published=True,
            audience__in=[
                "ALL",
                audience,
            ],
        )
    )

    return render(
        request,
        "portal/announcements.html",
        {
            "announcements": items,
        },
    )


# ==================================================
# ATTENDANCE
# ==================================================

@login_required
def attendance(request):

    role = role_of(request.user)

    if role == "INTERN":

        records = (
            Attendance.objects
            .filter(
                intern=request.user
            )
        )

    else:

        records = (
            Attendance.objects
            .select_related(
                "intern",
                "recorded_by",
            )
            .all()
        )

    return render(
        request,
        "portal/attendance.html",
        {
            "records": records,
            "role": role,
        },
    )


# ==================================================
# CERTIFICATES
# ==================================================

@login_required
def certificates(request):

    role = role_of(request.user)

    if role == "INTERN":

        items = (
            Certificate.objects
            .filter(
                intern=request.user
            )
        )

    else:

        items = (
            Certificate.objects
            .select_related("intern")
            .all()
        )

    return render(
        request,
        "portal/certificates.html",
        {
            "certificates": items,
            "role": role,
        },
    )


# ==================================================
# CERTIFICATE VERIFICATION
# ==================================================

def verify_certificate(request, code):

    certificate = get_object_or_404(
        Certificate,
        certificate_code=code,
        is_issued=True,
    )

    return render(
        request,
        "portal/verify.html",
        {
            "certificate": certificate,
        },
    )


# ==================================================
# INTERNSHIP PROGRAMS
# ==================================================

@login_required
def programs(request):

    role = role_of(request.user)

    program_list = (
        InternshipProgram.objects
        .exclude(status="DRAFT")
    )

    if (
        role in PROGRAM_MANAGEMENT_ROLES
        or request.user.is_superuser
    ):

        program_list = (
            InternshipProgram.objects.all()
        )

    return render(
        request,
        "portal/programs.html",
        {
            "programs": program_list,
            "role": role,
            "can_manage_programs": (
                role in PROGRAM_MANAGEMENT_ROLES
                or request.user.is_superuser
            ),
        },
    )