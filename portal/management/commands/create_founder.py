import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from portal.models import Profile


class Command(BaseCommand):
    help = "Create or update the configured CME founder account when credentials are provided."

    def handle(self, *args, **options):
        password = os.getenv("CME_FOUNDER_PASSWORD", "")
        if not password:
            self.stdout.write(self.style.WARNING(
                "CME_FOUNDER_PASSWORD is not set; founder bootstrap skipped."
            ))
            return

        User = get_user_model()
        username = os.getenv("CME_FOUNDER_USERNAME", "pranjal26").strip()
        email = os.getenv("CME_FOUNDER_EMAIL", "").strip()
        if not username:
            raise CommandError("CME_FOUNDER_USERNAME cannot be empty.")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": "CME", "last_name": "Founder"},
        )
        if email and user.email != email:
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        Profile.objects.update_or_create(user=user, defaults={"role": "FOUNDER"})
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Founder account {action} from environment configuration."))
