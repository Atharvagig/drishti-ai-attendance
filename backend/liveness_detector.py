"""
Drishti AI — Liveness Detector v1.0
Uses MediaPipe Face Mesh to detect:
  1. Blink detection via Eye Aspect Ratio (EAR)
  2. Head movement via nose-tip displacement
No additional dependencies — MediaPipe is already installed.
"""
import numpy as np
import time

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    MP_AVAILABLE = True
except (ImportError, AttributeError) as e:
    MP_AVAILABLE = False
    print(f"[Liveness] MediaPipe not available ({e}) — liveness disabled.")


# MediaPipe landmark indices for eyes
# Left eye: 362, 385, 387, 263, 373, 380
# Right eye: 33, 160, 158, 133, 153, 144
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
NOSE_TIP = 4


def _eye_aspect_ratio(landmarks, eye_indices, w, h):
    """Compute EAR from normalized landmarks."""
    pts = []
    for idx in eye_indices:
        lm = landmarks[idx]
        pts.append(np.array([lm.x * w, lm.y * h]))

    # EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    if C < 1e-6:
        return 0.3
    return (A + B) / (2.0 * C)


class LivenessDetector:
    """
    Per-session liveness tracker. Create one instance per attendance session.
    Call update(frame) each frame and check is_live to get status.
    """

    EAR_THRESHOLD = 0.22       # Below this = eye closed
    BLINK_CONSEC_FRAMES = 2    # Frames closed to count as blink
    HEAD_MOVE_THRESHOLD = 0.03 # Normalized nose displacement to count as movement
    REQUIRED_BLINKS = 1        # Blinks needed to pass
    REQUIRED_MOVES = 2         # Head movements needed (alternative path)

    def __init__(self):
        self.blink_count = 0
        self.move_count = 0
        self.ear_counter = 0       # Consecutive frames below threshold
        self.last_nose = None
        self.passed = False
        self.frames_checked = 0
        self.status_detail = 'Checking liveness...'

        if MP_AVAILABLE:
            self.mesh = mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.mesh = None

    def update(self, frame_bgr):
        """
        Process one BGR frame. Updates internal state.
        Returns dict: {liveness_passed, blinks, moves, ear, status}
        """
        if not MP_AVAILABLE or self.mesh is None:
            # If MediaPipe unavailable, auto-pass after 5 frames (graceful degradation)
            self.frames_checked += 1
            if self.frames_checked > 5:
                self.passed = True
                self.status_detail = 'Liveness check bypassed (MediaPipe unavailable)'
            return self._result()

        import cv2
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.mesh.process(rgb)

        if not results.multi_face_landmarks:
            self.status_detail = 'No face detected'
            return self._result()

        lms = results.multi_face_landmarks[0].landmark
        self.frames_checked += 1

        # Compute EAR for both eyes
        left_ear = _eye_aspect_ratio(lms, LEFT_EYE, w, h)
        right_ear = _eye_aspect_ratio(lms, RIGHT_EYE, w, h)
        ear = (left_ear + right_ear) / 2.0

        # Blink detection
        if ear < self.EAR_THRESHOLD:
            self.ear_counter += 1
        else:
            if self.ear_counter >= self.BLINK_CONSEC_FRAMES:
                self.blink_count += 1
            self.ear_counter = 0

        # Head movement detection via nose tip
        nose = lms[NOSE_TIP]
        nose_pos = np.array([nose.x, nose.y])
        if self.last_nose is not None:
            displacement = np.linalg.norm(nose_pos - self.last_nose)
            if displacement > self.HEAD_MOVE_THRESHOLD:
                self.move_count += 1
        self.last_nose = nose_pos

        # Determine if liveness is passed
        if self.blink_count >= self.REQUIRED_BLINKS or self.move_count >= self.REQUIRED_MOVES:
            self.passed = True
            self.status_detail = f'Liveness PASSED (blinks={self.blink_count}, moves={self.move_count})'
        else:
            blinks_needed = max(0, self.REQUIRED_BLINKS - self.blink_count)
            self.status_detail = f'Please blink {blinks_needed}x or move your head'

        return self._result(ear=ear)

    def _result(self, ear=0.0):
        return {
            'liveness_passed': self.passed,
            'blinks': self.blink_count,
            'moves': self.move_count,
            'ear': round(ear, 3),
            'status': self.status_detail,
        }

    def reset(self):
        self.blink_count = 0
        self.move_count = 0
        self.ear_counter = 0
        self.last_nose = None
        self.passed = False
        self.frames_checked = 0
        self.status_detail = 'Checking liveness...'

    def close(self):
        if self.mesh:
            self.mesh.close()


def check_face_quality(face_crop_bgr):
    """
    Quick quality assessment on a face crop.
    Returns (quality_label, quality_score, issues)
    """
    import cv2
    h, w = face_crop_bgr.shape[:2]
    issues = []

    # Size check
    if w < 60 or h < 60:
        issues.append('Face too far')
    elif w > 600 or h > 600:
        issues.append('Face too close')

    # Sharpness (Laplacian variance)
    gray = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if lap_var < 50:
        issues.append('Image blurry or poor lighting')

    # Brightness check
    mean_brightness = gray.mean()
    if mean_brightness < 50:
        issues.append('Too dark')
    elif mean_brightness > 220:
        issues.append('Overexposed')

    if not issues:
        quality = 'Good'
    elif len(issues) == 1:
        quality = 'Fair'
    else:
        quality = 'Poor'

    return quality, round(lap_var, 1), issues
