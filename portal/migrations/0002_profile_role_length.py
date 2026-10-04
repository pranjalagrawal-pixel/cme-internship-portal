from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("portal", "0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Administrator"),
                    ("FOUNDER", "Founder"),
                    ("INTERN_HEAD", "Intern Head"),
                    ("HR", "HR / Evaluator"),
                    ("INTERN", "Intern"),
                ],
                default="INTERN",
                max_length=16,
            ),
        ),
    ]
