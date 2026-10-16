from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import LoginForm, SubmissionForm, TaskForm, SubmissionReviewForm, InternshipProgramForm, InternshipBatchForm
from .models import Profile, Task, Submission, Attendance, Announcement, Certificate, InternshipProgram

TASK_MANAGEMENT_ROLES = {"ADMIN", "FOUNDER", "CO_FOUNDER", "INTERN_HEAD"}
CORE_TEAM_ACCESS_ROLES = {"ADMIN", "FOUNDER", "CO_FOUNDER", "CORE_TEAM"}


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
        full_access = can_view_all_programs(request.user)
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if full_access:
            interns = User.objects.filter(profile__role="INTERN", is_active=True)
            visible_tasks = Task.objects.all()
            visible_submissions = Submission.objects.all()
            visible_announcements = Announcement.objects.filter(published=True)
        elif program:
            interns = User.objects.filter(profile__role="INTERN", is_active=True, profile__assigned_program=program)
            if batch:
                interns = interns.filter(profile__assigned_batch=batch)
            task_scope = Q(program=program, batch__isnull=True)
            if batch:
                task_scope |= Q(batch=batch)
            visible_tasks = Task.objects.filter(task_scope)
            visible_submissions = Submission.objects.filter(task__in=visible_tasks)
            visible_announcements = announcements_for_member(request.user, "HR")
        else:
            interns = User.objects.none()
            visible_tasks = Task.objects.none()
            visible_submissions = Submission.objects.none()
            visible_announcements = Announcement.objects.none()
        pending_submissions = visible_submissions.filter(status__in=["SUBMITTED", "IN_REVIEW"])
        context = {
            "role": role,
            "can_manage_tasks": True,
            "intern_count": interns.count(),
            "task_count": visible_tasks.filter(is_published=True).count(),
            "submission_count": visible_submissions.count(),
            "pending_count": pending_submissions.count(),
            "recent_submissions": visible_submissions.select_related("intern", "task").order_by("-submitted_at")[:6],
            "announcements": visible_announcements[:4],
        }
    elif role == "HR":
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if can_view_all_programs(request.user):
            visible_tasks = Task.objects.filter(is_published=True)
            visible_announcements = Announcement.objects.filter(published=True, audience__in=["ALL", "HR"])
        elif program:
            task_scope = Q(program=program, batch__isnull=True)
            if batch:
                task_scope |= Q(batch=batch)
            visible_tasks = Task.objects.filter(task_scope, is_published=True)
            visible_announcements = announcements_for_member(request.user, "HR")
        else:
            visible_tasks = Task.objects.none()
            visible_announcements = Announcement.objects.none()
        context = {
            "role": role,
            "can_manage_tasks": False,
            "task_count": visible_tasks.count(),
            "announcements": visible_announcements[:4],
        }
    else:
        tasks_qs = tasks_for_member(request.user).filter(is_published=True).filter(models_q_for_user(request.user))
        subs = Submission.objects.filter(intern=request.user, task__in=tasks_for_member(request.user))
        approved_points = subs.filter(status="APPROVED").aggregate(total=Sum("awarded_points"))["total"] or 0
        assigned_count = tasks_qs.count()
        completed = subs.filter(status="APPROVED").count()
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        attendance_scope = Q(program=program, batch__isnull=True) if program else Q(pk__in=[])
        if batch:
            attendance_scope |= Q(batch=batch)
        total_days = Attendance.objects.filter(intern=request.user).filter(attendance_scope).count()
        present_days = Attendance.objects.filter(intern=request.user, status="PRESENT").filter(attendance_scope).count()
        context = {
            "role": role, "can_manage_tasks": False, "tasks": tasks_qs[:5], "assigned_count": assigned_count,
            "completed_count": completed, "pending_count": subs.filter(status__in=["SUBMITTED", "IN_REVIEW"]).count(),
            "points": approved_points,
            "attendance_percent": round(present_days * 100 / total_days) if total_days else 0,
            "announcements": announcements_for_member(request.user, "INTERN")[:4],
            "recent_submissions": subs.select_related("task")[:4],
        }
    return render(request, "portal/dashboard.html", context)



