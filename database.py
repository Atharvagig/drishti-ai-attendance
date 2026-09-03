import sqlite3
import os
from datetime import datetime

DB_PATH = 'attendance.db'

def get_db_connection():
    """Returns a SQLite database connection with row factory configured."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Students table
        cursor.execute('''
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
        
        # Attendance table
        cursor.execute('''
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
        
        conn.commit()
    print("[Database] SQLite database initialized successfully.")

# --- Student CRUD Functions ---

def add_student(student_id, name, department='General', email='', photo_path=''):
    """Inserts or updates a student record in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students (student_id, name, department, email, photo_path)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                name=excluded.name,
                department=excluded.department,
                email=excluded.email,
                photo_path=excluded.photo_path
        ''', (str(student_id), name, department, email, photo_path))
        conn.commit()
    return True

def get_all_students():
    """Returns all registered students as a list of dicts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students ORDER BY created_at DESC')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_student_by_id(student_id):
    """Retrieves a single student by student_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students WHERE student_id = ?', (str(student_id),))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_student(student_id):
    """Deletes a student record and associated attendance history."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM students WHERE student_id = ?', (str(student_id),))
        cursor.execute('DELETE FROM attendance WHERE student_id = ?', (str(student_id),))
        conn.commit()
    return True

# --- Attendance CRUD Functions ---

def add_attendance(student_id, name, department='General', confidence=0.0, email_sent=0):
    """Logs an attendance record for today if not already marked."""
    today = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if already marked today
        cursor.execute('SELECT id FROM attendance WHERE student_id = ? AND date = ?', (str(student_id), today))
        if cursor.fetchone():
            return False, "Already marked today"

        cursor.execute('''
            INSERT INTO attendance (student_id, name, department, date, time, status, confidence, email_sent)
            VALUES (?, ?, ?, ?, ?, 'Present', ?, ?)
        ''', (str(student_id), name, department, today, time_str, float(confidence), int(email_sent)))
        conn.commit()
    return True, time_str

def get_attendance_logs(date_str=None):
    """Retrieves attendance logs, optionally filtered by date (YYYY-MM-DD)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if date_str:
            cursor.execute('SELECT * FROM attendance WHERE date = ? ORDER BY timestamp DESC', (date_str,))
        else:
            cursor.execute('SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 500')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_attendance_record(record_id):
    """Deletes a specific attendance log entry by database ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM attendance WHERE id = ?', (record_id,))
        conn.commit()
    return True

def get_dashboard_stats():
    """Computes summary metrics for the dashboard."""
    today = datetime.now().strftime('%Y-%m-%d')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM students')
        total_registered = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT student_id) as count FROM attendance WHERE date = ?', (today,))
        present_today = cursor.fetchone()['count']
        
        absent_today = max(0, total_registered - present_today)
        attendance_rate = round((present_today / total_registered * 100), 1) if total_registered > 0 else 0.0

        return {
            'total_registered': total_registered,
            'present_today': present_today,
            'absent_today': absent_today,
            'attendance_rate': attendance_rate,
            'today_date': today
        }

if __name__ == '__main__':
    init_db()
    print("[Database] Schema & CRUD functions ready.")
