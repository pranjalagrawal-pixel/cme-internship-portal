from django import forms
from .models import InternshipBatch, InternshipProgram, Submission, Task


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Username or email", "autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your password", "autocomplete": "current-password"}))


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["response_text", "attachment_url", "attachment"]
        widgets = {
            "response_text": forms.Textarea(attrs={"rows": 5, "placeholder": "Summarise your work, approach, and outcome..."}),
            "attachment_url": forms.URLInput(attrs={"placeholder": "https://... (optional)"}),
            "attachment": forms.ClearableFileInput(attrs={}),
        }

    def clean(self):
        cleaned = super().clean()
        response_text = (cleaned.get("response_text") or "").strip()
        attachment_url = (cleaned.get("attachment_url") or "").strip()
        attachment = cleaned.get("attachment")
        if not response_text and not attachment_url and not attachment:
            raise forms.ValidationError("Provide a work summary, a project link, or upload a file.")
        return cleaned


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "program", "batch", "domain", "priority", "points", "due_date", "assigned_to", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Build a responsive landing page"}),
            "description": forms.Textarea(attrs={"rows": 6, "placeholder": "Task requirements, deliverables and submission instructions..."}),
            "domain": forms.TextInput(attrs={"placeholder": "e.g. Web Development"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "assigned_to": forms.SelectMultiple(attrs={"class": "multi-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = self.fields["assigned_to"].queryset.filter(profile__role="INTERN", is_active=True).order_by("username")
        if user:
            try:
                user_role = user.profile.role
                assigned_program = user.profile.assigned_program
                assigned_batch = user.profile.assigned_batch
            except Exception:
                user_role, assigned_program, assigned_batch = "", None, None
        else:
            user_role, assigned_program, assigned_batch = "", None, None
        if user and not (user.is_superuser or user_role in {"ADMIN", "FOUNDER", "CO_FOUNDER"}):
            self.fields["program"].queryset = InternshipProgram.objects.filter(pk=assigned_program.pk) if assigned_program else InternshipProgram.objects.none()
            self.fields["batch"].queryset = InternshipBatch.objects.filter(program=assigned_program) if assigned_program else InternshipBatch.objects.none()
            if assigned_program:
                self.fields["program"].initial = assigned_program
            if assigned_batch:
                self.fields["batch"].initial = assigned_batch
            self.fields["program"].disabled = True
            self.fields["batch"].disabled = True
            if assigned_program:
                member_scope = {"profile__assigned_program": assigned_program}
                if assigned_batch:
                    member_scope["profile__assigned_batch"] = assigned_batch
                self.fields["assigned_to"].queryset = self.fields["assigned_to"].queryset.filter(**member_scope)
            else:
                self.fields["assigned_to"].queryset = self.fields["assigned_to"].queryset.none()
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].help_text = "Leave empty to make this task visible to all active interns."
        self.fields["points"].min_value = 0
        self.fields["points"].max_value = 10000


    def clean(self):
        cleaned = super().clean()
        program = cleaned.get("program")
        batch = cleaned.get("batch")
        if batch and program and batch.program_id != program.id:
            self.add_error("batch", "This batch belongs to a different program.")
        if batch and not program:
            cleaned["program"] = batch.program
        return cleaned


class SubmissionReviewForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["status", "evaluator_feedback", "awarded_points"]
        widgets = {
            "evaluator_feedback": forms.Textarea(attrs={"rows": 4, "placeholder": "Feedback for the intern..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["awarded_points"].min_value = 0
        self.fields["awarded_points"].max_value = self.instance.task.points if self.instance and self.instance.pk else 10000
        self.fields["awarded_points"].help_text = f"Maximum points for this task: {self.instance.task.points}" if self.instance and self.instance.pk else "Points awarded after review."

    def clean_awarded_points(self):
        points = self.cleaned_data["awarded_points"]
        if self.instance and self.instance.pk and points > self.instance.task.points:
            raise forms.ValidationError(f"Awarded points cannot exceed the task maximum of {self.instance.task.points}.")
        return points


class InternshipProgramForm(forms.ModelForm):
    class Meta:
        model = InternshipProgram
        fields = ["title", "domain", "short_description", "description", "duration_weeks", "start_date", "end_date", "eligibility", "status"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Web Development Internship"}),
            "domain": forms.TextInput(attrs={"placeholder": "e.g. Technology"}),
            "short_description": forms.TextInput(attrs={"placeholder": "A concise summary of this program"}),
            "description": forms.Textarea(attrs={"rows": 6, "placeholder": "Describe the program, learning outcomes and responsibilities..."}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "eligibility": forms.Textarea(attrs={"rows": 3, "placeholder": "Eligibility requirements (optional)"}),
        }

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be earlier than the start date.")
        return cleaned


class InternshipBatchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.program = kwargs.pop("program", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = InternshipBatch
        fields = ["name", "code", "start_date", "end_date", "status", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. October 2026 Cohort"}),
            "code": forms.TextInput(attrs={"placeholder": "e.g. WEB-OCT26"}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Internal notes (optional)"}),
        }

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be earlier than the start date.")
        code = cleaned.get("code")
        if self.program and code:
            duplicate = InternshipBatch.objects.filter(program=self.program, code__iexact=code)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error("code", "This batch code already exists in this program.")
        return cleaned
