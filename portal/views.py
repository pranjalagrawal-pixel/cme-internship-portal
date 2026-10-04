from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import LoginForm, SubmissionForm, TaskForm, SubmissionReviewForm
from .models import Profile, Task, Submission, Attendance, Announcement, Certificate, InternshipProgram

TASK_MANAGEMENT_ROLES = {"ADMIN", "FOUNDER", "INTERN_HEAD"}
CORE_TEAM_ACCESS_ROLES = {"ADMIN", "FOUNDER", "CORE_TEAM"}


def role_of(user):
    if user.is_superuser:
        return "ADMIN"
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return "INTERN"


def can_manage_tasks(user):
    return user.is_authenticated and (user.is_superuser or role_of(user) in TASK_MANAGEMENT_ROLES)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "portal/home.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ident = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]
        user_obj = User.objects.filter(email__iexact=ident).first() if "@" in ident else User.objects.filter(username__iexact=ident).first()
        user = authenticate(request, username=user_obj.username if user_obj else ident, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Login details were not recognised. Please try again.")
    return render(request, "portal/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    role = role_of(request.user)
    if role == "CORE_TEAM":
        return redirect("core_team_dashboard")
    if role in TASK_MANAGEMENT_ROLES or request.user.is_superuser:
        interns = User.objects.filter(profile__role="INTERN", is_active=True)
        context = {
            "role": role,
            "can_manage_tasks": True,
            "intern_count": interns.count(),
            "task_count": Task.objects.filter(is_published=True).count(),
            "submission_count": Submission.objects.count(),
            "pending_count": Submission.objects.filter(status__in=["SUBMITTED", "IN_REVIEW"]).count(),
            "recent_submissions": Submission.objects.select_related("intern", "task").all()[:6],
            "announcements": Announcement.objects.filter(published=True)[:4],
        }
    elif role == "HR":
        context = {
            "role": role,
            "can_manage_tasks": False,
            "task_count": Task.objects.filter(is_published=True).count(),
            "announcements": Announcement.objects.filter(published=True, audience__in=["ALL", "HR"])[:4],
        }
    else:
        tasks_qs = Task.objects.filter(is_published=True).filter(models_q_for_user(request.user))
        subs = Submission.objects.filter(intern=request.user)
        approved_points = subs.filter(status="APPROVED").aggregate(total=Sum("awarded_points"))["total"] or 0
        assigned_count = tasks_qs.count()
        completed = subs.filter(status="APPROVED").count()
        total_days = Attendance.objects.filter(intern=request.user).count()
        present_days = Attendance.objects.filter(intern=request.user, status="PRESENT").count()
        context = {
            "role": role, "can_manage_tasks": False, "tasks": tasks_qs[:5], "assigned_count": assigned_count,
            "completed_count": completed, "pending_count": subs.filter(status__in=["SUBMITTED", "IN_REVIEW"]).count(),
            "points": approved_points,
            "attendance_percent": round(present_days * 100 / total_days) if total_days else 0,
            "announcements": Announcement.objects.filter(published=True, audience__in=["ALL", "INTERN"])[:4],
            "recent_submissions": subs.select_related("task")[:4],
        }
    return render(request, "portal/dashboard.html", context)



@login_required
def core_team_dashboard(request):
    """Separate internal workspace for manually-created CME core team accounts."""
    role = role_of(request.user)
    if role not in CORE_TEAM_ACCESS_ROLES and not request.user.is_superuser:
        return HttpResponseForbidden("This workspace is reserved for CME Core Team members and authorized leadership.")

    members = User.objects.filter(profile__role="CORE_TEAM", is_active=True).select_related("profile").order_by("first_name", "username")
    context = {
        "role": role,
        "members": members,
        "member_count": members.count(),
        "active_tasks": Task.objects.filter(is_published=True).count(),
        "submissions_count": Submission.objects.count(),
        "pending_submissions": Submission.objects.filter(status__in=["SUBMITTED", "IN_REVIEW"]).count(),
        "announcements": Announcement.objects.filter(published=True, audience="ALL")[:5],
        "is_leadership": role in {"ADMIN", "FOUNDER"} or request.user.is_superuser,
    }
    return render(request, "portal/core_team.html", context)

def models_q_for_user(user):
    return Q(assigned_to__isnull=True) | Q(assigned_to=user)


@login_required
def tasks(request):
    role = role_of(request.user)
    if can_manage_tasks(request.user):
        task_list = Task.objects.all()
        submissions = Submission.objects.select_related("intern", "task").all()
    else:
        task_list = Task.objects.filter(is_published=True)
        if role == "INTERN":
            task_list = task_list.filter(models_q_for_user(request.user))
        submissions = Submission.objects.filter(intern=request.user) if role == "INTERN" else Submission.objects.none()
    return render(request, "portal/tasks.html", {
        "tasks": task_list.distinct(), "submissions": submissions, "role": role,
        "can_manage_tasks": can_manage_tasks(request.user),
    })


@login_required
def task_create(request):
    if not can_manage_tasks(request.user):
        return HttpResponseForbidden("Only the Founder, Intern Head, or Administrator can create tasks.")
    form = TaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save()
        messages.success(request, f'Task "{task.title}" has been created.')
        return redirect("tasks")
    return render(request, "portal/task_form.html", {"form": form, "page_title": "Create task", "button_label": "Publish task"})


@login_required
def task_edit(request, task_id):
    if not can_manage_tasks(request.user):
        return HttpResponseForbidden("Only the Founder, Intern Head, or Administrator can edit tasks.")
    task = get_object_or_404(Task, pk=task_id)
    form = TaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Task details and maximum points updated.")
        return redirect("tasks")
    return render(request, "portal/task_form.html", {"form": form, "task": task, "page_title": "Edit task", "button_label": "Save changes"})


@login_required
def submit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, is_published=True)
    if role_of(request.user) != "INTERN":
        raise Http404
    if not (task.assigned_to.filter(id=request.user.id).exists() or not task.assigned_to.exists()):
        raise Http404
    existing = Submission.objects.filter(task=task, intern=request.user).exclude(status="REVISION").first()
    if existing:
        messages.info(request, "A submission already exists for this task. Contact CME task management if a revision is needed.")
        return redirect("tasks")
    form = SubmissionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        submission = form.save(commit=False)
        submission.task = task
        submission.intern = request.user
        submission.save()
        messages.success(request, "Your task submission has been received.")
        return redirect("tasks")
    return render(request, "portal/submit_task.html", {"task": task, "form": form})


@login_required
def submission_review(request, submission_id):
    if not can_manage_tasks(request.user):
        return HttpResponseForbidden("Only the Founder, Intern Head, or Administrator can review submissions and award points.")
    submission = get_object_or_404(Submission.objects.select_related("task", "intern"), pk=submission_id)
    form = SubmissionReviewForm(request.POST or None, instance=submission)
    if request.method == "POST" and form.is_valid():
        reviewed = form.save(commit=False)
        reviewed.reviewed_at = timezone.now()
        reviewed.save()
        messages.success(request, f"Review saved. {reviewed.awarded_points} points recorded for this submission.")
        return redirect("tasks")
    return render(request, "portal/submission_review.html", {"form": form, "submission": submission})


@login_required
def announcements(request):
    role = role_of(request.user)
    audience = "INTERN" if role == "INTERN" else "HR"
    items = Announcement.objects.filter(published=True, audience__in=["ALL", audience])
    return render(request, "portal/announcements.html", {"announcements": items})


@login_required
def attendance(request):
    role = role_of(request.user)
    records = Attendance.objects.filter(intern=request.user) if role == "INTERN" else Attendance.objects.select_related("intern", "recorded_by").all()
    return render(request, "portal/attendance.html", {"records": records, "role": role})


@login_required
def certificates(request):
    role = role_of(request.user)
    items = Certificate.objects.filter(intern=request.user) if role == "INTERN" else Certificate.objects.select_related("intern").all()
    return render(request, "portal/certificates.html", {"certificates": items, "role": role})


def verify_certificate(request, code):
    certificate = get_object_or_404(Certificate, certificate_code=code, is_issued=True)
    return render(request, "portal/verify.html", {"certificate": certificate})


@login_required
def programs(request):
    """Show active internship/training programs to signed-in portal members."""
    role = role_of(request.user)
    program_list = InternshipProgram.objects.exclude(status="DRAFT")
    if role in TASK_MANAGEMENT_ROLES or role == "ADMIN" or request.user.is_superuser:
        program_list = InternshipProgram.objects.all()
    return render(request, "portal/programs.html", {
        "programs": program_list,
        "role": role,
        "can_manage_programs": request.user.is_superuser,
    })
