import cv2
import os
import sys
import time
import database

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

    # Sanitize name for filename
    clean_name = student_name.replace(" ", "_")
    output_filename = f"{clean_name}_{student_id}.jpg"
    output_path = os.path.join(KNOWN_FACES_DIR, output_filename)

    print(f"[Capture Engine] Starting capture for {student_name} (ID: {student_id}, Dept: {department})...")
    print("[Capture Engine] Please look directly at the camera...")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    best_face = None
    best_score = -1.0
    captured = 0

    time.sleep(1.2)  # Camera warm-up delay

    while captured < target_captures:
        ret, frame = cap.read()
        if not ret:
            print("[Capture Engine] Error: Failed to grab webcam frame.")
            break

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

        cv2.imshow('Drishti AI — Face Enrollment', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[Capture Engine] Capture process cancelled by user.")
            break

        time.sleep(0.08)

    cap.release()
    cv2.destroyAllWindows()

    if best_face is not None:
        # Standardize face crop dimensions to 300x300
        best_face_resized = cv2.resize(best_face, (300, 300))
        cv2.imwrite(output_path, best_face_resized)
        
        # Save to database
        database.add_student(
            student_id=student_id,
            name=student_name,
            department=department,
            email=email,
            photo_path=output_path
        )
        print(f"[✓] Registration complete for {student_name}! Image saved: {output_path} (Sharpness: {best_score:.1f})")
        return True
    else:
        print("[!] Registration failed: No face detected during camera stream.")
        return False

if __name__ == "__main__":
    print("=== Drishti AI — Student Enrollment ===")
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
