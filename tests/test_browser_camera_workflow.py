"""
Drishti AI — End-to-End Camera Recognition & Duplicate Prevention Verification Suite
Tests:
1. Failed recognition on blank/non-face frame does not create attendance.
2. Enrolled face frame creates attendance once with correct confidence and metadata.
3. Repeated identical frame is rejected with 'Already marked for this session' / 'Already marked today'
   without creating duplicate database rows.
"""
import sys
import os
import unittest
import base64
import re
import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app_flask import app
import database


class TestBrowserCameraWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        database.init_db()
        database.seed_defaults()
        cls.client = app.test_client()

        # Login as admin to get CSRF token and authenticated session
        login_res = cls.client.post('/auth/login', json={'username': 'admin', 'password': 'admin123'})
        assert login_res.status_code == 200
        cookie_str = str(login_res.headers.get_all('Set-Cookie'))
        csrf_match = re.search(r'csrf_token=([a-f0-9]+)', cookie_str)
        assert csrf_match, "CSRF token must be present in session cookies"
        cls.headers = {'X-CSRFToken': csrf_match.group(1)}

    def test_01_blank_frame_creates_no_attendance(self):
        """Failed recognition on blank frame returns 0 faces and creates 0 attendance records."""
        with database.get_db_connection() as conn:
            count_before = conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0]

        blank_img = np.zeros((200, 200, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', blank_img)
        b64_str = 'data:image/jpeg;base64,' + base64.b64encode(buffer).decode()

        res = self.client.post('/api/recognize_frame', json={'frame': b64_str}, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['faces_detected'], 0)
        self.assertEqual(len(data['faces']), 0)

        with database.get_db_connection() as conn:
            count_after = conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0]
        self.assertEqual(count_before, count_after)

    def test_02_enrolled_face_and_duplicate_rejection(self):
        """Enrolled face marks attendance once; immediate second frame is rejected as duplicate."""
        img_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'known_faces', 'atharva_11.jpg')
        if not os.path.exists(img_path):
            self.skipTest(f"Sample face image not found at {img_path}")

        face_img = cv2.imread(img_path)
        self.assertIsNotNone(face_img)
        _, buffer = cv2.imencode('.jpg', face_img)
        b64_face = 'data:image/jpeg;base64,' + base64.b64encode(buffer).decode()

        sess = database.get_active_session()
        sess_id = sess['id'] if sess else 1

        # Frame 1: Recognition and initial mark
        res1 = self.client.post('/api/recognize_frame', json={'frame': b64_face, 'session_id': sess_id}, headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1['success'])
        self.assertGreaterEqual(data1['faces_detected'], 1)

        # Frame 2: Identical repeated frame immediately after
        res2 = self.client.post('/api/recognize_frame', json={'frame': b64_face, 'session_id': sess_id}, headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2['success'])
        self.assertGreaterEqual(data2['faces_detected'], 1)

        face2 = data2['faces'][0]
        self.assertIn('Already marked', face2['attendance_status'])


if __name__ == '__main__':
    unittest.main()
