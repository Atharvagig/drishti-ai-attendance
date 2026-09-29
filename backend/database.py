"""
Drishti AI — Database Layer v2.1
Full relational schema: RBAC tables added, migrations, CRUD, analytics, seeding.
Backwards-compatible with v1/v2.0 schema (additive only).
"""
import sqlite3
import os
import json
import pickle
import bcrypt
from datetime import datetime, date, timedelta
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'attendance.db')


def get_db_connection():
    """Returns a SQLite connection with row factory and WAL mode for concurrent access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """
    Initializes full database schema. Safe to call multiple times (idempotent).
    Creates all new tables and runs additive migrations on existing tables.
    """
    with get_db_connection() as conn:
        c = conn.cursor()

        # ── Departments ──────────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ── Subjects / Courses ───────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department_id INTEGER REFERENCES departments(id),
                semester INTEGER DEFAULT 1,
                credits INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ── Users (RBAC roles) ────────────────────────────────────────────────────
        # Create with extended schema; existing DBs get additive ALTER TABLE below
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'faculty',
                name TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                department_id INTEGER REFERENCES departments(id),
                student_id TEXT REFERENCES students(student_id),
                is_active INTEGER DEFAULT 1,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Additive migrations for users table (safe for existing databases)
        _user_migrations = [
            ('full_name',               'TEXT DEFAULT ""'),
            ('is_active',               'INTEGER DEFAULT 1'),
            ('failed_login_attempts',   'INTEGER DEFAULT 0'),
            ('locked_until',            'TIMESTAMP'),
            ('student_id',              'TEXT'),
            ('updated_at',              'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ]
        for col, defn in _user_migrations:
            try:
                c.execute(f'ALTER TABLE users ADD COLUMN {col} {defn}')
            except Exception:
                pass  # Column already exists

        # Ensure role values are valid for new RBAC scheme
        # (migrate legacy 'admin' → 'super_admin' safely via seed_defaults)
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_role     ON users(role)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_dept     ON users(department_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_student  ON users(student_id)')

        # ── Roles table (informational / extensibility) ──────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ── Permissions table (informational / extensibility) ─────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ── Role-Permission mapping ───────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role_id, permission_id)
            )
        ''')

        # ── Classrooms ───────────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                building TEXT DEFAULT '',
                capacity INTEGER DEFAULT 60,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ── Cameras ──────────────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                room TEXT DEFAULT '',
                status TEXT DEFAULT 'offline' CHECK(status IN ('online','offline','error')),
                fps REAL DEFAULT 0.0,
                resolution TEXT DEFAULT '1280x720',
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ── Students (original, extended) ────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT DEFAULT 'General',
                email TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Additive migrations for students
        for col, definition in [
            ('semester', 'INTEGER DEFAULT 1'),
            ('roll_number', 'TEXT DEFAULT ""'),
            ('year_of_joining', 'INTEGER DEFAULT 0'),
            ('enrollment_status', "TEXT DEFAULT 'active'"),
        ]:
            try:
                c.execute(f'ALTER TABLE students ADD COLUMN {col} {definition}')
            except Exception:
                pass  # Column already exists

        # ── Face Embeddings ──────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
                embedding_blob BLOB NOT NULL,
                quality_score REAL DEFAULT 0.0,
                angle TEXT DEFAULT 'front',
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_face_emb_student ON face_embeddings(student_id)')

        # ── Attendance Sessions ───────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER REFERENCES subjects(id),
                faculty_id INTEGER REFERENCES users(id),
                classroom_id INTEGER REFERENCES classrooms(id),
                camera_id TEXT DEFAULT 'CAM-01',
                department TEXT DEFAULT 'General',
                semester INTEGER DEFAULT 1,
                subject_name TEXT DEFAULT '',
                faculty_name TEXT DEFAULT '',
                classroom_name TEXT DEFAULT '',
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT DEFAULT '',
                late_threshold_minutes INTEGER DEFAULT 10,
                status TEXT DEFAULT 'scheduled'
                    CHECK(status IN ('scheduled','active','completed','locked')),
                created_by TEXT DEFAULT 'admin',
                locked_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_date ON attendance_sessions(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON attendance_sessions(status)')

        # ── Attendance Records (original, extended) ───────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
                department TEXT DEFAULT 'General',
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Present',
                confidence REAL DEFAULT 0.0,
                email_sent INTEGER DEFAULT 0
            )
        ''')

        # Additive migrations for attendance
        for col, definition in [
            ('session_id', 'INTEGER REFERENCES attendance_sessions(id)'),
            ('liveness_passed', 'INTEGER DEFAULT 0'),
            ('face_quality', "TEXT DEFAULT 'unknown'"),
            ('override_reason', 'TEXT DEFAULT ""'),
            ('override_by', 'TEXT DEFAULT ""'),
        ]:
            try:
                c.execute(f'ALTER TABLE attendance ADD COLUMN {col} {definition}')
            except Exception:
                pass

        c.execute('CREATE INDEX IF NOT EXISTS idx_att_student_date ON attendance(student_id, date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_att_session ON attendance(session_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_att_date ON attendance(date)')

        # ── Audit Logs ────────────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                username TEXT DEFAULT 'system',
                action TEXT NOT NULL,
                entity_type TEXT DEFAULT '',
                entity_id TEXT DEFAULT '',
                old_value TEXT DEFAULT '',
                new_value TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)')

        # ── Anomalies ─────────────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES attendance_sessions(id),
                student_id TEXT DEFAULT '',
                anomaly_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                severity TEXT DEFAULT 'medium'
                    CHECK(severity IN ('low','medium','high','critical')),
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_anomalies_session ON anomalies(session_id)')

        # ── Notifications ─────────────────────────────────────────────────────────
        c.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                type TEXT DEFAULT 'info'
                    CHECK(type IN ('info','warning','error','success')),
                title TEXT NOT NULL,
                message TEXT DEFAULT '',
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
    print("[Database v2.1] Full schema with RBAC initialized successfully.")


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_defaults():
    """Seeds default departments, classrooms, cameras, subjects and admin user."""
    with get_db_connection() as conn:
        c = conn.cursor()

        # Departments
        depts = [
            ('Artificial Intelligence & Data Science', 'AIDS'),
            ('Computer Science & Engineering', 'CSE'),
            ('Electronics & Communication', 'ECE'),
            ('Information Technology', 'IT'),
            ('Mechanical Engineering', 'ME'),
            ('General', 'GEN'),
        ]
        for name, code in depts:
            c.execute('INSERT OR IGNORE INTO departments (name, code) VALUES (?, ?)', (name, code))

        # Classrooms
        rooms = [
            ('LAB-101', 'Block A', 40),
            ('LAB-204', 'Block B', 35),
            ('ROOM-101', 'Block A', 60),
            ('ROOM-202', 'Block B', 60),
            ('SEMINAR HALL', 'Block C', 120),
        ]
        for name, building, cap in rooms:
            c.execute('INSERT OR IGNORE INTO classrooms (name, building, capacity) VALUES (?, ?, ?)',
                      (name, building, cap))

        # Cameras
        cams = [
            ('CAM-01', 'Main Cam', 'Block A', 'LAB-101'),
            ('CAM-02', 'Secondary', 'Block B', 'LAB-204'),
            ('CAM-03', 'Room Cam', 'Block A', 'ROOM-101'),
        ]
        for cid, name, loc, room in cams:
            c.execute('INSERT OR IGNORE INTO cameras (camera_id, name, location, room) VALUES (?, ?, ?, ?)',
                      (cid, name, loc, room))

        # Subjects
        c.execute('SELECT id FROM departments WHERE code = ?', ('AIDS',))
        aids_row = c.fetchone()
        aids_id = aids_row['id'] if aids_row else 1

        c.execute('SELECT id FROM departments WHERE code = ?', ('CSE',))
        cse_row = c.fetchone()
        cse_id = cse_row['id'] if cse_row else 2

        subjects = [
            ('AIDS501', 'Deep Learning', aids_id, 5, 4),
            ('AIDS502', 'Computer Networks', aids_id, 5, 4),
            ('AIDS503', 'Data Mining', aids_id, 5, 3),
            ('CSE401', 'Operating Systems', cse_id, 4, 4),
            ('CSE402', 'Database Management', cse_id, 4, 3),
        ]
        for code, name, dept_id, sem, cred in subjects:
            c.execute('INSERT OR IGNORE INTO subjects (code, name, department_id, semester, credits) VALUES (?, ?, ?, ?, ?)',
                      (code, name, dept_id, sem, cred))

        # ── Seed RBAC roles into roles table ─────────────────────────────────────
        default_roles = [
            ('super_admin',         'Super Administrator', 'Full system control'),
            ('department_head',     'Department Head',     'Manage assigned department'),
            ('faculty',             'Faculty',             'Conduct attendance sessions'),
            ('attendance_operator', 'Attendance Operator', 'Operate cameras and live tracking'),
            ('student',             'Student',             'View own attendance data'),
        ]
        for rname, display, desc in default_roles:
            c.execute('INSERT OR IGNORE INTO roles (name, display_name, description) VALUES (?,?,?)',
                      (rname, display, desc))

        # ── Migrate existing admin user ───────────────────────────────────────────
        # Safely rename role 'admin' → 'super_admin' on existing rows
        c.execute("UPDATE users SET role = 'super_admin' WHERE role = 'admin'")

        # ── Ensure super_admin user exists ────────────────────────────────────────
        c.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        if not c.fetchone():
            pw_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
            c.execute('''
                INSERT INTO users
                    (username, password_hash, role, name, full_name, email, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', ('admin', pw_hash, 'super_admin', 'Administrator',
                  'System Administrator', 'admin@drishti.ai'))

        # ── Ensure faculty demo user exists ───────────────────────────────────────
        c.execute('SELECT id FROM users WHERE username = ?', ('faculty',))
        if not c.fetchone():
            pw_hash = bcrypt.hashpw(b'faculty123', bcrypt.gensalt()).decode()
            c.execute('''
                INSERT INTO users
                    (username, password_hash, role, name, full_name, email,
                     department_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', ('faculty', pw_hash, 'faculty', 'Dr. Demo Faculty',
                  'Dr. Demo Faculty', 'faculty@drishti.ai', aids_id))
        else:
            # Ensure existing faculty user has is_active set
            c.execute("UPDATE users SET is_active = 1 WHERE username = 'faculty' AND is_active IS NULL")

        # ── Ensure existing users have is_active set ──────────────────────────────
        c.execute('UPDATE users SET is_active = 1 WHERE is_active IS NULL')
        c.execute("UPDATE users SET full_name = name WHERE full_name IS NULL OR full_name = ''")

        conn.commit()
    print("[Database] RBAC defaults seeded.")


# ── Students ──────────────────────────────────────────────────────────────────

def add_student(student_id, name, department='General', email='', photo_path='',
                semester=1, roll_number='', year_of_joining=0):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO students (student_id, name, department, email, photo_path,
                                  semester, roll_number, year_of_joining)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                name=excluded.name, department=excluded.department,
                email=excluded.email, photo_path=excluded.photo_path,
                semester=excluded.semester, roll_number=excluded.roll_number,
                year_of_joining=excluded.year_of_joining
        ''', (str(student_id), name, department, email, photo_path,
              semester, roll_number, year_of_joining))
        conn.commit()
    return True


def get_all_students():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM students ORDER BY created_at DESC')
        return [dict(r) for r in c.fetchall()]


def get_student_by_id(student_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM students WHERE student_id = ?', (str(student_id),))
        row = c.fetchone()
        return dict(row) if row else None


def delete_student(student_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM face_embeddings WHERE student_id = ?', (str(student_id),))
        c.execute('DELETE FROM attendance WHERE student_id = ?', (str(student_id),))
        c.execute('DELETE FROM students WHERE student_id = ?', (str(student_id),))
        conn.commit()
    return True


# ── Face Embeddings ───────────────────────────────────────────────────────────

def store_face_embedding(student_id, embedding_array, quality_score=0.0, angle='front'):
    """Stores a single face embedding as a pickled blob."""
    blob = pickle.dumps(embedding_array)
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO face_embeddings (student_id, embedding_blob, quality_score, angle)
            VALUES (?, ?, ?, ?)
        ''', (str(student_id), blob, float(quality_score), angle))
        conn.commit()
    return True


def get_all_face_embeddings():
    """
    Returns all stored embeddings as a list of dicts with deserialized numpy arrays.
    Used for loading recognition engine.
    """
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT fe.student_id, fe.embedding_blob, fe.quality_score, fe.angle,
                   s.name, s.department
            FROM face_embeddings fe
            JOIN students s ON s.student_id = fe.student_id
        ''')
        rows = c.fetchall()

    result = []
    for row in rows:
        try:
            emb = pickle.loads(row['embedding_blob'])
            result.append({
                'student_id': row['student_id'],
                'name': row['name'],
                'department': row['department'],
                'embedding': emb,
                'quality_score': row['quality_score'],
                'angle': row['angle'],
            })
        except Exception as e:
            print(f"[DB] Error deserializing embedding for {row['student_id']}: {e}")
    return result


def delete_student_embeddings(student_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM face_embeddings WHERE student_id = ?', (str(student_id),))
        conn.commit()
    return True


def count_student_embeddings(student_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) as cnt FROM face_embeddings WHERE student_id = ?', (str(student_id),))
        return c.fetchone()['cnt']


# ── Attendance ────────────────────────────────────────────────────────────────

def add_attendance(student_id, name, department='General', confidence=0.0,
                   email_sent=0, session_id=None, liveness_passed=0,
                   face_quality='unknown', status='Present'):
    """
    Logs attendance. For session-based mode, uses session_id and computes
    Present/Late based on session's late_threshold_minutes.
    Returns (success: bool, time_str or error_msg: str, final_status: str)
    """
    today = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    final_status = status

    with get_db_connection() as conn:
        c = conn.cursor()

        # Duplicate check for same session
        if session_id:
            c.execute('''
                SELECT id FROM attendance
                WHERE student_id = ? AND session_id = ?
            ''', (str(student_id), session_id))
            if c.fetchone():
                return False, 'Already marked for this session', final_status
        else:
            # Global daily duplicate check (legacy mode)
            c.execute('''
                SELECT id FROM attendance WHERE student_id = ? AND date = ? AND session_id IS NULL
            ''', (str(student_id), today))
            if c.fetchone():
                return False, 'Already marked today', final_status

        # Compute Present/Late based on session
        if session_id and status == 'Present':
            c.execute('SELECT start_time, late_threshold_minutes FROM attendance_sessions WHERE id = ?',
                      (session_id,))
            sess = c.fetchone()
            if sess:
                try:
                    start_dt = datetime.strptime(f"{today} {sess['start_time']}", '%Y-%m-%d %H:%M')
                    threshold_dt = start_dt + timedelta(minutes=sess['late_threshold_minutes'])
                    now_dt = datetime.now()
                    if now_dt > threshold_dt:
                        final_status = 'Late'
                except Exception:
                    pass

        c.execute('''
            INSERT INTO attendance
                (student_id, name, department, date, time, status, confidence,
                 email_sent, session_id, liveness_passed, face_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(student_id), name, department, today, time_str, final_status,
              float(confidence), int(email_sent), session_id,
              int(liveness_passed), face_quality))
        conn.commit()
    return True, time_str, final_status


def get_attendance_logs(date_str=None, session_id=None, limit=500):
    with get_db_connection() as conn:
        c = conn.cursor()
        if session_id:
            c.execute('''
                SELECT * FROM attendance WHERE session_id = ?
                ORDER BY timestamp DESC
            ''', (session_id,))
        elif date_str:
            c.execute('''
                SELECT * FROM attendance WHERE date = ?
                ORDER BY timestamp DESC
            ''', (date_str,))
        else:
            c.execute('SELECT * FROM attendance ORDER BY timestamp DESC LIMIT ?', (limit,))
        return [dict(r) for r in c.fetchall()]


def get_student_attendance_history(student_id, limit=100):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT a.*, s.subject_name, s.classroom_name
            FROM attendance a
            LEFT JOIN attendance_sessions s ON a.session_id = s.id
            WHERE a.student_id = ?
            ORDER BY a.timestamp DESC
            LIMIT ?
        ''', (str(student_id), limit))
        return [dict(r) for r in c.fetchall()]


def delete_attendance_record(record_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM attendance WHERE id = ?', (record_id,))
        conn.commit()
    return True


def override_attendance(record_id, new_status, reason, override_by):
    """Manual attendance correction with audit fields."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM attendance WHERE id = ?', (record_id,))
        row = c.fetchone()
        if not row:
            return False, 'Record not found'
        old_status = row['status']
        c.execute('''
            UPDATE attendance
            SET status = ?, override_reason = ?, override_by = ?
            WHERE id = ?
        ''', (new_status, reason, override_by, record_id))
        conn.commit()
    log_audit(None, override_by, 'override_attendance', 'attendance', str(record_id),
              old_status, new_status)
    return True, old_status


