"""
Drishti AI — MongoDB Atlas Database Layer
Complete MongoDB implementation preserving all 51 database function signatures,
data types, relational constraints, and API contracts.
Supports PyMongo with connection pooling, automatic index creation,
and atomic sequence counters for backward-compatible integer IDs.
"""
import os
import time
import pickle
import random
from datetime import datetime, date, timedelta
import bcrypt
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.binary import Binary
from bson.objectid import ObjectId

# ── Environment & Connection Configuration ─────────────────────────────────────
DEFAULT_MONGO_URI = os.getenv(
    'MONGODB_URI',
    'mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority'
)
DATABASE_NAME = os.getenv('DATABASE_NAME', 'drishti_attendance')

_client = None
_db = None


def get_mongo_client(uri=None):
    """Returns a singleton MongoDB client with connection pooling and timeouts."""
    global _client
    if _client is None:
        target_uri = uri or os.getenv('MONGODB_URI')
        if not target_uri or '<username>' in target_uri:
            raise ValueError("MONGODB_URI is not set or contains default placeholders.")
        _client = MongoClient(
            target_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            maxPoolSize=50,
            minPoolSize=5,
            retryWrites=True
        )
    return _client


def get_db(client=None, db_name=None):
    """Returns the MongoDB database handle."""
    global _db
    if client is not None:
        return client[db_name or DATABASE_NAME]
    if _db is None:
        c = get_mongo_client()
        _db = c[db_name or DATABASE_NAME]
    return _db


def set_custom_db(db_handle):
    """Allows injecting an in-memory or mock DB handle (for unit testing)."""
    global _db
    _db = db_handle


# ── Atomic Sequence Generator (for backward-compatible integer IDs) ───────────

def get_next_sequence_value(sequence_name, db=None):
    """Generates an atomic auto-increment integer ID for a given collection."""
    database = db if db is not None else get_db()
    ret = database.counters.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    return ret['sequence_value']


def set_sequence_value(sequence_name, value, db=None):
    """Sets the sequence counter value (useful after data migrations)."""
    database = db if db is not None else get_db()
    database.counters.update_one(
        {'_id': sequence_name},
        {'$set': {'sequence_value': int(value)}},
        upsert=True
    )


# ── Initialization & Schema Indexes ───────────────────────────────────────────

