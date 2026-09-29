import unittest
import sys
import os

# Ensure backend/ is on the path
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, BACKEND_DIR)

from rbac import get_allowed_student_ids
import database
from app_flask import app

class TestRBAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        database.seed_defaults()
        cls.app = app
        cls.app.config['TESTING'] = True
        
    def test_roles_exist(self):
        user = database.get_user_by_username('admin')
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'super_admin')

    def test_allowed_student_ids_super_admin(self):
        with self.app.test_request_context():
            from flask import session
            session['role'] = 'super_admin'
            with database.get_db_connection() as conn:
                allowed = get_allowed_student_ids(conn)
            self.assertIsNone(allowed)

    def test_allowed_student_ids_department_head(self):
        with self.app.test_request_context():
            from flask import session
            session['role'] = 'department_head'
            session['department_id'] = 1
            with database.get_db_connection() as conn:
                allowed = get_allowed_student_ids(conn)
            self.assertIsInstance(allowed, list)
        
    def test_allowed_student_ids_student(self):
        with self.app.test_request_context():
            from flask import session
            session['role'] = 'student'
            session['student_id'] = '102'
            with database.get_db_connection() as conn:
                allowed = get_allowed_student_ids(conn)
            self.assertEqual(allowed, ['102'])

if __name__ == '__main__':
    unittest.main()
