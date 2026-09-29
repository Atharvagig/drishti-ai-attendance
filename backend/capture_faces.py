"""
Drishti AI — Face Capture & Enrollment v2.0
Multi-angle enrollment: captures 5 angles, stores 128-D embeddings in DB.
Backwards-compatible: also saves known_faces/Name_ID.jpg for legacy flow.
"""
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database
from face_engine import enroll_student_multiangle


def progress_cb(step, total, message, angle):
    bar_len = 30
    filled = int(bar_len * step / total)
    bar = '█' * filled + '░' * (bar_len - filled)
    print(f"\r[{bar}] Step {step}/{total}: {message}  ", end='', flush=True)
    if step == total:
        print()


if __name__ == '__main__':
    print('=' * 60)
    print('  DRISHTI AI — Multi-Angle Face Enrollment v2.0')
    print('=' * 60)

    if len(sys.argv) >= 3:
        s_name  = sys.argv[1].strip()
        s_id    = sys.argv[2].strip()
        s_dept  = sys.argv[3].strip() if len(sys.argv) > 3 else 'General'
        s_email = sys.argv[4].strip() if len(sys.argv) > 4 else ''
        s_sem   = int(sys.argv[5])   if len(sys.argv) > 5 else 1
    else:
        s_name  = input('Full Name: ').strip()
        s_id    = input('Student ID: ').strip()
        s_dept  = input('Department (optional): ').strip() or 'General'
        s_email = input('Email (optional): ').strip() or ''
        s_sem   = int(input('Semester (1-8): ').strip() or '1')

    if not s_name or not s_id:
        print('[ERROR] Name and Student ID are required.')
        sys.exit(1)

    print(f'\nEnrolling: {s_name} | ID: {s_id} | Dept: {s_dept} | Sem: {s_sem}')
    print('Follow the on-screen angle instructions. Press Q to cancel.\n')

    database.init_db()

    success = enroll_student_multiangle(
        student_name=s_name,
        student_id=s_id,
        department=s_dept,
        email=s_email,
        semester=s_sem,
        target_captures_per_angle=20,
        progress_callback=progress_cb,
    )

    if success:
        count = database.count_student_embeddings(s_id)
        print(f'\n[OK] Enrollment complete: {count} face embeddings stored for {s_name}.')
        sys.exit(0)
    else:
        print('\n[ERROR] Enrollment failed or was cancelled.')
        sys.exit(1)