def mark_absent_for_session(session_id):
    """
    After a session ends, mark all enrolled students not yet recorded
    in this session as Absent.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT student_id FROM attendance WHERE session_id = ?
        ''', (session_id,))
        marked = {r['student_id'] for r in c.fetchall()}

        c.execute('SELECT student_id, name, department FROM students WHERE enrollment_status = "active"')
        all_students = c.fetchall()

        for s in all_students:
            if s['student_id'] not in marked:
                time_str = datetime.now().strftime('%H:%M:%S')
                c.execute('''
                    INSERT INTO attendance
                        (student_id, name, department, date, time, status,
                         session_id, liveness_passed, face_quality)
                    VALUES (?, ?, ?, ?, ?, 'Absent', ?, 0, 'n/a')
                ''', (s['student_id'], s['name'], s['department'], today, time_str, session_id))
        conn.commit()
    return True


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(subject_name, faculty_name, classroom_name, department, semester,
                   date_str, start_time, late_threshold_minutes=10,
                   camera_id='CAM-01', created_by='admin',
                   subject_id=None, faculty_id=None, classroom_id=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO attendance_sessions
                (subject_id, faculty_id, classroom_id, camera_id,
                 department, semester, subject_name, faculty_name, classroom_name,
                 date, start_time, late_threshold_minutes, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', ?)
        ''', (subject_id, faculty_id, classroom_id, camera_id,
              department, semester, subject_name, faculty_name, classroom_name,
              date_str, start_time, late_threshold_minutes, created_by))
        conn.commit()
        return c.lastrowid


def get_all_sessions(date_str=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        if date_str:
            c.execute('''
                SELECT * FROM attendance_sessions WHERE date = ?
                ORDER BY start_time DESC
            ''', (date_str,))
        else:
            c.execute('SELECT * FROM attendance_sessions ORDER BY date DESC, start_time DESC LIMIT 100')
        return [dict(r) for r in c.fetchall()]


def get_session(session_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM attendance_sessions WHERE id = ?', (session_id,))
        row = c.fetchone()
        return dict(row) if row else None


def update_session_status(session_id, status, end_time=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        if status == 'locked':
            c.execute('''
                UPDATE attendance_sessions
                SET status = ?, locked_at = CURRENT_TIMESTAMP, end_time = COALESCE(?, end_time)
                WHERE id = ?
            ''', (status, end_time, session_id))
        else:
            c.execute('''
                UPDATE attendance_sessions
                SET status = ?, end_time = COALESCE(?, end_time)
                WHERE id = ?
            ''', (status, end_time, session_id))
        conn.commit()
    return True


def get_active_session():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM attendance_sessions WHERE status = 'active' ORDER BY created_at DESC LIMIT 1")
        row = c.fetchone()
        return dict(row) if row else None


# ── Dashboard Stats ────────────────────────────────────────────────────────────

def get_dashboard_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        c = conn.cursor()

        c.execute('SELECT COUNT(*) as count FROM students')
        total = c.fetchone()['count']

        c.execute('''
            SELECT COUNT(DISTINCT student_id) as count FROM attendance
            WHERE date = ? AND status = 'Present'
        ''', (today,))
        present = c.fetchone()['count']

        c.execute('''
            SELECT COUNT(DISTINCT student_id) as count FROM attendance
            WHERE date = ? AND status = 'Late'
        ''', (today,))
        late = c.fetchone()['count']

        c.execute('''
            SELECT COUNT(DISTINCT student_id) as count FROM attendance
            WHERE date = ? AND status = 'Absent'
        ''', (today,))
        absent_marked = c.fetchone()['count']

        # Students with no record at all
        absent = max(0, total - present - late - absent_marked)

        rate = round(((present + late) / total * 100), 1) if total > 0 else 0.0

        c.execute("SELECT COUNT(*) as cnt FROM attendance_sessions WHERE status = 'active'")
        active_sessions = c.fetchone()['cnt']

        c.execute("SELECT COUNT(*) as cnt FROM anomalies WHERE resolved = 0")
        unresolved_anomalies = c.fetchone()['cnt']

        # Risk count: students with < 75% in last 30 days
        c.execute('''
            SELECT student_id,
                   SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 1.0 /
                   COUNT(*) as rate
            FROM attendance
            WHERE date >= date('now', '-30 days')
            GROUP BY student_id
            HAVING rate < 0.75
        ''')
        risk_count = len(c.fetchall())

        return {
            'total_registered': total,
            'present_today': present,
            'late_today': late,
            'absent_today': absent + absent_marked,
            'attendance_rate': rate,
            'active_sessions': active_sessions,
            'unresolved_anomalies': unresolved_anomalies,
            'at_risk_count': risk_count,
            'today_date': today,
        }


# ── Analytics ─────────────────────────────────────────────────────────────────

def get_attendance_trends(days=30):
    """Returns daily attendance rates for the past N days."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT date,
                   COUNT(DISTINCT student_id) as total_marked,
                   SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) as attended
            FROM attendance
            WHERE date >= date('now', ? || ' days')
            GROUP BY date
            ORDER BY date ASC
        ''', (f'-{days}',))
        return [dict(r) for r in c.fetchall()]


def get_department_stats():
    """Returns per-department attendance summary."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT department,
                   COUNT(DISTINCT student_id) as students,
                   SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) as attended,
                   COUNT(*) as total
            FROM attendance
            WHERE date >= date('now', '-30 days')
            GROUP BY department
        ''')
        rows = c.fetchall()
    result = []
    for r in rows:
        rate = round(r['attended'] / r['total'] * 100, 1) if r['total'] > 0 else 0
        result.append({**dict(r), 'rate': rate})
    return result