@login_required
def core_team_dashboard(request):
    """Separate internal workspace for manually-created CME core team accounts."""
    role = role_of(request.user)
    if role not in CORE_TEAM_ACCESS_ROLES and not request.user.is_superuser:
        return HttpResponseForbidden("This workspace is reserved for CME Core Team members and authorized leadership.")

    if can_view_all_programs(request.user):
        members = User.objects.filter(profile__role="CORE_TEAM", is_active=True)
        visible_tasks = Task.objects.all()
        visible_submissions = Submission.objects.all()
        visible_announcements = Announcement.objects.filter(published=True, audience="ALL")
    else:
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        members = User.objects.filter(profile__role="CORE_TEAM", is_active=True, profile__assigned_program=program) if program else User.objects.none()
        task_scope = Q(program=program, batch__isnull=True) if program else Q(pk__in=[])
        if batch:
            task_scope |= Q(batch=batch)
        visible_tasks = Task.objects.filter(task_scope)
        visible_submissions = Submission.objects.filter(task__in=visible_tasks)
        visible_announcements = announcements_for_member(request.user, "HR")
    members = members.select_related("profile").order_by("first_name", "username")
    context = {
        "role": role,
        "members": members,
        "member_count": members.count(),
        "active_tasks": visible_tasks.filter(is_published=True).count(),
        "submissions_count": visible_submissions.count(),
        "pending_submissions": visible_submissions.filter(status__in=["SUBMITTED", "IN_REVIEW"]).count(),
        "announcements": visible_announcements[:5],
        "is_leadership": role in {"ADMIN", "FOUNDER", "CO_FOUNDER"} or request.user.is_superuser,
    }
    return render(request, "portal/core_team.html", context)

def models_q_for_user(user):
    return Q(assigned_to__isnull=True) | Q(assigned_to=user)


FULL_PROGRAM_ACCESS_ROLES = {"ADMIN", "FOUNDER", "CO_FOUNDER"}


def assigned_program_for(user):
    try:
        return user.profile.assigned_program
    except Profile.DoesNotExist:
        return None


def assigned_batch_for(user):
    try:
        return user.profile.assigned_batch
    except Profile.DoesNotExist:
        return None


def tasks_for_member(user):
    """Return only the program/batch workspace assigned to this member."""
    program = assigned_program_for(user)
    batch = assigned_batch_for(user)
    if not program:
        return Task.objects.none()
    scoped = Q(program=program, batch__isnull=True)
    if batch:
        scoped |= Q(batch=batch)
    return Task.objects.filter(scoped)


def announcements_for_member(user, audience):
    program = assigned_program_for(user)
    batch = assigned_batch_for(user)
    scoped = Q(program__isnull=True, batch__isnull=True)
    if program:
        scoped |= Q(program=program, batch__isnull=True)
    if batch:
        scoped |= Q(batch=batch)
    return Announcement.objects.filter(
        scoped, published=True, audience__in=["ALL", audience]
    ).distinct()


def can_view_all_programs(user):
    return user.is_superuser or role_of(user) in FULL_PROGRAM_ACCESS_ROLES


@login_required
def tasks(request):
    role = role_of(request.user)
    if can_manage_tasks(request.user):
        if can_view_all_programs(request.user):
            task_list = Task.objects.all()
            submissions = Submission.objects.select_related("intern", "task").all()
        else:
            program = assigned_program_for(request.user)
            batch = assigned_batch_for(request.user)
            scoped = Q(program=program, batch__isnull=True) if program else Q(pk__in=[])
            if batch:
                scoped |= Q(batch=batch)
            task_list = Task.objects.filter(scoped)
            submissions = Submission.objects.select_related("intern", "task").filter(task__in=task_list)
    else:
        task_list = Task.objects.filter(is_published=True)
        if role == "INTERN":
            task_list = tasks_for_member(request.user).filter(is_published=True).filter(models_q_for_user(request.user))
        else:
            program = assigned_program_for(request.user)
            batch = assigned_batch_for(request.user)
            if program:
                scoped = Q(program=program, batch__isnull=True)
                if batch:
                    scoped |= Q(batch=batch)
                task_list = task_list.filter(scoped)
            else:
                task_list = Task.objects.none()
        submissions = Submission.objects.filter(intern=request.user) if role == "INTERN" else Submission.objects.none()
    task_list = list(task_list.distinct())
    if role == "INTERN":
        task_ids = [task.id for task in task_list]
        submissions = Submission.objects.filter(intern=request.user, task_id__in=task_ids).select_related("task").order_by("-submitted_at")
        submission_by_task = {}
        for submission in submissions:
            submission_by_task.setdefault(submission.task_id, submission)
        for task in task_list:
            task.user_submission = submission_by_task.get(task.id)
    return render(request, "portal/tasks.html", {
        "tasks": task_list, "submissions": submissions, "role": role,
        "can_manage_tasks": can_manage_tasks(request.user),
    })


@login_required
def task_create(request):
    if not can_manage_tasks(request.user):
        return HttpResponseForbidden("Only the Founder, Intern Head, or Administrator can create tasks.")
    if not can_view_all_programs(request.user) and not assigned_program_for(request.user):
        return HttpResponseForbidden("Your account must be assigned to a program before managing program tasks.")
    form = TaskForm(request.POST or None, user=request.user)
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
    if not can_view_all_programs(request.user):
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if not program or not (task.program_id == program.id and task.batch_id is None or batch and task.batch_id == batch.id):
            raise Http404
    form = TaskForm(request.POST or None, instance=task, user=request.user)
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
    allowed_task_ids = tasks_for_member(request.user).values_list("id", flat=True)
    if task.id not in allowed_task_ids:
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
    if not can_view_all_programs(request.user):
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if not program or not (submission.task.program_id == program.id and submission.task.batch_id is None or batch and submission.task.batch_id == batch.id):
            raise Http404
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
    if role == "INTERN":
        items = announcements_for_member(request.user, audience)
    elif can_view_all_programs(request.user):
        items = Announcement.objects.filter(published=True)
    else:
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        scoped = Q(program__isnull=True, batch__isnull=True)
        if program:
            scoped |= Q(program=program, batch__isnull=True)
        if batch:
            scoped |= Q(batch=batch)
        items = Announcement.objects.filter(scoped, published=True, audience__in=["ALL", audience]).distinct()
    return render(request, "portal/announcements.html", {"announcements": items})


