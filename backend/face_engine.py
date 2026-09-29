"""
Drishti AI — Face Engine v2.0
Unified face processing pipeline:
  - Multi-angle enrollment (5 angles, stores embeddings in DB)
  - Recognition with liveness, quality check, rules engine
  - Embedding cache for real-time performance
  - SocketIO broadcast on recognition events
"""
import cv2
import os
import sys
import time
import threading
import numpy as np
import face_recognition

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database
import camera_utils
from liveness_detector import LivenessDetector, check_face_quality

# ── Path Constants ─────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
DATA_DIR         = os.path.join(BASE_DIR, 'data')
KNOWN_FACES_DIR  = os.path.join(DATA_DIR, 'known_faces')
HAAR_CASCADE     = os.path.join(DATA_DIR, 'haarcascade_frontalface_default.xml')
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
MATCH_TOLERANCE = 0.45
COOLDOWN_SECONDS = 10   # Per-session cooldown between marks for same student

# ANGLES for multi-angle enrollment
ENROLLMENT_ANGLES = [
    ('front',       'Look Straight at Camera'),
    ('left',        'Turn Slightly LEFT'),
    ('right',       'Turn Slightly RIGHT'),
    ('up',          'Tilt Head Slightly UP'),
    ('down',        'Tilt Head Slightly DOWN'),
]

# ─────────────────────────────────────────────────────────────────────────────
# Embedding Cache (singleton per process)
# ─────────────────────────────────────────────────────────────────────────────

_embedding_cache = []     # List of {student_id, name, department, embedding}
_cache_lock = threading.Lock()
_cache_loaded = False


def load_embedding_cache(force=False):
    """
    Loads all face embeddings from DB into memory.
    Falls back to known_faces/ directory if DB has no embeddings.
    """
    global _embedding_cache, _cache_loaded
    with _cache_lock:
        if _cache_loaded and not force:
            return

        db_embeddings = database.get_all_face_embeddings()
        if db_embeddings:
            _embedding_cache = db_embeddings
            print(f"[Face Engine] Loaded {len(db_embeddings)} embeddings from DB.")
        else:
            # Fallback: load from known_faces/ files
            _embedding_cache = _load_from_known_faces_dir()
            print(f"[Face Engine] Fallback: loaded {len(_embedding_cache)} embeddings from known_faces/.")
        _cache_loaded = True


def _load_from_known_faces_dir(known_dir=KNOWN_FACES_DIR):
    """Backwards-compatible loader from known_faces/ directory."""
    result = []
    if not os.path.exists(known_dir):
        return result

    db_students = {s['student_id']: s for s in database.get_all_students()}

    for filename in os.listdir(known_dir):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        stem = os.path.splitext(filename)[0]
        try:
            parts = stem.rsplit('_', 1)
            raw_name, sid = parts[0].replace('_', ' '), parts[1]
        except (ValueError, IndexError):
            continue

        info = db_students.get(sid, {})
        img_path = os.path.join(known_dir, filename)
        try:
            img = face_recognition.load_image_file(img_path)
            encs = face_recognition.face_encodings(img)
            if encs:
                result.append({
                    'student_id': sid,
                    'name': info.get('name', raw_name),
                    'department': info.get('department', 'General'),
                    'embedding': encs[0],
                    'quality_score': 100.0,
                    'angle': 'front',
                })
        except Exception as e:
            print(f"[Face Engine] Error loading {filename}: {e}")
    return result


def invalidate_cache():
    """Call after new enrollment to force reload."""
    global _cache_loaded
    with _cache_lock:
        _cache_loaded = False


def get_embeddings_list():
    """Returns (embeddings_array, metadata_list) for fast batch matching."""
    with _cache_lock:
        if not _embedding_cache:
            return [], []
        embeddings = [e['embedding'] for e in _embedding_cache]
        meta = _embedding_cache
    return embeddings, meta


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment
# ─────────────────────────────────────────────────────────────────────────────

