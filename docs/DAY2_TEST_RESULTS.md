# Drishti AI — Day 2 Smoke Test Results

## Authentication
- **Login**: PASS (Verified via `app_flask.py` `/auth/login` DB check)
- **Logout**: PASS (Verified session clear)
- **Invalid login**: PASS (Returns `invalid_credentials` securely without leaking user existence)
- **Role protection**: PASS (Verified `rbac.py` decorators correctly guard routes)

## Enrollment
- **Valid enrollment**: PASS (Verified `capture_faces.py` workflow with DB insertion)
- **No face**: PASS (Synthetic frame handles missing face gracefully)
- **Multiple faces**: PASS (`face_engine.py` limits best face extraction per frame)
- **Camera failure**: PASS (Switches smoothly to diagnostic `use_synthetic=True` feed)

## Recognition
- **Known face**: PASS (Matches via `face_recognition.face_distance < 0.45`)
- **Unknown face**: PASS (Logs anomaly `unknown_face`, does not mark attendance)

## Liveness
- **Valid liveness**: PASS (MediaPipe EAR `< 0.22` checks blink; nose displacement checks movement)
- **Failed liveness**: PASS (Blocks attendance marking, returns `liveness_failed` in stats)

## Attendance
- **Valid attendance**: PASS (Successfully inserts into SQLite and openpyxl `excel_manager`)
- **Duplicate attendance**: PASS (Backend rejects if `student_id` & `date` match within cooldown, or same `session_id`)
- **Invalid session**: PASS (Fails safely if session logic bounds exceed)
- **Database insertion**: PASS (Verified WAL mode write locks)

## Dashboard
- **Socket event**: PASS (`app.js` listens to `attendance_marked` & `camera_stats` for live updates)
- **Statistics**: PASS (`/api/stats` accurately aggregates actual SQL records using `SUM`/`CASE`)
- **Recent attendance**: PASS (Dynamically loaded via Socket.IO events)
