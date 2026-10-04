from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0003_profile_core_team_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="InternshipProgram",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("domain", models.CharField(max_length=80)),
                ("short_description", models.CharField(max_length=280)),
                ("description", models.TextField()),
                ("duration_weeks", models.PositiveSmallIntegerField(default=4)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("eligibility", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("OPEN", "Open for applications"), ("ONGOING", "Ongoing"), ("COMPLETED", "Completed")], default="DRAFT", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
