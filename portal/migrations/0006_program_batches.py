# Additive program/batch fields. Existing users, tasks and historical records are preserved.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0005_submission_attachment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(choices=[("ADMIN", "Administrator"), ("FOUNDER", "Founder"), ("CO_FOUNDER", "Co-Founder"), ("INTERN_HEAD", "Intern Head"), ("HR", "HR / Evaluator"), ("CORE_TEAM", "Core Team"), ("INTERN", "Intern")], default="INTERN", max_length=16),
        ),
        migrations.CreateModel(
            name="InternshipBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=40)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("PLANNED", "Planned"), ("ACTIVE", "Active"), ("COMPLETED", "Completed"), ("ARCHIVED", "Archived")], default="PLANNED", max_length=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="batches", to="portal.internshipprogram")),
            ],
            options={"ordering": ["-start_date", "name"]},
        ),
        migrations.AddConstraint(
            model_name="internshipbatch",
            constraint=models.UniqueConstraint(fields=("program", "code"), name="unique_batch_code_per_program"),
        ),
        migrations.AddField(
            model_name="profile",
            name="assigned_program",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_profiles", to="portal.internshipprogram"),
        ),
        migrations.AddField(
            model_name="profile",
            name="assigned_batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_profiles", to="portal.internshipbatch"),
        ),
        migrations.AddField(
            model_name="task",
            name="program",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tasks", to="portal.internshipprogram"),
        ),
        migrations.AddField(
            model_name="task",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tasks", to="portal.internshipbatch"),
        ),
        migrations.AddField(
            model_name="announcement",
            name="program",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="announcements", to="portal.internshipprogram"),
        ),
        migrations.AddField(
            model_name="announcement",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="announcements", to="portal.internshipbatch"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="program",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="certificates", to="portal.internshipprogram"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="certificates", to="portal.internshipbatch"),
        ),
        migrations.AddField(
            model_name="attendance",
            name="program",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attendance_records", to="portal.internshipprogram"),
        ),
        migrations.AddField(
            model_name="attendance",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attendance_records", to="portal.internshipbatch"),
        ),
    ]