@login_required
def attendance(request):
    role = role_of(request.user)
    if role == "INTERN":
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if program:
            scoped = Q(program=program, batch__isnull=True)
            if batch:
                scoped |= Q(batch=batch)
            records = Attendance.objects.filter(intern=request.user).filter(scoped)
        else:
            records = Attendance.objects.none()
    elif can_view_all_programs(request.user):
        records = Attendance.objects.select_related("intern", "recorded_by").all()
    else:
        program = assigned_program_for(request.user)
        if program:
            scoped = Q(program=program, batch__isnull=True)
            if batch:
                scoped |= Q(batch=batch)
            records = Attendance.objects.select_related("intern", "recorded_by").filter(intern__profile__assigned_program=program).filter(scoped)
        else:
            records = Attendance.objects.none()
    return render(request, "portal/attendance.html", {"records": records, "role": role})


@login_required
def certificates(request):
    role = role_of(request.user)
    if role == "INTERN":
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if program:
            scoped = Q(program=program, batch__isnull=True)
            if batch:
                scoped |= Q(batch=batch)
            items = Certificate.objects.filter(intern=request.user).filter(scoped)
        else:
            items = Certificate.objects.none()
    elif can_view_all_programs(request.user):
        items = Certificate.objects.select_related("intern").all()
    else:
        program = assigned_program_for(request.user)
        batch = assigned_batch_for(request.user)
        if program:
            scoped = Q(program=program, batch__isnull=True)
            if batch:
                scoped |= Q(batch=batch)
            items = Certificate.objects.select_related("intern").filter(scoped)
        else:
            items = Certificate.objects.none()
    return render(request, "portal/certificates.html", {"certificates": items, "role": role})


def verify_certificate(request, code):
    certificate = get_object_or_404(Certificate, certificate_code=code, is_issued=True)
    return render(request, "portal/verify.html", {"certificate": certificate})


@login_required
def program_create(request):
    if not can_view_all_programs(request.user):
        return HttpResponseForbidden("Only CME leadership can manage all internship programs.")
    form = InternshipProgramForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        program = form.save()
        messages.success(request, f'Program "{program.title}" created. Add its first batch when ready.')
        return redirect("programs")
    return render(request, "portal/program_form.html", {
        "form": form, "page_title": "Create internship program",
        "button_label": "Create program", "is_edit": False,
    })


@login_required
def program_edit(request, program_id):
    if not can_view_all_programs(request.user):
        return HttpResponseForbidden("Only CME leadership can manage all internship programs.")
    program = get_object_or_404(InternshipProgram, pk=program_id)
    form = InternshipProgramForm(request.POST or None, instance=program)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Program details updated.")
        return redirect("programs")
    return render(request, "portal/program_form.html", {
        "form": form, "program": program, "page_title": "Edit internship program",
        "button_label": "Save changes", "is_edit": True,
    })


@login_required
def batch_create(request, program_id):
    if not can_view_all_programs(request.user):
        return HttpResponseForbidden("Only CME leadership can manage program batches.")
    program = get_object_or_404(InternshipProgram, pk=program_id)
    form = InternshipBatchForm(request.POST or None, program=program)
    if request.method == "POST" and form.is_valid():
        batch = form.save(commit=False)
        batch.program = program
        batch.save()
        messages.success(request, f'Batch "{batch.name}" created for {program.title}.')
        return redirect("programs")
    return render(request, "portal/batch_form.html", {
        "form": form, "program": program, "page_title": "Create program batch",
        "button_label": "Create batch",
    })


@login_required
def programs(request):
    """Show every program to leadership and only the assigned program to participants."""
    role = role_of(request.user)
    full_access = can_view_all_programs(request.user)
    assigned_program = assigned_program_for(request.user)
    if full_access:
        program_list = InternshipProgram.objects.prefetch_related("batches").all()
    elif assigned_program:
        program_list = InternshipProgram.objects.filter(pk=assigned_program.pk).prefetch_related("batches")
    else:
        program_list = InternshipProgram.objects.none()

    return render(request, "portal/programs.html", {
        "programs": program_list,
        "role": role,
        "can_manage_programs": full_access,
        "assigned_program": assigned_program,
        "assigned_batch": assigned_batch_for(request.user),
        "needs_assignment": role == "INTERN" and assigned_program is None,
    })