def init_db(db=None):
    """
    Ensures collections and indexes are set up in MongoDB Atlas.
    Idempotent and safe to run multiple times.
    """
    database = db if db is not None else get_db()

    # 1. users
    database.users.create_index([('username', ASCENDING)], unique=True)
    database.users.create_index([('email', ASCENDING)])
    database.users.create_index([('role', ASCENDING)])
    database.users.create_index([('department_id', ASCENDING)])
    database.users.create_index([('student_id', ASCENDING)])

    # 2. departments
    database.departments.create_index([('name', ASCENDING)], unique=True)
    database.departments.create_index([('code', ASCENDING)], unique=True)

    # 3. subjects
    database.subjects.create_index([('code', ASCENDING)], unique=True)
    database.subjects.create_index([('department_id', ASCENDING)])

    # 4. classrooms
    database.classrooms.create_index([('name', ASCENDING)], unique=True)

    # 5. cameras
    database.cameras.create_index([('camera_id', ASCENDING)], unique=True)

    # 6. students
    database.students.create_index([('student_id', ASCENDING)], unique=True)
    database.students.create_index([('department', ASCENDING)])

    # 7. face_embeddings
    database.face_embeddings.create_index([('student_id', ASCENDING)])

    # 8. attendance_sessions
    database.attendance_sessions.create_index([('date', DESCENDING)])
    database.attendance_sessions.create_index([('status', ASCENDING)])

    # 9. attendance
    # Session-bound duplicate prevention constraint:
    try:
        database.attendance.create_index(
            [('student_id', ASCENDING), ('session_id', ASCENDING)],
            unique=True,
            partialFilterExpression={'session_id': {'$gt': 0}}
        )
    except Exception:
        pass

    # Global daily duplicate prevention constraint (when session_id is None or 0):
    try:
        database.attendance.create_index(
            [('student_id', ASCENDING), ('date', ASCENDING)],
            unique=True,
            partialFilterExpression={'session_id': None}
        )
    except Exception:
        pass

    database.attendance.create_index([('session_id', ASCENDING)])
    database.attendance.create_index([('date', DESCENDING)])
    database.attendance.create_index([('timestamp', DESCENDING)])

    # 10. audit_logs
    database.audit_logs.create_index([('created_at', DESCENDING)])
    database.audit_logs.create_index([('username', ASCENDING)])

    # 11. anomalies
    database.anomalies.create_index([('session_id', ASCENDING)])
    database.anomalies.create_index([('resolved', ASCENDING)])

    # 12. notifications
    database.notifications.create_index([('user_id', ASCENDING)])
    database.notifications.create_index([('read', ASCENDING)])
    database.notifications.create_index([('created_at', DESCENDING)])

    print("[MongoDB Atlas] Database schema and indexes initialized successfully.")


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_defaults(db=None):
    """Seeds default departments, classrooms, cameras, subjects and admin/faculty users."""
    database = db if db is not None else get_db()

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
        if not database.departments.find_one({'name': name}):
            d_id = get_next_sequence_value('departments', database)
            database.departments.insert_one({
                'id': d_id,
                'name': name,
                'code': code,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    # Classrooms
    rooms = [
        ('LAB-101', 'Block A', 40),
        ('LAB-204', 'Block B', 35),
        ('ROOM-101', 'Block A', 60),
        ('ROOM-202', 'Block B', 60),
        ('SEMINAR HALL', 'Block C', 120),
    ]
    for name, building, cap in rooms:
        if not database.classrooms.find_one({'name': name}):
            c_id = get_next_sequence_value('classrooms', database)
            database.classrooms.insert_one({
                'id': c_id,
                'name': name,
                'building': building,
                'capacity': cap,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    # Cameras
    cams = [
        ('CAM-01', 'Main Cam', 'Block A', 'LAB-101'),
        ('CAM-02', 'Secondary', 'Block B', 'LAB-204'),
        ('CAM-03', 'Room Cam', 'Block A', 'ROOM-101'),
    ]
    for cid, name, loc, room in cams:
        if not database.cameras.find_one({'camera_id': cid}):
            cam_id = get_next_sequence_value('cameras', database)
            database.cameras.insert_one({
                'id': cam_id,
                'camera_id': cid,
                'name': name,
                'location': loc,
                'room': room,
                'status': 'offline',
                'fps': 0.0,
                'resolution': '1280x720',
                'last_heartbeat': None,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    # Subjects
    aids_dept = database.departments.find_one({'code': 'AIDS'})
    aids_id = aids_dept['id'] if aids_dept else 1

    subjects = [
        ('AIDS-101', 'Machine Learning Foundations', aids_id, 5, 4),
        ('AIDS-102', 'Deep Learning & Computer Vision', aids_id, 6, 4),
        ('CS-201', 'Data Structures & Algorithms', aids_id, 3, 4),
        ('CS-301', 'Database Management Systems', aids_id, 4, 3),
        ('GEN-101', 'Engineering Mathematics', aids_id, 1, 4),
    ]
    for code, name, dept_id, sem, credits in subjects:
        if not database.subjects.find_one({'code': code}):
            s_id = get_next_sequence_value('subjects', database)
            database.subjects.insert_one({
                'id': s_id,
                'code': code,
                'name': name,
                'department_id': dept_id,
                'semester': sem,
                'credits': credits,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    # Roles
    roles = [
        ('super_admin', 'Super Administrator', 'Full system access'),
        ('department_head', 'Department Head', 'Department-level management'),
        ('faculty', 'Faculty Member', 'Attendance & session control'),
        ('attendance_operator', 'Operator', 'Camera & check-in monitor'),
        ('student', 'Student', 'Personal attendance view'),
    ]
    for rname, dname, desc in roles:
        if not database.roles.find_one({'name': rname}):
            r_id = get_next_sequence_value('roles', database)
            database.roles.insert_one({
                'id': r_id,
                'name': rname,
                'display_name': dname,
                'description': desc,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

    # Users: Admin
    if not database.users.find_one({'username': 'admin'}):
        pw_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode()
        u_id = get_next_sequence_value('users', database)
        database.users.insert_one({
            'id': u_id,
            'username': 'admin',
            'password_hash': pw_hash,
            'role': 'super_admin',
            'name': 'System Administrator',
            'full_name': 'System Administrator',
            'email': 'admin@drishti.ai',
            'department_id': aids_id,
            'student_id': None,
            'is_active': 1,
            'failed_login_attempts': 0,
            'locked_until': None,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None
        })

    # Users: Faculty
    if not database.users.find_one({'username': 'faculty'}):
        pw_hash = bcrypt.hashpw(b'faculty123', bcrypt.gensalt()).decode()
        u_id = get_next_sequence_value('users', database)
        database.users.insert_one({
            'id': u_id,
            'username': 'faculty',
            'password_hash': pw_hash,
            'role': 'faculty',
            'name': 'Dr. Demo Faculty',
            'full_name': 'Dr. Demo Faculty',
            'email': 'faculty@drishti.ai',
            'department_id': aids_id,
            'student_id': None,
            'is_active': 1,
            'failed_login_attempts': 0,
            'locked_until': None,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None
        })

    # Users: Student
    if not database.users.find_one({'username': 'student'}):
        pw_hash = bcrypt.hashpw(b'student123', bcrypt.gensalt()).decode()
        u_id = get_next_sequence_value('users', database)
        database.users.insert_one({
            'id': u_id,
            'username': 'student',
            'password_hash': pw_hash,
            'role': 'student',
            'name': 'Demo Student',
            'full_name': 'Demo Student',
            'email': 'student@drishti.ai',
            'department_id': aids_id,
            'student_id': 'STD-001',
            'is_active': 1,
            'failed_login_attempts': 0,
            'locked_until': None,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None
        })

    print("[MongoDB Atlas] Default seed records verified.")


# ── Helper for clean dict output ──────────────────────────────────────────────

def _clean_doc(doc):
    """Strips MongoDB ObjectId or converts it to string, ensuring dict compatibility."""
    if not doc:
        return None
    d = dict(doc)
    if '_id' in d:
        d['_id'] = str(d['_id'])
    return d


# ── Students ──────────────────────────────────────────────────────────────────

def add_student(student_id, name, department='General', email='', photo_path='',
                semester=1, roll_number='', year_of_joining=0):
    database = get_db()
    sid = str(student_id)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    existing = database.students.find_one({'student_id': sid})
    if existing:
        database.students.update_one(
            {'student_id': sid},
            {'$set': {
                'name': name,
                'department': department,
                'email': email,
                'photo_path': photo_path,
                'semester': semester,
                'roll_number': roll_number,
                'year_of_joining': year_of_joining,
            }}
        )
    else:
        new_id = get_next_sequence_value('students', database)
        database.students.insert_one({
            'id': new_id,
            'student_id': sid,
            'name': name,
            'department': department,
            'email': email,
            'photo_path': photo_path,
            'semester': semester,
            'roll_number': roll_number,
            'year_of_joining': year_of_joining,
            'enrollment_status': 'active',
            'created_at': now_str
        })

    # Auto-create user account for student access
    try:
        user_exists = database.users.find_one({'username': sid})
        dept_id = None
        if department:
            d_row = database.departments.find_one({'name': department})
            if d_row:
                dept_id = d_row.get('id')

        if not user_exists:
            default_pw = f"Drishti@{sid}"
            if len(default_pw) < 8:
                default_pw += "12345"
            create_user(
                username=sid,
                password=default_pw,
                role='student',
                full_name=name,
                email=email,
                department_id=dept_id,
                student_id=sid
            )
            print(f"[MongoDB Atlas] Auto-created user account for student {sid}")
    except Exception as e:
        print(f"[MongoDB Atlas] Failed to auto-create user for student {sid}: {e}")

    return True


def get_all_students():
    database = get_db()
    cursor = database.students.find().sort('created_at', DESCENDING)
    return [_clean_doc(d) for d in cursor]


def get_student_by_id(student_id):
    database = get_db()
    doc = database.students.find_one({'student_id': str(student_id)})
    return _clean_doc(doc)


def delete_student(student_id):
    database = get_db()
    sid = str(student_id)
    database.face_embeddings.delete_many({'student_id': sid})
    database.attendance.delete_many({'student_id': sid})
    database.students.delete_one({'student_id': sid})
    return True


# ── Face Embeddings ───────────────────────────────────────────────────────────

def store_face_embedding(student_id, embedding_array, quality_score=0.0, angle='front'):
    """Stores a face embedding as Binary pickle blob."""
    database = get_db()
    blob = Binary(pickle.dumps(embedding_array))
    new_id = get_next_sequence_value('face_embeddings', database)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database.face_embeddings.insert_one({
        'id': new_id,
        'student_id': str(student_id),
        'embedding_blob': blob,
        'quality_score': float(quality_score),
        'angle': angle,
        'captured_at': now_str
    })
    return True


def get_all_face_embeddings():
    """
    Returns all stored embeddings joined with student name and department.
    Used for loading the recognition engine.
    """
    database = get_db()
    docs = list(database.face_embeddings.find())

    # Build student lookup map for fast join
    students = {s['student_id']: s for s in database.students.find()}

    result = []
    for d in docs:
        try:
            raw_blob = d['embedding_blob']
            # Support both BSON Binary and bytes
            emb = pickle.loads(raw_blob)
            s_info = students.get(d['student_id'], {})
            result.append({
                'student_id': d['student_id'],
                'name': s_info.get('name', 'Unknown'),
                'department': s_info.get('department', 'General'),
                'embedding': emb,
                'quality_score': d.get('quality_score', 0.0),
                'angle': d.get('angle', 'front'),
            })
        except Exception as e:
            print(f"[MongoDB Atlas] Error deserializing embedding: {e}")
    return result


def delete_student_embeddings(student_id):
    database = get_db()
    database.face_embeddings.delete_many({'student_id': str(student_id)})
    return True


def count_student_embeddings(student_id):
    database = get_db()
    return database.face_embeddings.count_documents({'student_id': str(student_id)})


# ── Attendance ────────────────────────────────────────────────────────────────

def add_attendance(student_id, name, department='General', confidence=0.0,
                   email_sent=0, session_id=None, liveness_passed=0,
                   face_quality='unknown', status='Present'):
    """
    Logs attendance with session duplicate check, late arrival computation,
    and database-level constraint handling.
    Returns (success: bool, time_str or error_msg: str, final_status: str)
    """
    database = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    final_status = status
    sid = str(student_id)

    # Convert session_id to int if present
    sess_id = int(session_id) if session_id else None

    # Duplicate check for session
    if sess_id:
        existing = database.attendance.find_one({'student_id': sid, 'session_id': sess_id})
        if existing:
            return False, 'Already marked for this session', final_status
    else:
        # Global daily duplicate check (legacy mode)
        existing = database.attendance.find_one({'student_id': sid, 'date': today, 'session_id': None})
        if existing:
            return False, 'Already marked today', final_status

    # Compute Present/Late based on session threshold
    if sess_id and status == 'Present':
        sess = database.attendance_sessions.find_one({'id': sess_id})
        if sess and sess.get('start_time'):
            try:
                start_dt = datetime.strptime(f"{today} {sess['start_time']}", '%Y-%m-%d %H:%M')
                threshold_dt = start_dt + timedelta(minutes=sess.get('late_threshold_minutes', 10))
                now_dt = datetime.now()
                if now_dt > threshold_dt:
                    final_status = 'Late'
            except Exception:
                pass

    new_id = get_next_sequence_value('attendance', database)

    try:
        database.attendance.insert_one({
            'id': new_id,
            'student_id': sid,
            'name': name,
            'department': department,
            'date': today,
            'time': time_str,
            'timestamp': now_iso,
            'status': final_status,
            'confidence': float(confidence),
            'email_sent': int(email_sent),
            'session_id': sess_id,
            'liveness_passed': int(liveness_passed),
            'face_quality': face_quality,
            'override_reason': '',
            'override_by': ''
        })
        return True, time_str, final_status
    except pymongo.errors.DuplicateKeyError:
        return False, 'Duplicate attendance detected by database constraint', final_status


def get_attendance_logs(date_str=None, session_id=None, limit=500):
    database = get_db()
    query = {}
    if session_id:
        query['session_id'] = int(session_id)
    elif date_str:
        query['date'] = date_str

    cursor = database.attendance.find(query).sort('timestamp', DESCENDING).limit(limit)
    return [_clean_doc(d) for d in cursor]


def get_student_attendance_history(student_id, limit=100):
    database = get_db()
    sid = str(student_id)
    cursor = database.attendance.find({'student_id': sid}).sort('timestamp', DESCENDING).limit(limit)
    records = list(cursor)

    # Join session info (subject_name, classroom_name)
    session_ids = [r['session_id'] for r in records if r.get('session_id')]
    sessions = {}
    if session_ids:
        sess_cursor = database.attendance_sessions.find({'id': {'$in': session_ids}})
        sessions = {s['id']: s for s in sess_cursor}

    result = []
    for r in records:
        cleaned = _clean_doc(r)
        s_obj = sessions.get(r.get('session_id'), {})
        cleaned['subject_name'] = s_obj.get('subject_name', '')
        cleaned['classroom_name'] = s_obj.get('classroom_name', '')
        result.append(cleaned)
    return result


def delete_attendance_record(record_id):
    database = get_db()
    database.attendance.delete_one({'id': int(record_id)})
    return True


def override_attendance(record_id, new_status, reason, override_by):
    """Manual attendance correction with audit fields."""
    database = get_db()
    rid = int(record_id)
    row = database.attendance.find_one({'id': rid})
    if not row:
        return False, 'Record not found'

    old_status = row.get('status', 'Unknown')
    database.attendance.update_one(
        {'id': rid},
        {'$set': {
            'status': new_status,
            'override_reason': reason,
            'override_by': override_by
        }}
    )
    log_audit(None, override_by, 'override_attendance', 'attendance', str(rid),
              old_status, new_status)
    return True, old_status


def mark_absent_for_session(session_id):
    """Marks enrolled active students not yet marked in this session as Absent."""
    database = get_db()
    sess_id = int(session_id)
    today = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    now_iso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    marked = {
        r['student_id'] for r in database.attendance.find(
            {'session_id': sess_id}, {'student_id': 1}
        )
    }

    all_students = list(database.students.find({'enrollment_status': 'active'}))
    for s in all_students:
        sid = s['student_id']
        if sid not in marked:
            new_id = get_next_sequence_value('attendance', database)
            try:
                database.attendance.insert_one({
                    'id': new_id,
                    'student_id': sid,
                    'name': s['name'],
                    'department': s.get('department', 'General'),
                    'date': today,
                    'time': time_str,
                    'timestamp': now_iso,
                    'status': 'Absent',
                    'confidence': 0.0,
                    'email_sent': 0,
                    'session_id': sess_id,
                    'liveness_passed': 0,
                    'face_quality': 'n/a',
                    'override_reason': '',
                    'override_by': ''
                })
            except pymongo.errors.DuplicateKeyError:
                pass
    return True


# ── Sessions ──────────────────────────────────────────────────────────────────

def create_session(subject_name, faculty_name, classroom_name, department, semester,
                   date_str, start_time, late_threshold_minutes=10,
                   camera_id='CAM-01', created_by='admin',
                   subject_id=None, faculty_id=None, classroom_id=None):
    database = get_db()
    new_id = get_next_sequence_value('attendance_sessions', database)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database.attendance_sessions.insert_one({
        'id': new_id,
        'subject_id': subject_id,
        'faculty_id': faculty_id,
        'classroom_id': classroom_id,
        'camera_id': camera_id,
        'department': department,
        'semester': semester,
        'subject_name': subject_name,
        'faculty_name': faculty_name,
        'classroom_name': classroom_name,
        'date': date_str,
        'start_time': start_time,
        'end_time': '',
        'late_threshold_minutes': int(late_threshold_minutes),
        'status': 'scheduled',
        'created_by': created_by,
        'locked_at': None,
        'created_at': now_str
    })
    return new_id


def get_all_sessions(date_str=None):
    database = get_db()
    query = {'date': date_str} if date_str else {}
    cursor = database.attendance_sessions.find(query).sort([
        ('date', DESCENDING),
        ('start_time', DESCENDING)
    ]).limit(100)
    return [_clean_doc(d) for d in cursor]


def get_session(session_id):
    database = get_db()
    doc = database.attendance_sessions.find_one({'id': int(session_id)})
    return _clean_doc(doc)


def update_session_status(session_id, status, end_time=None):
    database = get_db()
    sess_id = int(session_id)
    update = {'status': status}
    if end_time:
        update['end_time'] = end_time
    if status == 'locked':
        update['locked_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database.attendance_sessions.update_one({'id': sess_id}, {'$set': update})
    return True


def get_active_session():
    database = get_db()
    doc = database.attendance_sessions.find_one({'status': 'active'}, sort=[('created_at', DESCENDING)])
    return _clean_doc(doc)


# ── Dashboard Stats ────────────────────────────────────────────────────────────

def get_dashboard_stats():
    database = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    total = database.students.count_documents({})

    present_ids = database.attendance.distinct('student_id', {'date': today, 'status': 'Present'})
    present = len(present_ids)

    late_ids = database.attendance.distinct('student_id', {'date': today, 'status': 'Late'})
    late = len(late_ids)

    absent_ids = database.attendance.distinct('student_id', {'date': today, 'status': 'Absent'})
    absent_marked = len(absent_ids)

    absent = max(0, total - present - late - absent_marked)
    rate = round(((present + late) / total * 100), 1) if total > 0 else 0.0

    active_sessions = database.attendance_sessions.count_documents({'status': 'active'})
    unresolved_anomalies = database.anomalies.count_documents({'resolved': 0})

    # At-risk count in last 30 days (< 75%)
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    pipeline = [
        {'$match': {'date': {'$gte': cutoff_date}}},
        {'$group': {
            '_id': '$student_id',
            'total': {'$sum': 1},
            'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
        }},
        {'$project': {
            'rate': {'$divide': ['$attended', '$total']}
        }},
        {'$match': {'rate': {'$lt': 0.75}}}
    ]
    risk_docs = list(database.attendance.aggregate(pipeline))
    risk_count = len(risk_docs)

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
    """Returns daily attendance statistics for the past N days."""
    database = get_db()
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    pipeline = [
        {'$match': {'date': {'$gte': cutoff_date}}},
        {'$group': {
            '_id': '$date',
            'students': {'$addToSet': '$student_id'},
            'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
        }},
        {'$project': {
            'date': '$_id',
            'total_marked': {'$size': '$students'},
            'attended': 1,
            '_id': 0
        }},
        {'$sort': {'date': 1}}
    ]
    return list(database.attendance.aggregate(pipeline))


def get_department_stats():
    """Returns per-department attendance rates for the past 30 days."""
    database = get_db()
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    pipeline = [
        {'$match': {'date': {'$gte': cutoff_date}}},
        {'$group': {
            '_id': '$department',
            'students': {'$addToSet': '$student_id'},
            'total': {'$sum': 1},
            'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
        }},
        {'$project': {
            'department': '$_id',
            'students': {'$size': '$students'},
            'attended': 1,
            'total': 1,
            'rate': {
                '$cond': [
                    {'$gt': ['$total', 0]},
                    {'$round': [{'$multiply': [{'$divide': ['$attended', '$total']}, 100]}, 1]},
                    0.0
                ]
            },
            '_id': 0
        }}
    ]
    return list(database.attendance.aggregate(pipeline))


def get_at_risk_students(threshold=75.0, days=30):
    """Students with attendance below threshold in past N days."""
    database = get_db()
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    pipeline = [
        {'$match': {'date': {'$gte': cutoff_date}}},
        {'$group': {
            '_id': '$student_id',
            'total_sessions': {'$sum': 1},
            'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
        }},
        {'$project': {
            'student_id': '$_id',
            'total_sessions': 1,
            'attended': 1,
            'rate': {
                '$cond': [
                    {'$gt': ['$total_sessions', 0]},
                    {'$round': [{'$multiply': [{'$divide': ['$attended', '$total_sessions']}, 100]}, 1]},
                    0.0
                ]
            },
            '_id': 0
        }},
        {'$match': {'rate': {'$lt': float(threshold)}}},
        {'$sort': {'rate': 1}}
    ]
    rows = list(database.attendance.aggregate(pipeline))

    # Join student profile metadata
    s_ids = [r['student_id'] for r in rows]
    students = {s['student_id']: s for s in database.students.find({'student_id': {'$in': s_ids}})}

    result = []
    for r in rows:
        sid = r['student_id']
        s_info = students.get(sid, {})
        result.append({
            'student_id': sid,
            'name': s_info.get('name', 'Unknown'),
            'department': s_info.get('department', 'General'),
            'semester': s_info.get('semester', 1),
            'total_sessions': r['total_sessions'],
            'attended': r['attended'],
            'rate': r['rate']
        })
    return result


def get_ai_insights():
    """Generates data-driven attendance insights directly from MongoDB collections."""
    insights = []
    try:
        database = get_db()
        cutoff_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        cutoff_60 = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

        # Insight 1: 30-day rate vs previous 30 days
        curr_pipeline = [
            {'$match': {'date': {'$gte': cutoff_30}}},
            {'$group': {
                '_id': None,
                'total': {'$sum': 1},
                'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
            }}
        ]
        curr_res = list(database.attendance.aggregate(curr_pipeline))
        curr_rate = round(curr_res[0]['attended'] / curr_res[0]['total'] * 100, 1) if curr_res and curr_res[0]['total'] > 0 else 0

        prev_pipeline = [
            {'$match': {'date': {'$gte': cutoff_60, '$lt': cutoff_30}}},
            {'$group': {
                '_id': None,
                'total': {'$sum': 1},
                'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
            }}
        ]
        prev_res = list(database.attendance.aggregate(prev_pipeline))
        prev_rate = round(prev_res[0]['attended'] / prev_res[0]['total'] * 100, 1) if prev_res and prev_res[0]['total'] > 0 else curr_rate

        diff = round(curr_rate - prev_rate, 1)
        arrow = '↑' if diff >= 0 else '↓'
        insights.append({
            'icon': 'trend-up' if diff >= 0 else 'trend-down',
            'type': 'positive' if diff >= 0 else 'warning',
            'text': f"Attendance {arrow} {abs(diff)}% vs. last month ({curr_rate}% this month)",
        })

        # Insight 2: At-risk count
        at_risk_list = get_at_risk_students(threshold=75.0, days=30)
        risk_count = len(at_risk_list)
        if risk_count > 0:
            insights.append({
                'icon': 'warning',
                'type': 'warning',
                'text': f"{risk_count} student{'s' if risk_count != 1 else ''} currently below the 75% attendance threshold",
            })

        # Insight 3: Best department
        dept_stats = get_department_stats()
        if dept_stats:
            best_dept = max(dept_stats, key=lambda x: x.get('rate', 0))
            if best_dept.get('rate', 0) > 0:
                insights.append({
                    'icon': 'trophy',
                    'type': 'positive',
                    'text': f"{best_dept['department']} leads with {best_dept['rate']}% average attendance",
                })

        # Insight 4: Late arrivals
        late_cnt = database.attendance.count_documents({'status': 'Late', 'date': {'$gte': cutoff_30}})
        if late_cnt > 0:
            insights.append({
                'icon': 'clock',
                'type': 'info',
                'text': f"{late_cnt} late arrivals recorded in the past 30 days",
            })

    except Exception as e:
        print(f"[MongoDB Insights] Error: {e}")
        insights.append({
            'icon': 'info',
            'type': 'info',
            'text': 'Insights will appear once attendance data is collected.',
        })

    return insights


def get_heatmap_data(student_id=None, months=3):
    """Returns calendar heatmap data."""
    database = get_db()
    cutoff_date = (datetime.now() - timedelta(days=months * 30)).strftime('%Y-%m-%d')

    if student_id:
        cursor = database.attendance.find(
            {'student_id': str(student_id), 'date': {'$gte': cutoff_date}},
            {'date': 1, 'status': 1, '_id': 0}
        ).sort('date', ASCENDING)
        return list(cursor)
    else:
        pipeline = [
            {'$match': {'date': {'$gte': cutoff_date}}},
            {'$group': {
                '_id': '$date',
                'total': {'$sum': 1},
                'attended': {'$sum': {'$cond': [{'$in': ['$status', ['Present', 'Late']]}, 1, 0]}}
            }},
            {'$project': {
                'date': '$_id',
                'rate': {
                    '$cond': [
                        {'$gt': ['$total', 0]},
                        {'$round': [{'$multiply': [{'$divide': ['$attended', '$total']}, 100]}, 1]},
                        0.0
                    ]
                },
                '_id': 0
            }},
            {'$sort': {'date': 1}}
        ]
        return list(database.attendance.aggregate(pipeline))


# ── Cameras ───────────────────────────────────────────────────────────────────

def get_all_cameras():
    database = get_db()
    cursor = database.cameras.find().sort('camera_id', ASCENDING)
    return [_clean_doc(d) for d in cursor]


def update_camera_heartbeat(camera_id, status='online', fps=0.0):
    database = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.cameras.update_one(
        {'camera_id': camera_id},
        {'$set': {
            'status': status,
            'fps': float(fps),
            'last_heartbeat': now_str
        }}
    )


# ── Anomalies ─────────────────────────────────────────────────────────────────

def log_anomaly(anomaly_type, description, session_id=None, student_id='', severity='medium'):
    database = get_db()
    new_id = get_next_sequence_value('anomalies', database)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database.anomalies.insert_one({
        'id': new_id,
        'session_id': int(session_id) if session_id else None,
        'student_id': str(student_id),
        'anomaly_type': anomaly_type,
        'description': description,
        'severity': severity,
        'resolved': 0,
        'created_at': now_str
    })
    return new_id


def get_anomalies(limit=50, unresolved_only=False):
    database = get_db()
    query = {'resolved': 0} if unresolved_only else {}
    cursor = database.anomalies.find(query).sort('created_at', DESCENDING).limit(limit)
    return [_clean_doc(d) for d in cursor]


# ── Notifications ─────────────────────────────────────────────────────────────

def create_notification(title, message, type='info', user_id=None):
    database = get_db()
    new_id = get_next_sequence_value('notifications', database)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database.notifications.insert_one({
        'id': new_id,
        'user_id': int(user_id) if user_id else None,
        'type': type,
        'title': title,
        'message': message,
        'read': 0,
        'created_at': now_str
    })
    return new_id


def get_notifications(user_id=None, limit=30):
    database = get_db()
    query = {}
    if user_id:
        query = {'$or': [{'user_id': int(user_id)}, {'user_id': None}]}
    cursor = database.notifications.find(query).sort('created_at', DESCENDING).limit(limit)
    return [_clean_doc(d) for d in cursor]


def mark_notification_read(notification_id):
    database = get_db()
    database.notifications.update_one({'id': int(notification_id)}, {'$set': {'read': 1}})


def get_unread_count(user_id=None):
    database = get_db()
    return database.notifications.count_documents({'read': 0})


# ── Audit Logs ────────────────────────────────────────────────────────────────

def log_audit(user_id, username, action, entity_type='', entity_id='',
              old_value='', new_value='', ip_address=''):
    try:
        database = get_db()
        new_id = get_next_sequence_value('audit_logs', database)
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        database.audit_logs.insert_one({
            'id': new_id,
            'user_id': int(user_id) if user_id else None,
            'username': username or 'system',
            'action': action,
            'entity_type': entity_type,
            'entity_id': str(entity_id),
            'old_value': str(old_value),
            'new_value': str(new_value),
            'ip_address': ip_address,
            'created_at': now_str
        })
    except Exception as e:
        print(f"[MongoDB Audit] Log failed: {e}")


def get_audit_logs(limit=100):
    database = get_db()
    cursor = database.audit_logs.find().sort('created_at', DESCENDING).limit(limit)
    return [_clean_doc(d) for d in cursor]


def get_audit_logs_filtered(limit: int = 100, username: str = None,
                             action: str = None, entity_type: str = None,
                             date_from: str = None, date_to: str = None) -> list:
    database = get_db()
    query = {}
    if username:
        query['username'] = username
    if action:
        query['action'] = {'$regex': action, '$options': 'i'}
    if entity_type:
        query['entity_type'] = entity_type
    if date_from or date_to:
        query['created_at'] = {}
        if date_from:
            query['created_at']['$gte'] = date_from
        if date_to:
            query['created_at']['$lte'] = date_to + ' 23:59:59'

    cursor = database.audit_logs.find(query).sort('created_at', DESCENDING).limit(limit)
    return [_clean_doc(d) for d in cursor]


# ── Auth & Users ──────────────────────────────────────────────────────────────

def verify_user(username: str, password: str):
    """
    Authenticate user against MongoDB Atlas.
    Implements brute-force lockout: 5 failures → 10-minute lock.
    """
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 10

    database = get_db()
    user = database.users.find_one({'username': username})
    if not user:
        return 'invalid_credentials'

    if not user.get('is_active', 1):
        return 'account_disabled'

    locked_until = user.get('locked_until')
    if locked_until:
        try:
            lock_dt = datetime.fromisoformat(str(locked_until))
            if datetime.now() < lock_dt:
                return 'account_locked'
            else:
                database.users.update_one(
                    {'id': user['id']},
                    {'$set': {'locked_until': None, 'failed_login_attempts': 0}}
                )
        except Exception:
            pass

    try:
        password_ok = bcrypt.checkpw(password.encode(), user['password_hash'].encode())
    except Exception:
        return 'invalid_credentials'

    if not password_ok:
        attempts = user.get('failed_login_attempts', 0) + 1
        if attempts >= MAX_ATTEMPTS:
            lock_until_dt = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            database.users.update_one(
                {'id': user['id']},
                {'$set': {'failed_login_attempts': attempts, 'locked_until': lock_until_dt}}
            )
        else:
            database.users.update_one(
                {'id': user['id']},
                {'$set': {'failed_login_attempts': attempts}}
            )
        return 'invalid_credentials'

    # Successful login
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.users.update_one(
        {'id': user['id']},
        {'$set': {
            'last_login': now_str,
            'failed_login_attempts': 0,
            'locked_until': None,
            'updated_at': now_str
        }}
    )
    fresh = database.users.find_one({'id': user['id']})
    return _clean_doc(fresh)


def get_all_users():
    database = get_db()
    cursor = database.users.find().sort('created_at', DESCENDING)
    departments = {d['id']: d['name'] for d in database.departments.find()}

    result = []
    for u in cursor:
        doc = _clean_doc(u)
        doc.pop('password_hash', None)
        doc['department_name'] = departments.get(doc.get('department_id'), '')
        doc['full_name'] = doc.get('full_name') or doc.get('name', '')
        result.append(doc)
    return result


def get_user_by_id(user_id: int):
    database = get_db()
    u = database.users.find_one({'id': int(user_id)})
    if not u:
        return None
    doc = _clean_doc(u)
    doc.pop('password_hash', None)
    if doc.get('department_id'):
        dept = database.departments.find_one({'id': doc['department_id']})
        doc['department_name'] = dept['name'] if dept else ''
    else:
        doc['department_name'] = ''
    doc['full_name'] = doc.get('full_name') or doc.get('name', '')
    return doc


def get_user_by_username(username: str):
    database = get_db()
    u = database.users.find_one({'username': username})
    if not u:
        return None
    doc = _clean_doc(u)
    doc.pop('password_hash', None)
    if doc.get('department_id'):
        dept = database.departments.find_one({'id': doc['department_id']})
        doc['department_name'] = dept['name'] if dept else ''
    else:
        doc['department_name'] = ''
    doc['full_name'] = doc.get('full_name') or doc.get('name', '')
    return doc


def create_user(username: str, password: str, role: str, full_name: str,
                email: str = '', department_id: int = None,
                student_id: str = None) -> int:
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters.')

    valid_roles = ['super_admin', 'department_head', 'faculty',
                   'attendance_operator', 'student']
    if role not in valid_roles:
        raise ValueError(f'Invalid role. Must be one of: {valid_roles}')

    database = get_db()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_id = get_next_sequence_value('users', database)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database.users.insert_one({
        'id': new_id,
        'username': username.strip(),
        'password_hash': pw_hash,
        'role': role,
        'name': full_name.strip(),
        'full_name': full_name.strip(),
        'email': email.strip(),
        'department_id': int(department_id) if department_id else None,
        'student_id': student_id,
        'is_active': 1,
        'failed_login_attempts': 0,
        'locked_until': None,
        'created_at': now_str,
        'updated_at': now_str,
        'last_login': None
    })
    return new_id


def update_user(user_id: int, **fields) -> bool:
    allowed = {'full_name', 'email', 'role', 'department_id', 'student_id', 'is_active'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    if 'full_name' in updates:
        updates['name'] = updates['full_name']
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    database = get_db()
    database.users.update_one({'id': int(user_id)}, {'$set': updates})
    return True


def set_user_active(user_id: int, is_active: bool) -> bool:
    database = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.users.update_one(
        {'id': int(user_id)},
        {'$set': {'is_active': 1 if is_active else 0, 'updated_at': now_str}}
    )
    return True


def unlock_user(user_id: int) -> bool:
    database = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.users.update_one(
        {'id': int(user_id)},
        {'$set': {'locked_until': None, 'failed_login_attempts': 0, 'updated_at': now_str}}
    )
    return True


def reset_user_password(user_id: int, new_password: str) -> bool:
    if len(new_password) < 8:
        raise ValueError('Password must be at least 8 characters.')
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    database = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.users.update_one(
        {'id': int(user_id)},
        {'$set': {
            'password_hash': pw_hash,
            'updated_at': now_str,
            'failed_login_attempts': 0,
            'locked_until': None
        }}
    )
    return True


def change_own_password(user_id: int, current_password: str, new_password: str) -> bool:
    if len(new_password) < 8:
        raise ValueError('New password must be at least 8 characters.')
    database = get_db()
    u = database.users.find_one({'id': int(user_id)})
    if not u:
        raise ValueError('User not found.')

    if not bcrypt.checkpw(current_password.encode(), u['password_hash'].encode()):
        raise ValueError('Current password is incorrect.')

    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database.users.update_one(
        {'id': int(user_id)},
        {'$set': {'password_hash': pw_hash, 'updated_at': now_str}}
    )
    return True


def get_subjects():
    database = get_db()
    cursor = database.subjects.find().sort('name', ASCENDING)
    return [_clean_doc(d) for d in cursor]


def get_classrooms():
    database = get_db()
    cursor = database.classrooms.find().sort('name', ASCENDING)
    return [_clean_doc(d) for d in cursor]
