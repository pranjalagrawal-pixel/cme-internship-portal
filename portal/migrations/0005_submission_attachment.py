from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0004_internshipprogram"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to="task_submissions/%Y/%m/"),
        ),
    ]
