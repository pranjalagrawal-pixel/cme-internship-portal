from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0002_profile_role_length")]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(choices=[("ADMIN", "Administrator"), ("FOUNDER", "Founder"), ("INTERN_HEAD", "Intern Head"), ("HR", "HR / Evaluator"), ("CORE_TEAM", "Core Team"), ("INTERN", "Intern")], default="INTERN", max_length=16),
        ),
    ]
