from django import forms
from .models import Submission, Task


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"placeholder": "Username or email", "autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your password", "autocomplete": "current-password"}))


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["response_text", "attachment_url", "attachment"]
        widgets = {
            "response_text": forms.Textarea(
                attrs={
                    "rows": 8,
                    "placeholder": "Summarise your work, approach, and outcome...",
                }
            ),
            "attachment_url": forms.URLInput(
                attrs={
                    "placeholder": "https://... (optional)"
                }
            ),
            "attachment": forms.ClearableFileInput(attrs={}),
        }

    def clean(self):
        cleaned_data = super().clean()

        response_text = (
            cleaned_data.get("response_text") or ""
        ).strip()

        attachment_url = (
            cleaned_data.get("attachment_url") or ""
        ).strip()

        attachment = cleaned_data.get("attachment")

        if not response_text and not attachment_url and not attachment:
            raise forms.ValidationError(
                "Please provide a work summary, a project/document link, or upload a file."
            )

        return cleaned_data


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "domain", "priority", "points", "due_date", "assigned_to", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Build a responsive landing page"}),
            "description": forms.Textarea(attrs={"rows": 6, "placeholder": "Task requirements, deliverables and submission instructions..."}),
            "domain": forms.TextInput(attrs={"placeholder": "e.g. Web Development"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "assigned_to": forms.SelectMultiple(attrs={"class": "multi-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = (
            self.fields["assigned_to"]
            .queryset
            .exclude(profile__role="FOUNDER")
            .filter(is_active=True)
            .order_by("username")
        )

        self.fields["assigned_to"].required = False

        self.fields["assigned_to"].help_text = (
            "Select one or more active members. Founder cannot be assigned "
            "submission tasks. Leave empty to make the task available to "
            "all non-Founder members."
        )
        self.fields["points"].min_value = 0
        self.fields["points"].max_value = 10000


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
