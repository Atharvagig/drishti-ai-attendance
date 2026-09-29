# Drishti AI — Day 1 Technical Audit

## 1. Current Architecture
The application follows a client-server architecture.
**Backend**: Python Flask REST API server with Socket.IO for real-time bidirectional communication. It handles routing, RBAC validation via decorators, and interacts with SQLite and openpyxl (Excel) for data persistence.
**Frontend**: Single Page Application (SPA) structured using Flask template rendering (`admin_panel.html`, `faculty_panel.html`, `student_panel.html`). Implements a modern glassmorphic UI.
**Core AI Engine**: Relies on `dlib` 128-D facial embeddings and `face_recognition` library to detect and recognize faces from a webcam feed. Integrates a liveness check using `mediapipe`.

## 2. Application Entry Point
The application is started by executing the launcher script:
```bash
python run.py
```
This script explicitly sets the working directory to `backend/`, inserts it into `sys.path`, and starts the Flask Socket.IO server (`app_flask.py`) on `http://0.0.0.0:5000`.

## 3. Technology Stack
- **Backend**: Python 3.10+, Flask, Flask-SocketIO
- **Frontend**: HTML5, Vanilla JavaScript, CSS3 (Glassmorphism)
- **Database**: SQLite3 (`attendance.db`)
- **Face Recognition**: `face_recognition` (dlib 128-D encodings)
- **Liveness**: MediaPipe
- **Realtime**: Socket.IO
- **Reporting**: `openpyxl`, `pandas` (Excel .xlsx sync)
- **Authentication**: Session-based, `bcrypt` password hashing, Custom RBAC module

## 4. Core Data Flow
Camera → Detection → Liveness → Recognition → Attendance → Database → Dashboard

1. **Camera**: `camera_utils.py` captures frames. If unavailable, synthetic fallback is used.
2. **Detection & Recognition**: Frames are downscaled and passed to `face_recognition.face_locations` (HOG model) and `face_recognition.face_encodings`.
3. **Identity Resolution**: Distance is computed against `KNOWN_FACES_DIR`. A tolerance of `< 0.45` determines identity.
4. **Attendance**: 30-second cooldown is verified. If passed, it delegates to `database.add_attendance`.
5. **Database**: SQLite record is created.
6. **Reporting**: Triggers `excel_manager.sync_attendance_to_excel` to synchronously append to master and daily `.xlsx` sheets.
7. **Email Alert**: Background thread dispatches SMTP alert.

## 5. Working Components
- ✅ Application startup (`run.py` successfully initializes the server).
- ✅ Database initialization (schema builds seamlessly).
- ✅ Camera diagnostic fallback mechanism.
- ✅ RBAC structure and decorators.

## 6. Broken Components
**Component:** `backend/excel_manager.py` (Fixed)
- **Problem:** If a user has the `Attendance_*.xlsx` file open in Excel, the OS locks it. `pandas.to_excel` and `openpyxl.save` would throw a `PermissionError`, causing the background thread to crash and halting further attendance logging.
- **Severity:** HIGH
- **Suggested fix:** Wrapped `df.to_excel` and `wb.save` in a `try...except PermissionError` block to catch the exception, print a warning, and allow the application to proceed gracefully without crashing. (Implemented).

## 7. Security Findings
- **Missing Ignore Rules:** `backend/data`, Excel files, and `venv` artifacts were lacking from `.gitignore`. Updated `.gitignore` to prevent committing PII (images, db, xlsx).
- **Environment Template:** The `.env` file contained placeholders (no exposed production secrets), but a `.env.example` was missing. Copied the placeholders to a committed `.env.example`.

## 8. Dependency Findings
- The repository was missing a `requirements.txt` listing the precise packages needed to run in a clean environment.
- A basic `requirements.txt` was created specifying `Flask`, `Flask-SocketIO`, `opencv-python`, `face_recognition`, `openpyxl`, `pandas`, `bcrypt`, `mediapipe`, etc.

## 9. Database Findings
- The SQLite database utilizes robust additive migrations ensuring backwards compatibility.
- Tables present include `users`, `roles`, `permissions`, `students`, `face_embeddings`, `attendance_sessions`.
- The use of `journal_mode=WAL` ensures concurrent read/write stability when accessing `attendance.db`.

## 10. Duplicate / Legacy Code
The following files are OBSOLETE CANDIDATES and should be evaluated for removal:
- `backend/legacy/app.py` & `backend/legacy/trainer.yml` (Legacy LBPH approach).
- `frontend/templates/index.html`, `admin.html`, `faculty.html`, `student.html`, `report.html` (They were split into `_panel.html` versions via `split_templates.py`).
- `Drishti_AI_Project.zip` and `Drishti_AI_v2.zip` (Old archive backups taking up space).

## 11. Day 2 Priorities
1. **Remove Obsolete Code:** Safely delete the confirmed obsolete templates and legacy folders to clean the workspace.
2. **Review Frontend Integration:** Verify that `static/app.js` correctly renders tabs and handles real-time socket events for the dashboard.
3. **Face Enrollment Verification:** Perform an end-to-end test of the `capture_faces.py` workflow with a real webcam.
4. **Attendance Edge Cases:** Test the liveness detection and ensure it accurately blocks spoofing attempts before logging attendance.
5. **UI Polish & Analytics:** Ensure the analytics cards in the glassmorphic dashboard reflect actual data queried from `/api/stats`.
