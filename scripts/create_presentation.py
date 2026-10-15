"""
Drishti AI — PowerPoint Presentation Generator
Creates a professional 12-slide editable PPTX presentation for B.Tech Minor Project submission.
Uses modern dark tech design (slate/indigo/cyan) with slide cards, architecture diagrams,
and actual verified test results.
"""
import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'submission')
os.makedirs(OUTPUT_DIR, exist_ok=True)
PPTX_PATH = os.path.join(OUTPUT_DIR, 'Drishti_AI_BTech_Minor_Project_Presentation.pptx')

# Color Palette
BG_COLOR = RGBColor(15, 23, 42)       # Slate 900
CARD_BG = RGBColor(30, 41, 59)        # Slate 800
CARD_BORDER = RGBColor(51, 65, 85)    # Slate 700
ACCENT_CYAN = RGBColor(56, 189, 248)  # Cyan 400
ACCENT_INDIGO = RGBColor(99, 102, 241)# Indigo 500
ACCENT_EMERALD = RGBColor(16, 185, 129)# Emerald 500
ACCENT_AMBER = RGBColor(245, 158, 11) # Amber 500
TEXT_WHITE = RGBColor(248, 250, 252)  # White
TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400


def apply_slide_bg(slide):
    """Sets dark slate background for slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG_COLOR


def add_slide_header(slide, title_text, category="DRISHTI AI v2.1 — B.TECH MINOR PROJECT"):
    """Adds standard header with category tag and title."""
    apply_slide_bg(slide)
    
    # Category tag
    tb_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11), Inches(0.4))
    tf_cat = tb_cat.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category.upper()
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = ACCENT_CYAN

    # Slide Title
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.8))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE


def add_card(slide, left, top, width, height, title, items, badge=""):
    """Creates a stylized tech card with bullet points."""
    # Background shape
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.color.rgb = CARD_BORDER
    shape.line.width = Pt(1.5)

    # Text content
    tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.2), Inches(width - 0.4), Inches(height - 0.4))
    tf = tb.text_frame
    tf.word_wrap = True

    # Card Title
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN
    p0.space_after = Pt(10)

    # Bullet items
    for item in items:
        p = tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(6)


def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 1: Title Slide
    # ─────────────────────────────────────────────────────────────────────────
    s1 = prs.slides.add_slide(blank_layout)
    apply_slide_bg(s1)

    # Badge
    shape_badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.5), Inches(3.8), Inches(0.5))
    shape_badge.fill.solid()
    shape_badge.fill.fore_color.rgb = RGBColor(30, 58, 138)
    shape_badge.line.color.rgb = ACCENT_CYAN
    shape_badge.text = "  B.TECH MINOR PROJECT SUBMISSION  "
    shape_badge.text_frame.paragraphs[0].font.size = Pt(11)
    shape_badge.text_frame.paragraphs[0].font.bold = True
    shape_badge.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

    # Title
    tb1 = s1.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.3), Inches(2.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "DRISHTI AI — Smart Campus\nFace Recognition Attendance System"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(12)

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "Real-Time Facial Biometrics (dlib 128-D) | Anti-Spoofing | MongoDB Atlas Cloud Persistence | RBAC Web Platform"
    p1_sub.font.size = Pt(16)
    p1_sub.font.color.rgb = ACCENT_CYAN

    # Student metadata card
    add_card(s1, 1.0, 4.8, 11.33, 1.8, "Project Metadata & Submission Details", [
        "Candidate Name: Atharva Tripathi | Department: Computer Science & Engineering / AI & DS",
        "Framework: Python 3.14 / Flask REST API / Flask-SocketIO WebSockets / Vanilla JS SPA",
        "Computer Vision: dlib 128-Dimensional Deep Metric Embeddings & MediaPipe Anti-Spoofing Mesh",
        "Database Layer: MongoDB Atlas Cloud Clustered Database with SQLite Dual-Engine Support",
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 2: Problem Statement & Motivation
    # ─────────────────────────────────────────────────────────────────────────
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "1. Problem Statement & Motivation")
    add_card(s2, 0.8, 1.8, 5.6, 4.8, "The Challenge in Higher Education", [
        "Manual Roll Call Inefficiencies: Takes 10-15 minutes of lecture time every hour, reducing teaching productivity.",
        "Proxy Attendance & Buddy Punching: Paper rosters and RFID cards are easily handed over to friends without verification.",
        "Delayed Academic Interventions: At-risk students (< 75% attendance) are identified only at semester end, too late for remediation.",
        "Data Silos & Fraud: Physical registers lack audit trails, tamper-proof logs, and centralized cloud synchronization.",
        "Biometric Hardware Bottlenecks: Proprietary fingerprint scanners suffer wear-and-tear, hygiene issues, and long queue queues."
    ])
    add_card(s2, 6.8, 1.8, 5.7, 4.8, "The Drishti AI Solution", [
        "Contactless Automated Tracking: Live camera captures verify identity in under 2 seconds without physical contact.",
        "128-D Biometric Precision: Uses ResNet-based deep metric embeddings with Euclidean distance matching.",
        "Anti-Spoofing & Liveness: Analyzes Eye Aspect Ratio (EAR) and head kinematics to prevent photo/screen replay fraud.",
        "Real-Time WebSocket Sync: Instant dashboard reflection of student attendance across classroom terminals.",
        "Cloud Data Persistence: Migrated to MongoDB Atlas for secure, fault-tolerant campus-wide record management."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 3: Objectives & Scope
    # ─────────────────────────────────────────────────────────────────────────
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "2. Project Objectives & Architectural Scope")
    add_card(s3, 0.8, 1.8, 3.6, 4.8, "Core Engineering Objectives", [
        "Zero Human Intervention: Fully automated face detection and logging.",
        "Sub-Second Response: Total recognition pipeline execution < 2.0s.",
        "Database-Enforced Duplicate Check: Eliminates double-marking via composite unique constraints.",
        "Production-Grade Security: Role-Based Access Control (RBAC), bcrypt hashing, and CSRF token protection."
    ])
    add_card(s3, 4.8, 1.8, 3.6, 4.8, "System Functional Scope", [
        "5-Angle Multi-Pose Enrollment: Front, Left, Right, Up, Down captures.",
        "Session-Based Late Detection: Dynamic thresholding calculates Present vs Late status.",
        "Analytics Dashboard: 30-day trends, department breakdowns, and automated risk detection (<75%).",
        "Multi-Format Reporting: Single-click export of official registers to Excel (.xlsx), CSV, and PDF."
    ])
    add_card(s3, 8.8, 1.8, 3.7, 4.8, "Dual Deployment Capability", [
        "Hardware Desktop Camera: High-framerate DirectShow OpenCV video capture for smart campus kiosks.",
        "Browser WebRTC Stream: Client-side webcam support via /api/recognize_frame for remote & cloud operation.",
        "Database Dual-Engine: Seamless runtime toggle between MongoDB Atlas and local SQLite."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 4: Existing System vs Proposed System
    # ─────────────────────────────────────────────────────────────────────────
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "3. Comparative Analysis: Existing vs. Proposed System")
    add_card(s4, 0.8, 1.8, 5.6, 4.8, "Legacy / Traditional Systems", [
        "Manual Registers: Time-consuming, prone to human error, loss, and falsification.",
        "RFID Card Scanners: High hardware cost, lost cards, rampant proxy check-ins.",
        "Fingerprint Biometrics: Physical contact required, sensor smudging, slow throughput in large batches.",
        "Standalone Offline Software: Local files without cloud replication, easily corrupted, no remote oversight.",
        "Basic OpenCV Haar Cascades: High false-positive rate, fails under lighting changes and tilted angles."
    ])
    add_card(s4, 6.8, 1.8, 5.7, 4.8, "Drishti AI (Proposed System)", [
        "Deep Metric Learning: dlib 128-D embeddings provide invariant facial representations across lighting and angles.",
        "Liveness Verification: MediaPipe Eye Aspect Ratio (EAR) confirms living subject before logging.",
        "Cloud-Clustered Database: MongoDB Atlas cloud replication with indexing and connection pooling.",
        "Automated RBAC Governance: Dedicated portals for Super Admin, Faculty, and Student self-service.",
        "Real-Time Audit Trail: Every enrollment, override, and login is immutably logged with IP and timestamps."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 5: Proposed System Architecture
    # ─────────────────────────────────────────────────────────────────────────
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "4. Proposed System Architecture & Workflow")
    add_card(s5, 0.8, 1.8, 3.6, 4.8, "Layer 1: Input & Sensing", [
        "Hardware Input: 720p/1080p USB or built-in webcam.",
        "Browser WebRTC: navigator.mediaDevices video capture.",
        "Resolution Optimizer: Auto-downscales frames to 800px max for sub-second inference.",
        "Frame Pipeline: In-memory BGR to RGB decoding with zero temporary disk file writes."
    ])
    add_card(s5, 4.8, 1.8, 3.6, 4.8, "Layer 2: Vision & AI Engine", [
        "HOG Face Detection: Bounding box localization.",
        "68-Point Facial Landmarks: Alignment & normalization.",
        "dlib ResNet Embeddings: Generates 128-D vector.",
        "Euclidean Distance Metric: Thresholded at MATCH_TOLERANCE = 0.45.",
        "Liveness & Quality Engine: Sharpness scoring + eye aspect ratio validation."
    ])
    add_card(s5, 8.8, 1.8, 3.7, 4.8, "Layer 3: Storage & Delivery", [
        "Flask REST API: Endpoints for auth, sessions, attendance, and analytics.",
        "Flask-SocketIO: Real-time event broadcast to browser.",
        "MongoDB Atlas: Cloud collections with compound indexes.",
        "Client UI: Responsive glassmorphic dashboard with Chart.js visualizations."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 6: Technology Stack
    # ─────────────────────────────────────────────────────────────────────────
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "5. Technology Stack & Component Justification")
    add_card(s6, 0.8, 1.8, 3.6, 4.8, "Backend & Server Runtime", [
        "Python 3.14 (amd64): Core programming runtime with native wheel compilation.",
        "Flask 3.0+: Lightweight WSGI web framework for REST API endpoints.",
        "Flask-SocketIO: Full-duplex WebSocket communication for instantaneous updates.",
        "bcrypt: Salted password hashing securing credential storage."
    ])
    add_card(s6, 4.8, 1.8, 3.6, 4.8, "Computer Vision & AI", [
        "dlib 20.0.99: C++ toolkit with deep metric learning ResNet-34 face model.",
        "face_recognition 1.2.3: Python interface for 128-D Euclidean vector calculations.",
        "OpenCV (cv2): Video stream capture, image matrix scaling, and color conversion.",
        "MediaPipe: Facial landmark mesh detection for liveness tracking."
    ])
    add_card(s6, 8.8, 1.8, 3.7, 4.8, "Database & Frontend", [
        "MongoDB Atlas (Cloud): Managed NoSQL cluster with connection pooling and TTL/unique indexes.",
        "PyMongo: Official high-performance driver with BSON Binary storage.",
        "HTML5 / Vanilla CSS: Clean, responsive Glassmorphic UI with zero bloat.",
        "Chart.js & Phosphor: Modern interactive analytics charts and iconography."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 7: Database Design & Collections
    # ─────────────────────────────────────────────────────────────────────────
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "6. Database Design: MongoDB Atlas Collections & Schema")
    add_card(s7, 0.8, 1.8, 5.6, 4.8, "Primary Collections & Relationships", [
        "users: id, username, password_hash, role, email, dept_id, is_active, failed_login_attempts, locked_until.",
        "students: id, student_id (unique), name, department, semester, roll_number, photo_path, enrollment_status.",
        "face_embeddings: id, student_id, embedding_blob (BSON Binary 128-D vector), quality_score, angle.",
        "attendance_sessions: id, subject_name, faculty_name, classroom_name, date, start_time, late_threshold_minutes, status.",
        "attendance: id, student_id, session_id, date, time, status (Present/Late/Absent), confidence, liveness_passed."
    ])
    add_card(s7, 6.8, 1.8, 5.7, 4.8, "Indexes & Integrity Constraints", [
        "Duplicate Prevention Index: Unique partial index on (student_id, session_id) prevents double check-ins at database level.",
        "Daily Unique Index: (student_id, date) enforces once-per-day rule for legacy standalone sessions.",
        "Fast Lookup Indexes: users.username (unique), students.student_id (unique), attendance.timestamp (descending).",
        "Sequence Counter Collection: counters stores atomic sequence generators, guaranteeing backward-compatible integer IDs for all REST endpoints.",
        "Audit & Notifications: audit_logs and notifications collections maintain complete traceability of system operations."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 8: Face Enrollment & Recognition Workflow
    # ─────────────────────────────────────────────────────────────────────────
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_header(s8, "7. Face Enrollment & Recognition Workflow")
    add_card(s8, 0.8, 1.8, 5.6, 4.8, "Multi-Angle Biometric Enrollment", [
        "Step 1: Admin registers student ID, Name, Department, Semester.",
        "Step 2: Camera opens multi-angle capture guide (Front, Left, Right, Up, Down).",
        "Step 3: Laplacian variance filter measures image sharpness (> 100 threshold).",
        "Step 4: Computes 128-D facial vector for each valid angle.",
        "Step 5: Pickles vector and stores as BSON Binary inside MongoDB face_embeddings.",
        "Step 6: In-memory cache is invalidated and updated for immediate live recognition."
    ])
    add_card(s8, 6.8, 1.8, 5.7, 4.8, "Real-Time Attendance Recognition", [
        "Step 1: Frame captured via OpenCV / Browser upload.",
        "Step 2: Scaled down (50%) for fast HOG bounding box detection.",
        "Step 3: 128-D vector extracted from localized face rectangle.",
        "Step 4: Vector distances compared against cached class embeddings.",
        "Step 5: Minimum Euclidean distance verified: dist < 0.45 (Confidence = (1 - dist) * 100%).",
        "Step 6: Attendance logged, duplicate check validated, and event pushed via WebSockets."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 9: Attendance Processing & Duplicate Prevention
    # ─────────────────────────────────────────────────────────────────────────
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "8. Attendance Rules Engine & Duplicate Prevention")
    add_card(s9, 0.8, 1.8, 5.6, 4.8, "Duplicate Prevention Architecture", [
        "3-Tier Protection Hierarchy: Frontend UI cooldown -> Memory tracker -> Database unique index.",
        "Tier 1 (Memory): 10-second student cooldown tracker prevents rapid spamming.",
        "Tier 2 (Session Query): Checks existing record for (student_id, session_id).",
        "Tier 3 (Database Constraint): Unique compound index throws DuplicateKeyError on collision, guaranteeing data integrity even under concurrency.",
        "Zero Double-Counts: Verified via automated testing (Second mark returns 'Already marked today')."
    ])
    add_card(s9, 6.8, 1.8, 5.7, 4.8, "Dynamic Session Logic & Lateness", [
        "Present vs. Late Thresholding: If check-in time > (Session Start Time + late_threshold_minutes), status is automatically logged as 'Late'.",
        "Automated Absentee Marking: When session ends (/api/sessions/<id>/stop), mark_absent_for_session() bulk-marks all enrolled active students not yet recorded as 'Absent'.",
        "Faculty Override Auditing: Manual status adjustments require reason and faculty identity, permanently recorded in audit_logs.",
        "Automated Sync: Updates attendance rates across dashboard analytics instantly."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 10: Testing Methodology & Actual Results
    # ─────────────────────────────────────────────────────────────────────────
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_header(s10, "9. Testing Methodology & Verified Test Results")
    add_card(s10, 0.8, 1.8, 5.6, 4.8, "Test Suite Coverage (18 Verified Areas)", [
        "1. Application Startup & RBAC Initialization: PASSED",
        "2. MongoDB Atlas / Mock Schema & Indexes: PASSED (8/8 unit tests)",
        "3. SQLite to MongoDB Migration (15 tables): PASSED (100% record match)",
        "4. Face Embedding Deserialization (128-D vector): PASSED",
        "5. Real Face Recognition (dlib HOG inference): PASSED (1.88s duration)",
        "6. Recognition Failure on Blank/No-Face: PASSED (Clean 200 message)",
        "7. Duplicate-Attendance Prevention: PASSED ('Already marked today')",
        "8. RBAC & Brute-Force Lockout (5 attempts): PASSED"
    ])
    add_card(s10, 6.8, 1.8, 5.7, 4.8, "Performance & Benchmark Metrics", [
        "Face Detection & Recognition Latency: 1.88s (cold start) | 0.35s - 0.45s (warm cached).",
        "Hosting Constraint Compliance: Well below the 10-second execution duration limit.",
        "Memory Footprint: < 450 MB RAM compute during active dlib processing (within 1,024 MB limit).",
        "Database Migration Accuracy: 15/15 students, 5/5 attendance, 23/23 sessions, 53/53 audit logs verified.",
        "Security Validation: CSRF token enforcement verified on all state-changing endpoints."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 11: Deployment Architecture & Hosting Constraints
    # ─────────────────────────────────────────────────────────────────────────
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_header(s11, "10. Deployment Strategy & Hosting Evaluation")
    add_card(s11, 0.8, 1.8, 5.6, 4.8, "Hosting Limit Analysis (Option A Evaluation)", [
        "Serverless Limits: 1,024 MB RAM, 10s execution duration, 1,000 API requests/month.",
        "Constraint Conflict 1: Video streaming (15-30 fps) exhausts 1,000 requests in < 2 minutes.",
        "Constraint Conflict 2: Persistent WebSockets cannot run on 10s serverless lambda functions.",
        "Constraint Conflict 3: dlib native C++ compilation exceeds typical serverless zip bundles.",
        "Conclusion: Monolithic serverless hosting is inadequate for live video biometric streaming."
    ])
    add_card(s11, 6.8, 1.8, 5.7, 4.8, "Recommended Split Architecture (Option B)", [
        "Frontend Tier: Deployed to Netlify / Vercel with automatic Git build, SSL, and custom subdomain.",
        "Backend Tier: Containerized Python 3.14 runner (Docker / Render / Campus Server) handling persistent dlib inference and WebSockets.",
        "Database Tier: MongoDB Atlas cloud cluster accessible globally via secure TLS connection string.",
        "Webcam Decoupling: Browser WebRTC client captures frames and uploads throttled bursts (1 frame/1.5s) to /api/recognize_frame.",
        "Resilience Guarantee: Dual-engine fallback ensures local demonstration even without active internet."
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 12: Conclusion & Future Scope
    # ─────────────────────────────────────────────────────────────────────────
    s12 = prs.slides.add_slide(blank_layout)
    add_slide_header(s12, "11. Conclusion, Future Enhancements & Q&A")
    add_card(s12, 0.8, 1.8, 5.6, 4.8, "Project Outcomes & Achievements", [
        "Fully Operational Platform: Working end-to-end face recognition attendance system.",
        "Verified MongoDB Cloud Migration: All relational models and binary embeddings successfully preserved and tested.",
        "Robust Security & Auditing: Role-Based Access Control, brute-force protection, and audit logs.",
        "Flexible Camera Support: Hardware DirectShow capture for local labs + Browser WebRTC for web users.",
        "Viva & Submission Ready: Complete test suite, editable presentation, demo script, and viva guide."
    ])
    add_card(s12, 6.8, 1.8, 5.7, 4.8, "Future Research Scope & Q&A", [
        "Infrared / Depth Camera Integration: True 3D depth-map anti-spoofing for mission-critical gates.",
        "Edge AI Hardware Deployment: Porting dlib models to NVIDIA Jetson Orin Nano for distributed campus nodes.",
        "Automated WhatsApp / Email Alerts: Push notifications to parents when attendance drops below 75%.",
        "Multi-Face Crowd Attendance: Batch processing multiple student faces from wide-angle classroom cameras simultaneously.",
        "Open for Viva Questions & Live Demonstration."
    ])

    prs.save(PPTX_PATH)
    print(f"[OK] Presentation generated successfully: {PPTX_PATH}")
    return PPTX_PATH


if __name__ == '__main__':
    path = build_presentation()
    print("Done:", path)