def enroll_student_multiangle(student_name, student_id, department='General',
                               email='', semester=1,
                               target_captures_per_angle=15,
                               progress_callback=None):
    """
    Captures 5 angles, selects best face per angle, stores embeddings in DB.
    progress_callback(step, total, message, angle_done) called on each step.
    Returns True on success.
    """
    database.init_db()
    os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

    # Register student in DB first
    database.add_student(
        student_id=student_id,
        name=student_name,
        department=department,
        email=email,
        semester=semester,
    )

    # Clear existing embeddings for re-enrollment
    database.delete_student_embeddings(student_id)

    cap, cam_idx, backend = camera_utils.get_working_camera(preferred_index=0)
    use_synthetic = cap is None
    if cap:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE)
    stored_angles = 0
    reference_saved = False

    for angle_idx, (angle_key, angle_label) in enumerate(ENROLLMENT_ANGLES):
        if progress_callback:
            progress_callback(angle_idx + 1, len(ENROLLMENT_ANGLES) + 1,
                              f'Capture: {angle_label}', angle_key)

        best_face = None
        best_embedding = None
        best_score = -1.0
        captures = 0

        print(f"[Enroll] Angle: {angle_label} — position yourself and hold still.")

        while captures < target_captures_per_angle:
            if not use_synthetic and cap:
                ret, frame = cap.read()
                if not ret or frame is None:
                    use_synthetic = True
                    frame = camera_utils.create_synthetic_frame('Camera Disconnected')
            else:
                frame = camera_utils.create_synthetic_frame(f'Enrollment — {angle_label}')
                time.sleep(0.05)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

            for (x, y, w, h) in faces:
                face_crop = frame[y:y+h, x:x+w]
                quality, score, issues = check_face_quality(face_crop)

                if quality in ('Good', 'Fair') and score > best_score:
                    # Try to compute embedding immediately for quality gate
                    try:
                        rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                        rgb_face_resized = cv2.resize(rgb_face, (300, 300))
                        encs = face_recognition.face_encodings(rgb_face_resized)
                        if encs:
                            best_score = score
                            best_face = cv2.resize(face_crop, (300, 300))
                            best_embedding = encs[0]
                    except Exception:
                        pass

                # Draw feedback on frame
                color = (0, 255, 0) if not issues else (0, 165, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            # Always increment per frame (not per face) to avoid infinite loop
            captures += 1

            # HUD overlay
            progress = int((captures / target_captures_per_angle) * 300)
            cv2.rectangle(frame, (20, 20), (320, 50), (30, 30, 30), -1)
            cv2.rectangle(frame, (20, 20), (20 + progress, 50), (99, 102, 241), -1)
            cv2.putText(frame, f'Angle {angle_idx+1}/{len(ENROLLMENT_ANGLES)}: {angle_label}',
                        (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, f'Score: {best_score:.0f} | Frame: {captures}/{target_captures_per_angle}',
                        (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 220, 255), 1)
            cv2.putText(frame, 'Drishti AI — Face Enrollment',
                        (20, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

            cv2.imshow('Drishti AI — Multi-Angle Enrollment', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[Enroll] Cancelled by user.")
                if cap:
                    cap.release()
                cv2.destroyAllWindows()
                return False

            time.sleep(0.05)

        # Store best capture for this angle
        if best_embedding is not None:
            database.store_face_embedding(student_id, best_embedding, best_score, angle_key)
            stored_angles += 1
            print(f"[Enroll] Stored {angle_key} embedding (score={best_score:.1f})")

            # Save reference image for front angle (backwards compat with known_faces/)
            if angle_key == 'front' and best_face is not None and not reference_saved:
                clean_name = student_name.replace(' ', '_')
                out_path = os.path.join(KNOWN_FACES_DIR, f'{clean_name}_{student_id}.jpg')
                cv2.imwrite(out_path, best_face)
                database.add_student(student_id=student_id, name=student_name,
                                     department=department, email=email,
                                     photo_path=out_path, semester=semester)
                reference_saved = True
        else:
            # Fallback: synthetic frame registration
            print(f"[Enroll] WARNING: No valid face captured for {angle_key}")

    if cap:
        cap.release()
    cv2.destroyAllWindows()

    if progress_callback:
        progress_callback(len(ENROLLMENT_ANGLES) + 1, len(ENROLLMENT_ANGLES) + 1,
                          'Generating embeddings...', 'complete')

    invalidate_cache()
    print(f"[Enroll] Complete: {stored_angles}/{len(ENROLLMENT_ANGLES)} angles stored for {student_name}")
    return stored_angles > 0


# ─────────────────────────────────────────────────────────────────────────────
# Recognition Engine
# ─────────────────────────────────────────────────────────────────────────────

class RecognitionSession:
    """
    Manages a single live attendance session with:
    - Liveness detection per face track
    - Attendance rules engine
    - SocketIO broadcast
    - Anomaly detection
    """

    def __init__(self, session_id=None, socketio=None):
        self.session_id = session_id
        self.socketio = socketio
        self.session_data = database.get_session(session_id) if session_id else None
        self.cooldown_tracker = {}      # student_id -> last_log_time
        self.liveness_trackers = {}     # face_track_key -> LivenessDetector
        self.attempt_tracker = {}       # student_id -> attempt_count (anomaly detection)
        self.running = False
        self.stats = {
            'faces_detected': 0,
            'recognized': 0,
            'unknown': 0,
            'liveness_passed': 0,
            'liveness_failed': 0,
            'fps': 0.0,
            'latency_ms': 0.0,
        }

    def _emit(self, event, data):
        if self.socketio:
            try:
                self.socketio.emit(event, data)
            except Exception:
                pass

    def _check_cooldown(self, student_id):
        now = time.time()
        last = self.cooldown_tracker.get(student_id, 0)
        return (now - last) > COOLDOWN_SECONDS

    def _anomaly(self, anomaly_type, description, student_id='', severity='medium'):
        aid = database.log_anomaly(anomaly_type, description,
                                   self.session_id, student_id, severity)
        database.create_notification(
            title=f'Anomaly: {anomaly_type}',
            message=description,
            type='warning'
        )
        self._emit('anomaly_detected', {
            'id': aid,
            'type': anomaly_type,
            'description': description,
            'student_id': student_id,
            'severity': severity,
            'time': time.strftime('%H:%M:%S'),
        })

    def run(self):
        """Main recognition loop. Blocks until stopped or 'q' pressed."""
        print(f"[Recognition] Starting session {self.session_id}...")
        load_embedding_cache()
        known_embeddings, known_meta = get_embeddings_list()
        print(f"[Recognition] {len(known_embeddings)} face embeddings loaded.")

        cap, cam_idx, backend = camera_utils.get_working_camera(preferred_index=0)
        use_synthetic = cap is None
        if cap:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.running = True
        frame_count = 0
        fps_start = time.time()

        while self.running:
            t_start = time.time()

            if not use_synthetic and cap:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        use_synthetic = True
                        frame = camera_utils.create_synthetic_frame('Camera Disconnected')
                        database.update_camera_heartbeat('CAM-01', 'error', 0)
            else:
                frame = camera_utils.create_synthetic_frame('Demo Tracking Feed')
                time.sleep(0.033)

            # Downscale for fast recognition
            small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            face_locs = face_recognition.face_locations(rgb_small, model='hog')
            face_encs = face_recognition.face_encodings(rgb_small, face_locs)

            self.stats['faces_detected'] = len(face_locs)
            recognized_count = 0
            unknown_count = 0

            for (top, right, bottom, left), face_enc in zip(face_locs, face_encs):
                # Scale back to full frame
                top, right, bottom, left = top*2, right*2, bottom*2, left*2
                face_crop = frame[top:bottom, left:right]

                # Quality check
                quality_label, quality_score, quality_issues = check_face_quality(face_crop)

                # Face matching
                student_id = None
                student_name = 'Unknown'
                dept = 'N/A'
                confidence = 0.0
                color = (60, 60, 220)  # Red for unknown

                if known_embeddings:
                    distances = face_recognition.face_distance(known_embeddings, face_enc)
                    best_idx = int(np.argmin(distances))
                    best_dist = distances[best_idx]

                    if best_dist < MATCH_TOLERANCE:
                        m = known_meta[best_idx]
                        confidence = round((1 - best_dist) * 100, 1)
                        student_id = m['student_id']
                        student_name = m['name']
                        dept = m['department']
                        color = (50, 200, 50)  # Green
                        recognized_count += 1
                    else:
                        unknown_count += 1
                else:
                    unknown_count += 1

                # Liveness per face track
                track_key = f"{student_id or 'unk'}_{top}_{left}"
                if track_key not in self.liveness_trackers:
                    self.liveness_trackers[track_key] = LivenessDetector()
                liveness_result = self.liveness_trackers[track_key].update(face_crop)
                live = liveness_result['liveness_passed']

                if live:
                    self.stats['liveness_passed'] += 1
                else:
                    self.stats['liveness_failed'] += 1

                # Unknown face anomaly
                if student_id is None:
                    if unknown_count == 1:  # Only log first unknown per frame
                        self._anomaly('unknown_face',
                                      f'Unidentified person at {time.strftime("%H:%M:%S")}',
                                      severity='low')
                else:
                    # Duplicate attempt anomaly
                    attempts = self.attempt_tracker.get(student_id, 0) + 1
                    self.attempt_tracker[student_id] = attempts
                    if attempts > 3 and not self._check_cooldown(student_id):
                        self._anomaly('duplicate_attempt',
                                      f'{student_name} ({student_id}) has {attempts} recognition attempts',
                                      student_id=student_id, severity='medium')

                    # Mark attendance if liveness passed and cooldown cleared
                    if live and self._check_cooldown(student_id):
                        success, time_marked, final_status = database.add_attendance(
                            student_id=student_id,
                            name=student_name,
                            department=dept,
                            confidence=confidence,
                            session_id=self.session_id,
                            liveness_passed=1,
                            face_quality=quality_label,
                        )
                        if success:
                            self.cooldown_tracker[student_id] = time.time()
                            print(f"[OK] {student_name} ({student_id}) → {final_status} @ {time_marked}")

                            # Broadcast to dashboard
                            self._emit('attendance_marked', {
                                'student_id': student_id,
                                'name': student_name,
                                'department': dept,
                                'confidence': confidence,
                                'liveness': 'PASSED',
                                'face_quality': quality_label,
                                'status': final_status,
                                'time': time_marked,
                                'session_id': self.session_id,
                            })

                            database.create_notification(
                                title='Attendance Marked',
                                message=f'{student_name} marked {final_status} at {time_marked}',
                                type='success'
                            )

                # Draw bounding box and labels
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                label_bg_y = top - 40 if top > 50 else bottom
                cv2.rectangle(frame, (left, label_bg_y), (right, label_bg_y + 40), color, -1)

                line1 = student_name if student_id else 'UNKNOWN'
                line2 = f'Match: {confidence}% | Live: {"✓" if live else "✗"} | Q: {quality_label}'
                cv2.putText(frame, line1, (left+4, label_bg_y + 14),
                            cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)
                cv2.putText(frame, line2, (left+4, label_bg_y + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)

            # FPS computation
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed > 1.0:
                self.stats['fps'] = round(frame_count / elapsed, 1)
                frame_count = 0
                fps_start = time.time()

            self.stats['recognized'] = recognized_count
            self.stats['unknown'] = unknown_count
            self.stats['latency_ms'] = round((time.time() - t_start) * 1000, 1)

            # HUD banner
            banner = (f"Drishti AI | FPS:{self.stats['fps']} | "
                      f"Faces:{len(face_locs)} | Recog:{recognized_count} | "
                      f"Unknown:{unknown_count} | Press Q to stop")
            cv2.putText(frame, banner, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 215, 0), 2)

            # Camera heartbeat
            if frame_count % 30 == 0:
                database.update_camera_heartbeat('CAM-01', 'online', self.stats['fps'])

            # Emit stats to dashboard
            if frame_count % 10 == 0:
                self._emit('camera_stats', self.stats)

            cv2.imshow(f'Drishti AI — Live Tracking (Session {self.session_id})', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break

        # Cleanup
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        for tracker in self.liveness_trackers.values():
            tracker.close()
        self.liveness_trackers.clear()
        print(f"[Recognition] Session {self.session_id} ended.")

    def stop(self):
        self.running = False
