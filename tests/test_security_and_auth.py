"""
Drishti AI — Security, RBAC & Protection Verification Suite
Tests:
1. Rejection of unauthenticated access to biometric, student, and attendance data.
2. CSRF token validation on state-changing API endpoints.
3. RBAC isolation (student role forbidden from administrative routes).
4. Brute-force account lockout (5 failed attempts).
5. Production administrator password security constraint.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app_flask import app
import database


class TestSecurityAndAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        database.init_db()
        database.seed_defaults()
        cls.client = app.test_client()

    def test_01_unauthenticated_student_data_blocked(self):
        """Ensure /api/students cannot be accessed without login."""
        res = self.client.get('/api/students')
        # Expect 401 Unauthorized or redirect to /login
        self.assertIn(res.status_code, [401, 403, 302])

    def test_02_unauthenticated_attendance_blocked(self):
        """Ensure /api/attendance cannot be accessed without login."""
        res = self.client.get('/api/attendance')
        self.assertIn(res.status_code, [401, 403, 302])

    def test_03_unauthenticated_user_management_blocked(self):
        """Ensure /api/users cannot be accessed without login."""
        res = self.client.get('/api/users')
        self.assertIn(res.status_code, [401, 403, 302])

    def test_04_unauthenticated_frame_recognition_blocked(self):
        """Ensure /api/recognize_frame cannot be accessed without login."""
        res = self.client.post('/api/recognize_frame', json={'frame': 'test'})
        self.assertIn(res.status_code, [401, 403, 302])

    def test_05_csrf_protection_on_mutating_requests(self):
        """Ensure POST requests without valid CSRF header are rejected with 403."""
        # Log in first to get an active authenticated session
        login_res = self.client.post('/auth/login', json={'username': 'admin', 'password': 'admin123'})
        self.assertEqual(login_res.status_code, 200)

        # Mutating request without X-CSRFToken header must fail
        post_res = self.client.post('/api/attendance/1/override', json={'status': 'Late', 'reason': 'Test'})
        self.assertEqual(post_res.status_code, 403)
        self.assertEqual(post_res.get_json().get('error'), 'csrf_failed')

    def test_06_student_role_forbidden_from_admin_routes(self):
        """Ensure student account gets 403 when trying to access admin endpoints."""
        student_client = app.test_client()
        # Login as student
        login_res = student_client.post('/auth/login', json={'username': 'student', 'password': 'student123'})
        self.assertEqual(login_res.status_code, 200)

        # Try to view all users (/api/users requires users.view permission)
        res = student_client.get('/api/users')
        self.assertEqual(res.status_code, 403)

    def test_07_brute_force_lockout(self):
        """Ensure account locks after 5 consecutive failed login attempts."""
        bf_client = app.test_client()
        for _ in range(5):
            res = bf_client.post('/auth/login', json={'username': 'admin', 'password': 'wrong_password_attempt'})
            self.assertEqual(res.status_code, 401)

        # 6th attempt should return account_locked
        res6 = bf_client.post('/auth/login', json={'username': 'admin', 'password': 'any_password'})
        self.assertEqual(res6.status_code, 403)
        self.assertEqual(res6.get_json().get('error'), 'account_locked')

        # Admin reset for subsequent tests
        user = database.get_user_by_username('admin')
        if user:
            database.unlock_user(user['id'])

    def test_08_production_admin_password_enforcement(self):
        """Ensure production environment strictly rejects default admin123."""
        orig_env = os.environ.get('FLASK_ENV')
        orig_pass = os.environ.get('ADMIN_PASSWORD')

        try:
            os.environ['FLASK_ENV'] = 'production'
            os.environ['ADMIN_PASSWORD'] = 'admin123'  # Insecure default

            with self.assertRaises(RuntimeError) as ctx:
                database.seed_defaults()
            self.assertIn('CRITICAL SECURITY REQUIREMENT', str(ctx.exception))
        finally:
            if orig_env is not None:
                os.environ['FLASK_ENV'] = orig_env
            else:
                os.environ.pop('FLASK_ENV', None)
            if orig_pass is not None:
                os.environ['ADMIN_PASSWORD'] = orig_pass
            else:
                os.environ.pop('ADMIN_PASSWORD', None)


if __name__ == '__main__':
    unittest.main()
