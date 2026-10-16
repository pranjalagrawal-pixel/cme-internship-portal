from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse, resolve, Resolver404
from .models import Profile, Task, Submission, InternshipProgram, InternshipBatch


class PortalTests(TestCase):
    def setUp(self):
        self.program = InternshipProgram.objects.create(
            title="Web Development", domain="Technology",
            short_description="Build web products", description="Program details",
            status="ONGOING",
        )
        self.batch = InternshipBatch.objects.create(
            program=self.program, name="Batch 01", code="WEB-01", status="ACTIVE",
        )
        self.user = User.objects.create_user(username="intern1", password="SafePass123!", first_name="Test", last_name="Intern")
        Profile.objects.create(user=self.user, role="INTERN", domain="Technology", assigned_program=self.program, assigned_batch=self.batch)
        self.manager = User.objects.create_user(username="internhead", password="SafePass123!")
        Profile.objects.create(user=self.manager, role="INTERN_HEAD", assigned_program=self.program, assigned_batch=self.batch)
        self.hr = User.objects.create_user(username="hr1", password="SafePass123!")
        Profile.objects.create(user=self.hr, role="HR")

    def test_profiles_for_different_roles_receive_unique_ids(self):
        ids = [self.user.profile.intern_id, self.manager.profile.intern_id, self.hr.profile.intern_id]
        self.assertTrue(all(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_home_loads(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_login_and_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "intern1", "password": "SafePass123!"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_public_self_registration_route_does_not_exist(self):
        with self.assertRaises(Resolver404):
            resolve("/register/")
        with self.assertRaises(Resolver404):
            resolve("/signup/")

    def test_intern_cannot_open_unassigned_task_submission_when_not_logged_in(self):
        task = Task.objects.create(title="Private task", description="Test", is_published=True)
        response = self.client.get(reverse("submit_task", args=[task.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_intern_cannot_create_task(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("task_create"))
        self.assertEqual(response.status_code, 403)

    def test_intern_head_can_create_task(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse("task_create"), {
            "title": "Create a landing page", "description": "Build the assigned page", "domain": "Web",
            "priority": "MEDIUM", "points": 20, "due_date": "", "is_published": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Task.objects.filter(title="Create a landing page", points=20).exists())

    def test_hr_cannot_award_points(self):
        task = Task.objects.create(title="Test task", description="Task description", points=20)
        submission = Submission.objects.create(task=task, intern=self.user, response_text="Done")
        self.client.force_login(self.hr)
        response = self.client.get(reverse("submission_review", args=[submission.id]))
        self.assertEqual(response.status_code, 403)

    def test_awarded_points_cannot_exceed_task_maximum(self):
        task = Task.objects.create(title="Test task", description="Task description", points=20, program=self.program, batch=self.batch)
        submission = Submission.objects.create(task=task, intern=self.user, response_text="Done")
        self.client.force_login(self.manager)
        response = self.client.post(reverse("submission_review", args=[submission.id]), {
            "status": "APPROVED", "evaluator_feedback": "Good work", "awarded_points": 21,
        })
        self.assertEqual(response.status_code, 200)
        submission.refresh_from_db()
        self.assertEqual(submission.awarded_points, 0)

    def test_intern_sees_only_assigned_program_and_batch_tasks(self):
        own = Task.objects.create(title="Own batch task", description="Scoped", program=self.program, batch=self.batch)
        second_batch = InternshipBatch.objects.create(
            program=self.program, name="Batch 02", code="WEB-02", status="ACTIVE",
        )
        other_same_program = Task.objects.create(title="Private same-program other-batch task", description="Not for this cohort", program=self.program, batch=second_batch)
        other_program = InternshipProgram.objects.create(
            title="Design", domain="Design", short_description="Design track",
            description="Other program", status="ONGOING",
        )
        other_batch = InternshipBatch.objects.create(
            program=other_program, name="Design Batch", code="DES-01", status="ACTIVE",
        )
        other = Task.objects.create(title="Private other batch task", description="Not for this intern", program=other_program, batch=other_batch)
        self.client.force_login(self.user)
        response = self.client.get(reverse("tasks"))
        self.assertContains(response, own.title)
        self.assertNotContains(response, other_same_program.title)
        self.assertNotContains(response, other.title)

    def test_intern_program_page_only_shows_assigned_program(self):
        other = InternshipProgram.objects.create(
            title="Design", domain="Design", short_description="Design track",
            description="Other program", status="ONGOING",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("programs"))
        self.assertContains(response, self.program.title)
        self.assertNotContains(response, other.title)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/"))
        self.assertTrue("_auth_user_id" in self.client.session)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
