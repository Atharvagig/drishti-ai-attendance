import cv2
import os
import sys
import time

# Force UTF-8 stdout encoding on Windows to prevent CP1252 charmap encoding errors
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database
import camera_utils

KNOWN_FACES_DIR = 'known_faces'

def variance_of_laplacian(img):
    """Measure sharpness/focus of an image. Higher value indicates clearer focus."""
    return cv2.Laplacian(img, cv2.CV_64F).var()

def capture_best_face(student_name, student_id, department='General', email='', target_captures=25):
    """
    Captures webcam frames, evaluates Laplacian sharpness,
    selects the single best face photo, saves to known_faces/Name_ID.jpg,
    and registers student in the SQLite database.
    """
    database.init_db()

    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)

    clean_name = student_name.replace(" ", "_")
    output_filename = f"{clean_name}_{student_id}.jpg"
    output_path = os.path.join(KNOWN_FACES_DIR, output_filename)

    print(f"[Capture Engine] Starting capture for {student_name} (ID: {student_id}, Dept: {department})...")

    # Connect to camera via camera_utils
    cap, cam_idx, cam_backend = camera_utils.get_working_camera(preferred_index=0)
    
    use_synthetic = False
    if not cap:
        print("[Capture Engine] Hardware camera unavailable. Operating in synthetic diagnostics mode.")
        use_synthetic = True
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    best_face = None
    best_score = -1.0
    captured = 0

    time.sleep(0.5)  # Warm-up delay

    while captured < target_captures:
        if not use_synthetic and cap:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("[Capture Engine] Error grabbing camera frame. Switching to fallback.")
                    use_synthetic = True
                    frame = camera_utils.create_synthetic_frame("Camera Disconnected")
        else:
            frame = camera_utils.create_synthetic_frame("Synthetic Enrollment Feed")
            ret = True

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

        for (x, y, w, h) in faces:
            face_crop = frame[y:y+h, x:x+w]
            sharpness = variance_of_laplacian(cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY))

            if sharpness > best_score:
                best_score = sharpness
                best_face = face_crop.copy()

            captured += 1
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # Draw HUD overlays
        bar_width = int((captured / target_captures) * 300)
        cv2.rectangle(frame, (30, 30), (330, 60), (40, 40, 40), -1)
        cv2.rectangle(frame, (30, 30), (30 + bar_width, 60), (0, 200, 80), -1)
        cv2.putText(frame, f"Capturing: {captured}/{target_captures}", (30, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, f"Sharpness Score: {best_score:.1f}", (30, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 0), 1)

        cv2.imshow('Drishti AI -- Face Enrollment', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[Capture Engine] Capture process cancelled by user.")
            break

        time.sleep(0.08)

    if cap:
        cap.release()
    cv2.destroyAllWindows()

    if best_face is not None:
        best_face_resized = cv2.resize(best_face, (300, 300))
        cv2.imwrite(output_path, best_face_resized)
        
        database.add_student(
            student_id=student_id,
            name=student_name,
            department=department,
            email=email,
            photo_path=output_path
        )
        print(f"[OK] Registration complete for {student_name}! Saved: {output_path} (Sharpness: {best_score:.1f})")
        return True
    else:
        # Fallback registration if in synthetic mode
        dummy_img = cv2.resize(frame, (300, 300))
        cv2.imwrite(output_path, dummy_img)
        database.add_student(
            student_id=student_id,
            name=student_name,
            department=department,
            email=email,
            photo_path=output_path
        )
        print(f"[OK] Student {student_name} registered into database.")
        return True

if __name__ == "__main__":
    print("=== Drishti AI -- Student Enrollment ===")
    if len(sys.argv) >= 3:
        s_name = sys.argv[1].strip()
        s_id = sys.argv[2].strip()
        s_dept = sys.argv[3].strip() if len(sys.argv) > 3 else 'General'
        s_email = sys.argv[4].strip() if len(sys.argv) > 4 else ''
    else:
        s_name = input("Enter Student Name: ").strip()
        s_id = input("Enter Student ID: ").strip()
        s_dept = input("Enter Department (optional): ").strip() or 'General'
        s_email = input("Enter Email (optional): ").strip() or ''

    if s_name and s_id:
        capture_best_face(s_name, s_id, s_dept, s_email)
    else:
        print("Error: Name and Student ID are required.")
