import cv2
import os
import sys
import face_recognition
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import threading
import time

# Force UTF-8 stdout encoding on Windows to prevent CP1252 charmap encoding errors
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database
import excel_manager
import camera_utils

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

KNOWN_FACES_DIR = 'known_faces'
COOLDOWN_SECONDS = 30
MATCH_TOLERANCE = 0.45

# --- Email Alert Dispatch ---
def send_email_alert(name, student_id, time_str):
    """Dispatches attendance notification email asynchronously."""
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECEIVER_EMAIL:
        print("[Email Alert] Credentials omitted in .env -- skipping email dispatch.")
        return False

    def send_job():
        try:
            body = (f"Hello,\n\nAttendance has been logged successfully:\n"
                    f"- Student Name: {name}\n"
                    f"- Student ID: {student_id}\n"
                    f"- Check-in Time: {time_str}\n"
                    f"- Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"
                    f"Best regards,\nDrishti AI Attendance System")

            msg = MIMEText(body)
            msg['Subject'] = f"[Attendance Alert] Check-in logged for {name}"
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECEIVER_EMAIL

            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"[Email Alert] Notification sent successfully for {name} ({student_id}).")
        except Exception as err:
            print(f"[Email Alert] Error sending email: {err}")

    threading.Thread(target=send_job, daemon=True).start()
    return True

# --- Load Encodings & Metadata ---
def load_known_face_encodings(known_dir=KNOWN_FACES_DIR):
    """
    Loads face reference images and maps them to student records in SQLite database.
    Returns lists of (encodings, names, ids, departments).
    """
    database.init_db()
    db_students = {s['student_id']: s for s in database.get_all_students()}

    encodings = []
    names = []
    ids = []
    departments = []

    if not os.path.exists(known_dir):
        print(f"[INFO] '{known_dir}' directory not found. Please register students first.")
        return encodings, names, ids, departments

    for filename in os.listdir(known_dir):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        stem = os.path.splitext(filename)[0]
        try:
            parts = stem.rsplit('_', 1)
            name, sid = parts[0].replace("_", " "), parts[1]
        except (ValueError, IndexError):
            print(f"[WARN] Skipping '{filename}': Expected naming format 'Name_ID.jpg'")
            continue

        student_info = db_students.get(sid, {})
        dept = student_info.get('department', 'General')
        full_name = student_info.get('name', name)

        img_path = os.path.join(known_dir, filename)
        try:
            img = face_recognition.load_image_file(img_path)
            face_encs = face_recognition.face_encodings(img)

            if len(face_encs) == 0:
                print(f"[WARN] No face detected in reference photo '{filename}' -- skipping.")
                continue

            encodings.append(face_encs[0])
            names.append(full_name)
            ids.append(sid)
            departments.append(dept)
            print(f"[+] Loaded face embedding for: {full_name} (ID: {sid}, Dept: {dept})")
        except Exception as e:
            print(f"[ERROR] Error processing {filename}: {e}")

    return encodings, names, ids, departments

# --- Main Recognition Loop ---
def recognize_faces(known_dir=KNOWN_FACES_DIR):
    """Starts live tracking camera engine, performs dlib 128-D face recognition & updates DB/Excel."""
    print("[Recognition Engine] Initializing face recognition system...")
    known_encodings, known_names, known_ids, known_depts = load_known_face_encodings(known_dir)

    print(f"[OK] Successfully loaded {len(known_encodings)} student face model(s).")
    print("[Recognition Engine] Launching camera stream... Press 'q' to stop.\n")

    # Connect to camera via robust camera_utils
    cap, cam_idx, cam_backend = camera_utils.get_working_camera(preferred_index=0)
    
    use_synthetic = False
    if not cap:
        print("[Recognition Engine] Hardware camera unavailable. Running diagnostic synthetic feed.")
        use_synthetic = True
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    cooldown_tracker = {}

    while True:
        if not use_synthetic and cap:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("[Recognition Engine] Camera stream interrupted. Switching to diagnostic feed.")
                    use_synthetic = True
                    frame = camera_utils.create_synthetic_frame("Camera Disconnected")
        else:
            frame = camera_utils.create_synthetic_frame("Diagnostic Live Tracking Feed")
            time.sleep(0.03)

        # Downscale frame for fast recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detect face locations & compute encodings
        face_locations = face_recognition.face_locations(rgb_small, model='hog')
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        for (top, right, bottom, left), face_enc in zip(face_locations, face_encodings):
            top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2

            distances = face_recognition.face_distance(known_encodings, face_enc) if known_encodings else []
            best_idx = distances.argmin() if len(distances) > 0 else -1

            name = "Unknown"
            student_id = None
            dept = "N/A"
            confidence = 0.0
            color = (0, 0, 255)  # Red for unknown

            if best_idx >= 0 and distances[best_idx] < MATCH_TOLERANCE:
                confidence = round((1 - distances[best_idx]) * 100, 1)
                name = known_names[best_idx]
                student_id = known_ids[best_idx]
                dept = known_depts[best_idx]
                color = (0, 255, 0)  # Green for recognized

                # Cooldown check
                now = time.time()
                last_logged = cooldown_tracker.get(student_id, 0)
                if now - last_logged > COOLDOWN_SECONDS:
                    email_dispatched = 1 if (SENDER_EMAIL and SENDER_PASSWORD) else 0
                    success, time_marked = database.add_attendance(
                        student_id=student_id,
                        name=name,
                        department=dept,
                        confidence=confidence,
                        email_sent=email_dispatched
                    )

                    if success:
                        excel_manager.sync_attendance_to_excel(
                            student_id=student_id,
                            name=name,
                            department=dept,
                            time_str=time_marked,
                            confidence=confidence,
                            email_sent=email_dispatched
                        )

                        if email_dispatched:
                            send_email_alert(name, student_id, time_marked)

                        cooldown_tracker[student_id] = now
                        print(f"[OK] Check-in logged for {name} ({student_id}) at {time_marked}")

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 42), (right, bottom), color, cv2.FILLED)

            label_text = f"{name}" if name == "Unknown" else f"{name} ({confidence}%)"
            cv2.putText(frame, label_text, (left + 6, bottom - 12),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1)

        status_banner = f"Drishti AI Tracker | Active Faces: {len(face_locations)} | Press 'q' to exit"
        cv2.putText(frame, status_banner, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow('Drishti AI -- Live Tracking Engine', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[Recognition Engine] Tracking session ended by operator.")
            break

    if cap:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_faces()
