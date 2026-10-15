"""
Drishti AI — Authentication & Session Flow Regression Test Suite
Validates:
1. Unauthenticated page requests (/admin, /faculty, /student) redirect to /login?next=... (HTTP 302).
2. Unauthenticated API requests (/api/*, /auth/*) return HTTP 401 JSON.
3. Login sets session cookie and returns user role/permissions.
4. Authenticated admin can access /admin (HTTP 200 HTML).
5. Already-authenticated users visiting /login are redirected.
6. Role-based restrictions prevent unauthorized access.
7. CSRF protection enforces valid token on state mutations.
"""
import os
import sys
import unittest
from urllib.parse import urlparse, parse_qs

# Ensure backend/ is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app_flask import app, socketio
import database


class TestAuthFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        database.init_db()
        database.seed_defaults()
        cls.app = app

    def setUp(self):
        self.client = self.app.test_client()

    def test_01_unauthenticated_admin_page_redirects_to_login(self):
        """GET /admin by a browser must redirect to /login?next=%2Fadmin (HTTP 302), NOT return 401 JSON."""
        res = self.client.get('/admin', headers={'Accept': 'text/html,application/xhtml+xml'})
        self.assertEqual(res.status_code, 302)
        parsed = urlparse(res.headers.get('Location'))
        self.assertEqual(parsed.path, '/login')
        params = parse_qs(parsed.query)
        self.assertEqual(params.get('next'), ['/admin'])

    def test_02_unauthenticated_faculty_and_student_redirect(self):
        """GET /faculty and /student by browser must redirect to /login with appropriate next parameter."""
        res_fac = self.client.get('/faculty', headers={'Accept': 'text/html'})
        self.assertEqual(res_fac.status_code, 302)
        self.assertIn('/login?next=', res_fac.headers.get('Location'))

        res_stud = self.client.get('/student', headers={'Accept': 'text/html'})
        self.assertEqual(res_stud.status_code, 302)
        self.assertIn('/login?next=', res_stud.headers.get('Location'))

    def test_03_unauthenticated_api_endpoints_return_401_json(self):
        """Unauthenticated requests to API endpoints must return HTTP 401 JSON, NOT redirect."""
        endpoints = [
            ('/api/students', 'GET'),
            ('/api/attendance', 'GET'),
            ('/api/users', 'GET'),
            ('/api/recognize_frame', 'POST'),
            ('/auth/change-password', 'POST'),
        ]
        for ep, method in endpoints:
            if method == 'GET':
                res = self.client.get(ep, headers={'Accept': 'application/json'})
            else:
                res = self.client.post(ep, json={}, headers={'Accept': 'application/json'})

            self.assertEqual(res.status_code, 401, f"Expected 401 for {method} {ep}")
            data = res.get_json()
            self.assertIsNotNone(data, f"Response should be JSON for {method} {ep}")
            self.assertFalse(data.get('success'))
            self.assertEqual(data.get('error'), 'authentication_required')

    def test_04_successful_admin_login_and_session_persistence(self):
        """Admin login creates a valid session, sets session cookie, and allows access to protected pages."""
        # 1. Login with demo admin credentials
        login_res = self.client.post('/auth/login', json={'username': 'admin', 'password': 'admin123'})
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data['success'])
        self.assertEqual(login_data['user']['role'], 'super_admin')

        # 2. Verify /auth/me returns authenticated state
        me_res = self.client.get('/auth/me')
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.get_json()
        self.assertTrue(me_data['authenticated'])
        self.assertEqual(me_data['user']['username'], 'admin')

        # 3. Access protected /admin page with active session
        admin_page_res = self.client.get('/admin')
        self.assertEqual(admin_page_res.status_code, 200)
        self.assertIn(b'Drishti AI', admin_page_res.data)

    def test_05_authenticated_user_visiting_login_redirects(self):
        """When an authenticated user visits /login or /login?next=/admin, they are redirected."""
        self.client.post('/auth/login', json={'username': 'admin', 'password': 'admin123'})

        # Visit /login?next=/admin
        res = self.client.get('/login?next=/admin')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/admin')

        # Visit /login without next
        res_plain = self.client.get('/login')
        self.assertEqual(res_plain.status_code, 302)
        self.assertEqual(res_plain.headers.get('Location'), '/')

    def test_06_student_cannot_access_admin_panel(self):
        """A logged-in student accessing /admin must be redirected away from admin panel."""
        self.client.post('/auth/login', json={'username': 'student', 'password': 'student123'})

        # Attempt to access /admin page
        res = self.client.get('/admin', headers={'Accept': 'text/html'})
        # Should redirect to / (which sends student to /student)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get('Location'), '/')

    def test_07_csrf_protection_and_cookie_generation(self):
        """State-changing requests require matching X-CSRFToken header matching session token."""
        # 1. Login
        self.client.post('/auth/login', json={'username': 'admin', 'password': 'admin123'})

        # 2. Mutation without CSRF token must fail with 403
        bad_post = self.client.post('/api/attendance/1/override', json={'status': 'Late', 'reason': 'Test'})
        self.assertEqual(bad_post.status_code, 403)
        self.assertEqual(bad_post.get_json().get('error'), 'csrf_failed')

        # 3. Read csrf_token cookie and send header
        with self.client.session_transaction() as sess:
            token = sess.get('_csrf_token')
        self.assertIsNotNone(token)

        good_post = self.client.post(
            '/api/attendance/1/override',
            json={'status': 'Late', 'reason': 'Testing valid token'},
            headers={'X-CSRFToken': token}
        )
        # Should not be csrf_failed (may be 404 or success depending on record existence)
        self.assertNotEqual(good_post.status_code, 403)
        if good_post.status_code != 200:
            self.assertNotEqual(good_post.get_json().get('error'), 'csrf_failed')


if __name__ == '__main__':
    unittest.main()
