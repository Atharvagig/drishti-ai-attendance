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

if __name__ == '__main__':
    init_db()
