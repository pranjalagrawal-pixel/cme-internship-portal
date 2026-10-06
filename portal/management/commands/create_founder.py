import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from portal.models import Profile


class Command(BaseCommand):
    help = "Create or update the permanent CME Founder account."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.getenv("CME_FOUNDER_USERNAME", "pranjal26")
        email = os.getenv(
            "CME_FOUNDER_EMAIL",
            "conceptmadeeasyclasses@gmail.com",
        )
        password = os.getenv("CME_FOUNDER_PASSWORD")

        if not password:
            self.stdout.write(
                self.style.ERROR(
                    "CME_FOUNDER_PASSWORD environment variable is missing."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        user.email = email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)

        profile.role = "FOUNDER"
        profile.save()

        action = "created" if created else "updated"

        self.stdout.write(
            self.style.SUCCESS(
                f"CME Founder account {action} successfully: {username}"
            )
        )