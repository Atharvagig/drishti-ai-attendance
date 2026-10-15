"""
Test suite for database_mongo.py using mongomock.
Verifies all CRUD, auth, session, attendance duplicate prevention,
and analytics functions without external network dependencies.
"""
import sys
import os
import unittest
import numpy as np
import mongomock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import database_mongo as db_mongo


class TestDatabaseMongo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an in-memory mongomock database
        cls.client = mongomock.MongoClient()
        cls.db = cls.client['drishti_test_db']
        db_mongo.set_custom_db(cls.db)
        db_mongo.init_db(cls.db)
        db_mongo.seed_defaults(cls.db)

    def test_01_seed_defaults(self):
        depts = list(self.db.departments.find())
        self.assertGreaterEqual(len(depts), 6)
        admin = self.db.users.find_one({'username': 'admin'})
        self.assertIsNotNone(admin)
        self.assertEqual(admin['role'], 'super_admin')

    def test_02_add_and_get_student(self):
        success = db_mongo.add_student(
            student_id='TEST001',
            name='Test Student',
            department='AIDS',
            email='test@drishti.ai',
            semester=3
        )
        self.assertTrue(success)
        student = db_mongo.get_student_by_id('TEST001')
        self.assertIsNotNone(student)
        self.assertEqual(student['name'], 'Test Student')
        self.assertEqual(student['department'], 'AIDS')

        # Check auto-created user account
        user = db_mongo.get_user_by_username('TEST001')
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'student')

    def test_03_store_and_get_face_embeddings(self):
        dummy_embedding = np.random.rand(128).astype(np.float64)
        stored = db_mongo.store_face_embedding(
            student_id='TEST001',
            embedding_array=dummy_embedding,
            quality_score=95.5,
            angle='front'
        )
        self.assertTrue(stored)
        count = db_mongo.count_student_embeddings('TEST001')
        self.assertEqual(count, 1)

        all_embs = db_mongo.get_all_face_embeddings()
        self.assertGreaterEqual(len(all_embs), 1)
        found = next((e for e in all_embs if e['student_id'] == 'TEST001'), None)
        self.assertIsNotNone(found)
        self.assertEqual(len(found['embedding']), 128)
        self.assertAlmostEqual(found['embedding'][0], dummy_embedding[0], places=5)

    def test_04_create_and_manage_session(self):
        sess_id = db_mongo.create_session(
            subject_name='Machine Learning Foundations',
            faculty_name='Dr. Demo Faculty',
            classroom_name='LAB-101',
            department='AIDS',
            semester=5,
            date_str='2026-10-15',
            start_time='09:00',
            late_threshold_minutes=15
        )
        self.assertIsInstance(sess_id, int)
        sess = db_mongo.get_session(sess_id)
        self.assertIsNotNone(sess)
        self.assertEqual(sess['status'], 'scheduled')

        # Activate session
        db_mongo.update_session_status(sess_id, 'active')
        active = db_mongo.get_active_session()
        self.assertIsNotNone(active)
        self.assertEqual(active['id'], sess_id)

    def test_05_add_attendance_and_duplicate_prevention(self):
        sess = db_mongo.get_active_session()
        sess_id = sess['id']

        # First mark: should succeed
        ok1, msg1, status1 = db_mongo.add_attendance(
            student_id='TEST001',
            name='Test Student',
            department='AIDS',
            confidence=0.92,
            session_id=sess_id,
            status='Present'
        )
        self.assertTrue(ok1)
        self.assertIn(status1, ['Present', 'Late'])

        # Duplicate mark for same session: must fail!
        ok2, msg2, status2 = db_mongo.add_attendance(
            student_id='TEST001',
            name='Test Student',
            department='AIDS',
            confidence=0.95,
            session_id=sess_id,
            status='Present'
        )
        self.assertFalse(ok2)
        self.assertIn('Already marked', msg2)

    def test_06_verify_user_auth(self):
        res = db_mongo.verify_user('admin', 'admin123')
        self.assertIsInstance(res, dict)
        self.assertEqual(res['username'], 'admin')

        # Bad password
        bad = db_mongo.verify_user('admin', 'wrongpass')
        self.assertEqual(bad, 'invalid_credentials')

    def test_07_dashboard_stats(self):
        stats = db_mongo.get_dashboard_stats()
        self.assertIn('total_registered', stats)
        self.assertIn('present_today', stats)
        self.assertGreaterEqual(stats['total_registered'], 1)

    def test_08_delete_student_cascade(self):
        db_mongo.delete_student('TEST001')
        s = db_mongo.get_student_by_id('TEST001')
        self.assertIsNone(s)
        cnt = db_mongo.count_student_embeddings('TEST001')
        self.assertEqual(cnt, 0)


if __name__ == '__main__':
    unittest.main()
