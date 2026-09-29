import os
import sys
from datetime import datetime, timedelta
import random
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database

def seed_demo_data():
    database.init_db()
    database.seed_defaults()
    
    print("Seeding demo data using API...")
    
    students = [
        {"id": "101", "name": "Alice Smith", "dept": "Computer Science", "sem": 5},
        {"id": "102", "name": "Bob Johnson", "dept": "Computer Science", "sem": 5},
        {"id": "103", "name": "Charlie Brown", "dept": "Electrical", "sem": 3},
        {"id": "104", "name": "Diana Prince", "dept": "Mechanical", "sem": 7},
        {"id": "105", "name": "Eve Adams", "dept": "Civil", "sem": 1},
        {"id": "106", "name": "Frank White", "dept": "Information Technology", "sem": 5},
        {"id": "107", "name": "Grace Lee", "dept": "Computer Science", "sem": 7},
        {"id": "108", "name": "Hank Pym", "dept": "Electrical", "sem": 3},
        {"id": "109", "name": "Ivy Poison", "dept": "Mechanical", "sem": 5},
        {"id": "110", "name": "Jack Sparrow", "dept": "Civil", "sem": 5}
    ]
    
    with database.get_db_connection() as conn:
        c = conn.cursor()
        for s in students:
            try:
                c.execute('''
                    INSERT INTO students (student_id, name, department)
                    VALUES (?, ?, ?)
                ''', (s["id"], s["name"], s["dept"]))
            except sqlite3.IntegrityError:
                pass
        conn.commit()

    today = datetime.now()
    for i in range(30):
        d = today - timedelta(days=i)
        if d.weekday() > 4: # Skip weekends
            continue
            
        date_str = d.strftime('%Y-%m-%d')
        
        # We manually insert sessions since database.create_session uses CURRENT_DATE
        with database.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO attendance_sessions 
                (subject_name, faculty_name, classroom_name, department, semester, camera_id, date, start_time, late_threshold_minutes, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ("Demo Subject", "Dr. Demo", "Room 101", "Computer Science", 5, "CAM-01", date_str, "09:00:00", 10, "completed", "admin"))
            session_id = c.lastrowid
            
            for s in students:
                # 85% chance to be present
                status = random.choices(['Present', 'Late', 'Absent'], weights=[80, 10, 10])[0]
                
                if status != 'Absent':
                    time_str = "09:05:00" if status == 'Present' else "09:20:00"
                    conf = round(random.uniform(90.0, 99.9), 1)
                    
                    try:
                        c.execute('''
                            INSERT INTO attendance 
                            (student_id, date, time, status, confidence, liveness_passed, face_quality, session_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (s["id"], date_str, time_str, status, conf, 1, "Good", session_id))
                    except sqlite3.IntegrityError:
                        pass
            conn.commit()
            
    print("Demo data seeded successfully!")

if __name__ == '__main__':
    seed_demo_data()
