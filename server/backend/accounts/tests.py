import io
import os
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CollegeSettings, Department, Subject, User
from labs.models import Practical, Submission
from labs.secure_browser import compute_signature, is_secure_browser_request


class SecurityHardeningTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=open(os.devnull, "w"))
        cache.clear()
        self.client = APIClient()
        self.student1 = User.objects.get(username="student1")
        self.student2 = User.objects.get(username="student2")
        self.teacher = User.objects.get(username="teacher")
        self.admin = User.objects.get(username="admin")

    def login_as(self, username, password):
        res = self.client.post("/api/auth/login/", {"username": username, "password": password}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        data = res.json()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        return data

    def sign_headers(self, method: str, path: str, key: str = None, ts: str = None):
        key = key or settings.SECURE_BROWSER_KEY
        ts = ts or str(int(time.time()))
        sig = compute_signature(key, ts, method, path)
        return {
            "HTTP_X_LABORA_TS": ts,
            "HTTP_X_LABORA_SIGNATURE": sig,
            "HTTP_X_LABORA_CLIENT": "secure-browser/1.0.0",
        }

    # =========================================================================
    # 1. JWT Authentication, Rotation & Blacklisting Tests
    # =========================================================================

    def test_refresh_token_rotation_and_old_token_blacklisting(self):
        """When a refresh token is used, a new refresh token is issued and the old one is blacklisted."""
        tokens = self.login_as("student1", "student123")
        old_refresh = tokens["refresh"]

        # First refresh: succeeds and returns new access + rotated refresh
        res = self.client.post("/api/auth/refresh/", {"refresh": old_refresh}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_data = res.json()
        self.assertIn("access", new_data)
        self.assertIn("refresh", new_data)
        new_refresh = new_data["refresh"]
        self.assertNotEqual(old_refresh, new_refresh)

        # Attempt to reuse the old rotated refresh token: MUST fail with 401
        reuse_res = self.client.post("/api/auth/refresh/", {"refresh": old_refresh}, format="json")
        self.assertEqual(reuse_res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("token_not_valid", str(reuse_res.content))

        # The new rotated refresh token works
        second_res = self.client.post("/api/auth/refresh/", {"refresh": new_refresh}, format="json")
        self.assertEqual(second_res.status_code, status.HTTP_200_OK)

    def test_server_side_logout_blacklists_token(self):
        """Logging out via /api/auth/logout/ blacklists the refresh token immediately."""
        tokens = self.login_as("student1", "student123")
        refresh = tokens["refresh"]

        # Call logout
        logout_res = self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Subsequent refresh attempt with the logged-out refresh token MUST fail
        refresh_res = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_or_expired_refresh_token_rejected(self):
        """Malformed or random strings passed as refresh tokens return HTTP 401."""
        res = self.client.post("/api/auth/refresh/", {"refresh": "not-a-valid-jwt-token"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # =========================================================================
    # 2. Content Security Policy & Modern Security Headers Tests
    # =========================================================================

    def test_security_headers_present_on_responses(self):
        """All responses include nosniff, DENY, strict referrer, and a compliant CSP."""
        res = self.client.get("/api/client-status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("camera=()", res.headers.get("Permissions-Policy", ""))

        csp = res.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("style-src 'self' 'unsafe-inline'", csp)
        self.assertIn("worker-src 'self' blob:", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)

    # =========================================================================
    # 3. Secure Browser Signature Verification & Anti-Replay Tests
    # =========================================================================

    def test_valid_secure_browser_signature_accepted(self):
        """Valid HMAC signature with current timestamp is recognized."""
        path = "/api/client-status/"
        headers = self.sign_headers("GET", path)
        res = self.client.get(path, **headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["secure_browser"])

    def test_invalid_secure_browser_signature_rejected(self):
        """Forged or tampered signature is rejected."""
        path = "/api/client-status/"
        headers = self.sign_headers("GET", path, key="wrong-secret-key")
        res = self.client.get(path, **headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.json()["secure_browser"])

    def test_skewed_secure_browser_timestamp_rejected(self):
        """Signatures with timestamps beyond the skew window (> 300s) are rejected."""
        path = "/api/client-status/"
        stale_ts = str(int(time.time()) - 400)
        headers = self.sign_headers("GET", path, ts=stale_ts)
        res = self.client.get(path, **headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.json()["secure_browser"])

    def test_secure_browser_signature_replay_prevention(self):
        """Replaying the exact same signature within the skew window is blocked."""
        path = "/api/client-status/"
        headers = self.sign_headers("GET", path)

        # First request with this signature: succeeds
        res1 = self.client.get(path, **headers)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertTrue(res1.json()["secure_browser"])

        # Second request with the identical (replayed) signature: MUST be rejected
        res2 = self.client.get(path, **headers)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertFalse(res2.json()["secure_browser"])

    def test_secure_browser_enforcement_for_students(self):
        """When students_secure_browser_only is enabled, normal browser student login is blocked."""
        cs = CollegeSettings.load()
        cs.students_secure_browser_only = True
        cs.save()

        # Student login from normal browser: blocked with 403
        res = self.client.post("/api/auth/login/", {"username": "student1", "password": "student123"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.json()["code"], "secure_browser_required")

        # Teacher login from normal browser: permitted
        t_res = self.client.post("/api/auth/login/", {"username": "teacher", "password": "teacher123"}, format="json")
        self.assertEqual(t_res.status_code, status.HTTP_200_OK)

        # Student login with Secure Browser headers: permitted
        path = "/api/auth/login/"
        headers = self.sign_headers("POST", path)
        s_res = self.client.post(path, {"username": "student1", "password": "student123"}, format="json", **headers)
        self.assertEqual(s_res.status_code, status.HTTP_200_OK)

    # =========================================================================
    # 4. Role-Based Permissions & Cross-Student Isolation Tests
    # =========================================================================

    def test_student_cannot_access_other_student_execution(self):
        """Student 1 cannot access execution details belonging to Student 2."""
        py_prac = Practical.objects.get(language="python")
        sub2 = Submission.objects.create(practical=py_prac, student=self.student2, code="print('student2')")
        from labs.models import Execution
        ex2 = Execution.objects.create(submission=sub2, code="print('student2')", stdin="", status="Accepted")

        # Student 1 logs in and attempts to access Student 2's execution
        self.login_as("student1", "student123")
        res = self.client.get(f"/api/executions/{ex2.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_access_unassigned_practical(self):
        """Student cannot access practical in a subject they are not enrolled in."""
        unassigned_subject = Subject.objects.create(
            name="Unenrolled Subject", code="UN101", semester=1, academic_year="2026-27",
            department=Department.objects.first()
        )
        unassigned_prac = Practical.objects.create(
            subject=unassigned_subject, experiment_no=1, title="Test", aim="Aim",
            question="Q", language="python", starter_code="", is_published=True
        )

        self.login_as("student1", "student123")
        res = self.client.get(f"/api/workspace/{unassigned_prac.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_call_teacher_approve_endpoint(self):
        """Students cannot approve submissions or access teacher review endpoints."""
        py_prac = Practical.objects.get(language="python")
        sub = Submission.objects.create(practical=py_prac, student=self.student1, code="print('code')")

        self.login_as("student1", "student123")
        approve_res = self.client.post(f"/api/submissions/{sub.id}/approve/", {"result": "OK"}, format="json")
        self.assertEqual(approve_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_set_password_endpoint(self):
        """Admin can reset a user password via POST /api/users/<id>/set-password/."""
        self.login_as("admin", "admin123")
        res = self.client.post(f"/api/users/{self.student1.id}/set-password/", {"password": "newpassword123"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Student can now log in with the new password
        self.client.credentials()  # clear credentials
        login_res = self.client.post("/api/auth/login/", {"username": "student1", "password": "newpassword123"}, format="json")
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)

    def test_payload_size_limits_enforced(self):
        """Oversized CSV or logo uploads return HTTP 400 Bad Request."""
        self.login_as("admin", "admin123")

        # Create dummy file > 5 MB
        oversized_csv = SimpleUploadedFile("big.csv", b"x" * (6 * 1024 * 1024), content_type="text/csv")
        res = self.client.post("/api/users/import/", {"file": oversized_csv}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("File too large", res.json()["detail"])

        # Oversized logo > 2 MB
        oversized_logo = SimpleUploadedFile("big_logo.png", b"x" * (3 * 1024 * 1024), content_type="image/png")
        logo_res = self.client.patch("/api/college-settings/", {"logo": oversized_logo}, format="multipart")
        self.assertEqual(logo_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Logo file too large", logo_res.json()["detail"])

    # =========================================================================
    # 5. Rate Limiting Tests
    # =========================================================================

    def test_login_rate_limiting(self):
        """Exceeding LOGIN_RATE throttles further requests with HTTP 429."""
        from accounts.views import LoginThrottle
        with override_settings(REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {
                **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
                "login": "3/min",
            }
        }):
            # Dynamically clear throttle rate cache on the class
            LoginThrottle.rate = "3/min"
            cache.clear()
            for i in range(3):
                r = self.client.post("/api/auth/login/", {"username": "bad", "password": "bad"}, format="json")
                self.assertNotEqual(r.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

            throttled_res = self.client.post("/api/auth/login/", {"username": "bad", "password": "bad"}, format="json")
            self.assertEqual(throttled_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            LoginThrottle.rate = None  # reset