def get_at_risk_students(threshold=75.0, days=30):
    """Students with attendance below threshold in past N days."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT a.student_id, s.name, s.department, s.semester,
                   COUNT(*) as total_sessions,
                   SUM(CASE WHEN a.status IN ('Present','Late') THEN 1 ELSE 0 END) as attended,
                   ROUND(SUM(CASE WHEN a.status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                         / COUNT(*), 1) as rate
            FROM attendance a
            JOIN students s ON s.student_id = a.student_id
            WHERE a.date >= date('now', ? || ' days')
            GROUP BY a.student_id
            HAVING rate < ?
            ORDER BY rate ASC
        ''', (f'-{days}', threshold))
        return [dict(r) for r in c.fetchall()]


def get_ai_insights():
    """Generates real, data-driven insights from the database."""
    insights = []
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            # Insight 1: Monthly trend
            c.execute('''
                SELECT
                  ROUND(SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                        / NULLIF(COUNT(*), 0), 1) as rate
                FROM attendance
                WHERE date >= date('now', '-30 days')
            ''')
            row = c.fetchone()
            curr_rate = row['rate'] or 0

            c.execute('''
                SELECT
                  ROUND(SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                        / NULLIF(COUNT(*), 0), 1) as rate
                FROM attendance
                WHERE date >= date('now', '-60 days') AND date < date('now', '-30 days')
            ''')
            row2 = c.fetchone()
            prev_rate = row2['rate'] or curr_rate
            diff = round(curr_rate - prev_rate, 1)
            arrow = '↑' if diff >= 0 else '↓'
            insights.append({
                'icon': 'trend-up' if diff >= 0 else 'trend-down',
                'type': 'positive' if diff >= 0 else 'warning',
                'text': f"Attendance {arrow} {abs(diff)}% vs. last month ({curr_rate}% this month)",
            })

            # Insight 2: At-risk count
            c.execute('''
                SELECT COUNT(DISTINCT student_id) as cnt FROM (
                    SELECT student_id,
                           ROUND(SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                                 / COUNT(*), 1) as rate
                    FROM attendance WHERE date >= date('now', '-30 days')
                    GROUP BY student_id HAVING rate < 75
                )
            ''')
            risk = c.fetchone()['cnt']
            if risk > 0:
                insights.append({
                    'icon': 'warning',
                    'type': 'warning',
                    'text': f"{risk} student{'s' if risk != 1 else ''} currently below the 75% attendance threshold",
                })

            # Insight 3: Worst day of week
            c.execute('''
                SELECT strftime('%w', date) as dow,
                       ROUND(SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                             / NULLIF(COUNT(*), 0), 1) as rate
                FROM attendance
                WHERE date >= date('now', '-60 days')
                GROUP BY dow
                ORDER BY rate ASC
                LIMIT 1
            ''')
            row3 = c.fetchone()
            if row3:
                days_map = {'0': 'Sunday', '1': 'Monday', '2': 'Tuesday',
                            '3': 'Wednesday', '4': 'Thursday', '5': 'Friday', '6': 'Saturday'}
                day_name = days_map.get(str(row3['dow']), 'that day')
                insights.append({
                    'icon': 'calendar-x',
                    'type': 'info',
                    'text': f"{day_name} sessions have the lowest average attendance ({row3['rate']}%)",
                })

            # Insight 4: Best department
            c.execute('''
                SELECT department,
                       ROUND(SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                             / NULLIF(COUNT(*), 0), 1) as rate
                FROM attendance WHERE date >= date('now', '-30 days')
                GROUP BY department ORDER BY rate DESC LIMIT 1
            ''')
            row4 = c.fetchone()
            if row4 and row4['rate']:
                insights.append({
                    'icon': 'trophy',
                    'type': 'positive',
                    'text': f"{row4['department']} leads with {row4['rate']}% average attendance",
                })

            # Insight 5: Late arrival pattern
            c.execute('''
                SELECT COUNT(*) as cnt FROM attendance
                WHERE status = 'Late' AND date >= date('now', '-30 days')
            ''')
            late_cnt = c.fetchone()['cnt']
            if late_cnt > 0:
                insights.append({
                    'icon': 'clock',
                    'type': 'info',
                    'text': f"{late_cnt} late arrivals recorded in the past 30 days",
                })

    except Exception as e:
        print(f"[Insights] Error: {e}")
        insights.append({
            'icon': 'info',
            'type': 'info',
            'text': 'Insights will appear once attendance data is collected.',
        })

    return insights


def get_heatmap_data(student_id=None, months=3):
    """Returns calendar heatmap data: {date: status}."""
    with get_db_connection() as conn:
        c = conn.cursor()
        if student_id:
            c.execute('''
                SELECT date, status FROM attendance
                WHERE student_id = ? AND date >= date('now', ? || ' months')
                ORDER BY date
            ''', (str(student_id), f'-{months}'))
        else:
            c.execute('''
                SELECT date,
                       ROUND(SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) * 100.0
                             / NULLIF(COUNT(*), 0), 1) as rate
                FROM attendance
                WHERE date >= date('now', ? || ' months')
                GROUP BY date ORDER BY date
            ''', (f'-{months}',))
        rows = c.fetchall()
    return [dict(r) for r in rows]


# ── Cameras ───────────────────────────────────────────────────────────────────

def get_all_cameras():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM cameras ORDER BY camera_id')
        return [dict(r) for r in c.fetchall()]


def update_camera_heartbeat(camera_id, status='online', fps=0.0):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            UPDATE cameras SET status = ?, fps = ?, last_heartbeat = CURRENT_TIMESTAMP
            WHERE camera_id = ?
        ''', (status, fps, camera_id))
        conn.commit()


# ── Anomalies ─────────────────────────────────────────────────────────────────

def log_anomaly(anomaly_type, description, session_id=None, student_id='', severity='medium'):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO anomalies (session_id, student_id, anomaly_type, description, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, student_id, anomaly_type, description, severity))
        conn.commit()
        return c.lastrowid


def get_anomalies(limit=50, unresolved_only=False):
    with get_db_connection() as conn:
        c = conn.cursor()
        if unresolved_only:
            c.execute('''
                SELECT * FROM anomalies WHERE resolved = 0
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        else:
            c.execute('SELECT * FROM anomalies ORDER BY created_at DESC LIMIT ?', (limit,))
        return [dict(r) for r in c.fetchall()]


# ── Notifications ─────────────────────────────────────────────────────────────

def create_notification(title, message, type='info', user_id=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO notifications (user_id, type, title, message)
            VALUES (?, ?, ?, ?)
        ''', (user_id, type, title, message))
        conn.commit()
        return c.lastrowid


def get_notifications(user_id=None, limit=30):
    with get_db_connection() as conn:
        c = conn.cursor()
        if user_id:
            c.execute('''
                SELECT * FROM notifications WHERE user_id = ? OR user_id IS NULL
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit))
        else:
            c.execute('SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?', (limit,))
        return [dict(r) for r in c.fetchall()]


def mark_notification_read(notification_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('UPDATE notifications SET read = 1 WHERE id = ?', (notification_id,))
        conn.commit()


def get_unread_count(user_id=None):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) as cnt FROM notifications WHERE read = 0')
        return c.fetchone()['cnt']


# ── Audit Logs ────────────────────────────────────────────────────────────────

def log_audit(user_id, username, action, entity_type='', entity_id='',
              old_value='', new_value='', ip_address=''):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO audit_logs
                    (user_id, username, action, entity_type, entity_id,
                     old_value, new_value, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, action, entity_type, str(entity_id),
                  str(old_value), str(new_value), ip_address))
            conn.commit()
    except Exception as e:
        print(f"[Audit] Log failed: {e}")


def get_audit_logs(limit=100):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?', (limit,))
        return [dict(r) for r in c.fetchall()]


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_user(username: str, password: str):
    """
    Authenticate a user. Returns user dict on success, or a string error code.
    Error codes: 'invalid_credentials' | 'account_disabled' | 'account_locked'
    Implements brute-force lockout: 5 failures → 10-minute lock.
    """
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 10

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        if not user:
            return 'invalid_credentials'

        user = dict(user)

        # Check if account is manually disabled
        if not user.get('is_active', 1):
            return 'account_disabled'

        # Check if account is temporarily locked
        locked_until = user.get('locked_until')
        if locked_until:
            try:
                lock_dt = datetime.fromisoformat(str(locked_until))
                if datetime.now() < lock_dt:
                    return 'account_locked'
                else:
                    # Lock expired — reset
                    c.execute('''
                        UPDATE users SET locked_until = NULL, failed_login_attempts = 0
                        WHERE id = ?
                    ''', (user['id'],))
                    conn.commit()
            except Exception:
                pass

        # Verify password
        try:
            password_ok = bcrypt.checkpw(password.encode(), user['password_hash'].encode())
        except Exception:
            return 'invalid_credentials'

        if not password_ok:
            # Increment failed attempts
            attempts = user.get('failed_login_attempts', 0) + 1
            if attempts >= MAX_ATTEMPTS:
                lock_until_dt = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                c.execute('''
                    UPDATE users
                    SET failed_login_attempts = ?, locked_until = ?
                    WHERE id = ?
                ''', (attempts, lock_until_dt.isoformat(), user['id']))
            else:
                c.execute('''
                    UPDATE users SET failed_login_attempts = ? WHERE id = ?
                ''', (attempts, user['id']))
            conn.commit()
            return 'invalid_credentials'

        # Successful login — reset counters, update last_login
        c.execute('''
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP,
                failed_login_attempts = 0,
                locked_until = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user['id'],))
        conn.commit()
        # Return fresh copy
        c.execute('SELECT * FROM users WHERE id = ?', (user['id'],))
        return dict(c.fetchone())


# ── User Management ───────────────────────────────────────────────────────────

def get_all_users():
    """Return all users (excluding password_hash) for admin view."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT u.id, u.username, u.email,
                   COALESCE(u.full_name, u.name) as full_name,
                   u.name, u.role, u.is_active,
                   u.department_id, d.name as department_name,
                   u.student_id, u.created_at, u.last_login,
                   u.failed_login_attempts, u.locked_until
            FROM users u
            LEFT JOIN departments d ON d.id = u.department_id
            ORDER BY u.created_at DESC
        ''')
        return [dict(r) for r in c.fetchall()]


def get_user_by_id(user_id: int):
    """Return a single user dict (no password_hash)."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT u.id, u.username, u.email,
                   COALESCE(u.full_name, u.name) as full_name,
                   u.name, u.role, u.is_active,
                   u.department_id, d.name as department_name,
                   u.student_id, u.created_at, u.last_login,
                   u.failed_login_attempts, u.locked_until
            FROM users u
            LEFT JOIN departments d ON d.id = u.department_id
            WHERE u.id = ?
        ''', (user_id,))
        row = c.fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str):
    """Return a user dict (no password_hash) by username."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT u.id, u.username, u.email,
                   COALESCE(u.full_name, u.name) as full_name,
                   u.name, u.role, u.is_active,
                   u.department_id, d.name as department_name,
                   u.student_id, u.created_at, u.last_login
            FROM users u
            LEFT JOIN departments d ON d.id = u.department_id
            WHERE u.username = ?
        ''', (username,))
        row = c.fetchone()
        return dict(row) if row else None


def create_user(username: str, password: str, role: str, full_name: str,
                email: str = '', department_id: int = None,
                student_id: str = None) -> int:
    """
    Create a new user. Returns the new user's ID.
    Raises ValueError on validation errors.
    """
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters.')

    valid_roles = ['super_admin', 'department_head', 'faculty',
                   'attendance_operator', 'student']
    if role not in valid_roles:
        raise ValueError(f'Invalid role. Must be one of: {valid_roles}')

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO users
                (username, password_hash, role, name, full_name, email,
                 department_id, student_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (username.strip(), pw_hash, role, full_name.strip(),
              full_name.strip(), email.strip(), department_id, student_id))
        conn.commit()
        return c.lastrowid


def update_user(user_id: int, **fields) -> bool:
    """
    Update user fields. Allowed: full_name, email, role, department_id,
    student_id, is_active.
    Never updates password_hash or username via this function.
    """
    allowed = {'full_name', 'email', 'role', 'department_id', 'student_id', 'is_active'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    # Also update name to keep backwards compat
    if 'full_name' in updates:
        updates['name'] = updates['full_name']
    updates['updated_at'] = datetime.now().isoformat()
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    vals = list(updates.values()) + [user_id]
    with get_db_connection() as conn:
        conn.execute(f'UPDATE users SET {set_clause} WHERE id = ?', vals)
        conn.commit()
    return True


def set_user_active(user_id: int, is_active: bool) -> bool:
    """Enable or disable a user account."""
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (1 if is_active else 0, user_id))
        conn.commit()
    return True


def unlock_user(user_id: int) -> bool:
    """Admin unlock of a brute-force locked account."""
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users
            SET locked_until = NULL, failed_login_attempts = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
    return True


def reset_user_password(user_id: int, new_password: str) -> bool:
    """
    Admin password reset. Does NOT require current password.
    Raises ValueError if password is too short.
    """
    if len(new_password) < 8:
        raise ValueError('Password must be at least 8 characters.')
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users
            SET password_hash = ?, updated_at = CURRENT_TIMESTAMP,
                failed_login_attempts = 0, locked_until = NULL
            WHERE id = ?
        ''', (pw_hash, user_id))
        conn.commit()
    return True


def change_own_password(user_id: int, current_password: str, new_password: str) -> bool:
    """
    Self-service password change. Requires current password verification.
    Returns True on success, raises ValueError on failure.
    """
    if len(new_password) < 8:
        raise ValueError('New password must be at least 8 characters.')
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        if not row:
            raise ValueError('User not found.')
        if not bcrypt.checkpw(current_password.encode(), row['password_hash'].encode()):
            raise ValueError('Current password is incorrect.')
        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        conn.execute('''
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (pw_hash, user_id))
        conn.commit()
    return True


def get_audit_logs_filtered(limit: int = 100, username: str = None,
                             action: str = None, entity_type: str = None,
                             date_from: str = None, date_to: str = None) -> list:
    """Extended audit log query with optional filters."""
    with get_db_connection() as conn:
        c = conn.cursor()
        where = []
        params = []
        if username:
            where.append('username = ?')
            params.append(username)
        if action:
            where.append('action LIKE ?')
            params.append(f'%{action}%')
        if entity_type:
            where.append('entity_type = ?')
            params.append(entity_type)
        if date_from:
            where.append('DATE(created_at) >= ?')
            params.append(date_from)
        if date_to:
            where.append('DATE(created_at) <= ?')
            params.append(date_to)
        clause = ('WHERE ' + ' AND '.join(where)) if where else ''
        params.append(limit)
        c.execute(f'''
            SELECT * FROM audit_logs {clause}
            ORDER BY created_at DESC LIMIT ?
        ''', params)
        return [dict(r) for r in c.fetchall()]


def get_subjects():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM subjects ORDER BY name')
        return [dict(r) for r in c.fetchall()]


def get_classrooms():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM classrooms ORDER BY name')
        return [dict(r) for r in c.fetchall()]


if __name__ == '__main__':
    init_db()
    seed_defaults()
    print("[Database v2.0] Ready.")
