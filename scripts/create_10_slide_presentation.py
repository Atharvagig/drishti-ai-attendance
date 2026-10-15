"""
Drishti AI — 10-Slide B.Tech Minor Project Presentation Generator
Generates a 10-slide presentation in PPTX format.
Design: Dark tech aesthetic (Slate 900 background, Slate 800 cards, Slate 700 borders,
Cyan / Indigo / Emerald accents, clear hierarchy, structured metrics, 16:9 widescreen).
"""
import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'submission')
os.makedirs(OUTPUT_DIR, exist_ok=True)
PPTX_PATH_10 = os.path.join(OUTPUT_DIR, 'Drishti_AI_10_Slide_Presentation.pptx')
PPTX_PATH_DEFAULT = os.path.join(OUTPUT_DIR, 'Drishti_AI_BTech_Minor_Project_Presentation.pptx')

# Color Palette
BG_COLOR = RGBColor(15, 23, 42)        # Slate 900
CARD_BG = RGBColor(30, 41, 59)         # Slate 800
CARD_BORDER = RGBColor(51, 65, 85)     # Slate 700
ACCENT_CYAN = RGBColor(56, 189, 248)   # Cyan 400
ACCENT_INDIGO = RGBColor(99, 102, 241) # Indigo 500
ACCENT_EMERALD = RGBColor(16, 185, 129)# Emerald 500
ACCENT_AMBER = RGBColor(245, 158, 11)  # Amber 500
TEXT_WHITE = RGBColor(248, 250, 252)   # White
TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400


def apply_slide_bg(slide):
    """Sets dark slate background for slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = BG_COLOR


def add_slide_header(slide, title_text, slide_number_str=""):
    """Adds standard header with category tag and title."""
    apply_slide_bg(slide)

    # Category / Slide Number tag
    tb_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11), Inches(0.35))
    tf_cat = tb_cat.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = f"DRISHTI AI v2.1 -- B.TECH MINOR PROJECT  |  SLIDE {slide_number_str}" if slide_number_str else "DRISHTI AI v2.1 -- B.TECH MINOR PROJECT"
    p_cat.font.size = Pt(11)
    p_cat.font.bold = True
    p_cat.font.color.rgb = ACCENT_CYAN

    # Slide Title
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.8), Inches(0.8))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_WHITE


def add_card(slide, left, top, width, height, title, items, title_color=ACCENT_CYAN):
    """Creates a stylized tech card with bullet points."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.color.rgb = CARD_BORDER
    shape.line.width = Pt(1.5)

    tb = slide.shapes.add_textbox(Inches(left + 0.25), Inches(top + 0.22), Inches(width - 0.5), Inches(height - 0.44))
    tf = tb.text_frame
    tf.word_wrap = True

    # Title
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = title_color
    p0.space_after = Pt(10)

    # Bullet items
    for item in items:
        p = tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.size = Pt(11.5)
        p.font.color.rgb = TEXT_MUTED
        p.space_after = Pt(5)


def build_10_slide_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 1: Title & Overview
    # ═════════════════════════════════════════════════════════════════════════
    s1 = prs.slides.add_slide(blank_layout)
    apply_slide_bg(s1)

    # Badge chip
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(1.3), Inches(4.2), Inches(0.45))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(30, 58, 138)
    badge.line.color.rgb = ACCENT_CYAN
    badge.text = "  B.TECH MINOR PROJECT PRESENTATION  "
    badge.text_frame.paragraphs[0].font.size = Pt(11)
    badge.text_frame.paragraphs[0].font.bold = True
    badge.text_frame.paragraphs[0].font.color.rgb = ACCENT_CYAN

    # Main Title
    tb1 = s1.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(11.5), Inches(2.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "DRISHTI AI\nSmart Campus Biometric Attendance Platform"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(10)

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "Real-Time Facial Biometrics (dlib 128-D) | Anti-Spoofing | Cloud Clustered Database (MongoDB Atlas) | Centralized RBAC"
    p1_sub.font.size = Pt(15)
    p1_sub.font.color.rgb = ACCENT_CYAN

    # Metadata card
    add_card(s1, 0.9, 4.7, 11.5, 2.1, "Project Metadata & Verification Details", [
        "Candidate Name: Atharva Tripathi  |  Department: Computer Science & Engineering (AI & DS)",
        "Technology Stack: Python 3.11-3.14, Flask, Socket.IO, dlib (ResNet 128-D), OpenCV, MongoDB Atlas, Docker, Render",
        "Cloud Deployment: https://drishti-ai-attendance.onrender.com (Live HTTPS with active MongoDB Atlas cluster)",
        "Source Repository: https://github.com/Atharvagig/drishti-ai-attendance (Public Git repository with test suite)"
    ], title_color=ACCENT_EMERALD)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 2: Problem Statement & Motivation
    # ═════════════════════════════════════════════════════════════════════════
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "1. Problem Statement & Motivation", "02 / 10")
    add_card(s2, 0.8, 1.8, 5.7, 5.0, "Challenges in Traditional Campus Systems", [
        "Instructional Time Loss: Manual roll calls consume 10-15 minutes of every 60-minute lecture, wasting up to 25% of teaching time.",
        "Rampant Proxy Attendance: Paper rosters, RFID cards, and manual sign-ins allow 'buddy punching' with zero biometric accountability.",
        "Hygiene & Queue Bottlenecks: Physical fingerprint readers cause long classroom queues and surface transmission concerns.",
        "Delayed At-Risk Interventions: Low attendance (<75%) is detected only at semester end, preventing timely academic counseling.",
        "Data Silos & Record Tampering: Physical ledgers lack centralized synchronization, tamper-evident audit logs, and cloud backups."
    ], title_color=ACCENT_AMBER)
    add_card(s2, 6.8, 1.8, 5.7, 5.0, "The Drishti AI Solution", [
        "Non-Intrusive Computer Vision: Fast facial recognition verifies students in < 0.45s without physical contact.",
        "128-D Deep Metric Biometrics: ResNet-based facial embeddings ensure high accuracy across diverse lighting, expressions, and angles.",
        "Active Anti-Spoofing: MediaPipe Eye Aspect Ratio (EAR) and head kinematics prevent photo, screen replay, and paper mask fraud.",
        "Real-Time Classroom Broadcasting: WebSocket (Socket.IO) pushes check-in events to faculty terminals instantly.",
        "Enterprise Cloud Persistence: Production MongoDB Atlas cluster guarantees high availability, security, and institutional scaling."
    ], title_color=ACCENT_CYAN)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 3: System Architecture & Workflow
    # ═════════════════════════════════════════════════════════════════════════
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "2. System Architecture & End-to-End Workflow", "03 / 10")
    add_card(s3, 0.8, 1.8, 5.7, 5.0, "End-to-End Attendance Pipeline", [
        "1. Video Capture: DirectShow OpenCV (hardware camera) or WebRTC canvas streaming (/api/recognize_frame).",
        "2. Image Normalization: Automatic bounding, downscaling (fx=0.5, fy=0.5), and color-space conversion (BGR to RGB).",
        "3. Face Detection & Landmark Extraction: HOG detection finds face regions; MediaPipe extracts 468 landmark coordinates.",
        "4. 128-D Embedding Generation: Deep metric network maps face crop into invariant 128-dimensional Euclidean space.",
        "5. Distance Comparison: Compares candidate vector with cached student vectors using Euclidean metric (tolerance <= 0.45).",
        "6. Business Logic & Real-Time Sync: Enforces duplicate prevention, lateness rules, updates MongoDB Atlas, and emits Socket.IO event."
    ])
    add_card(s3, 6.8, 1.8, 5.7, 5.0, "Modular Tier Architecture", [
        "Presentation Tier: Glassmorphic Single Page Application (HTML5, Vanilla CSS tokens, ES6 JavaScript, Phosphor Icons).",
        "Application Tier: Python Flask v2.1 with Werkzeug ProxyFix, REST API endpoints, and eventlet-powered SocketIO engine.",
        "Biometric AI Engine: dlib C++ bindings, OpenCV, face_recognition ResNet models, and MediaPipe liveness detection.",
        "Database Tier: MongoDB Atlas cloud cluster with replica sets, SRV TLS encryption, and compound unique indexes.",
        "DevOps & Container Tier: Multi-stage Docker container deployed to Render Web Services with automated CI/CD pipeline."
    ], title_color=ACCENT_INDIGO)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 4: Biometric Face Recognition Pipeline
    # ═════════════════════════════════════════════════════════════════════════
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "3. Biometric Pipeline: Multi-Pose Enrollment & Recognition", "04 / 10")
    add_card(s4, 0.8, 1.8, 5.7, 5.0, "Multi-Angle Biometric Enrollment", [
        "5-Pose Enrollment Architecture: Captures Front, Left Profile (-30 deg), Right Profile (+30 deg), Pitch Up (+15 deg), and Pitch Down (-15 deg).",
        "Laplacian Quality Gate: Computes image sharpness via cv2.Laplacian(frame).var(); rejects blurry captures with score < 80.0.",
        "Adaptive Lighting Validation: Rejects overexposed (>235 mean) or underexposed (<40 mean) frames before computing embeddings.",
        "Dual Storage Strategy: 128-D vectors serialized into MongoDB Atlas binary fields; reference image saved for legacy audit compatibility.",
        "Cache Invalidation: Updates in-memory embedding cache immediately upon new enrollment without restarting the application."
    ])
    add_card(s4, 6.8, 1.8, 5.7, 5.0, "Deep Metric Learning & Euclidean Matching", [
        "ResNet-29 Backbone: Pre-trained deep metric network projects faces into a 128-dimensional hypersphere where same-person distance is minimized.",
        "Euclidean Distance Metric: d(u, v) = sqrt(sum((u_i - v_i)^2)). Distance below threshold indicates confirmed identity.",
        "Strict Match Tolerance: Configured at 0.45 (tighter than standard 0.60) to eliminate false positives in diverse campus cohorts.",
        "Confidence Score Normalization: Confidence = round((1.0 - (min_distance / 0.45)) * 100, 1) mapped to human-readable percentages.",
        "Multi-Face Batch Capability: Detects and classifies multiple faces simultaneously in group classroom camera feeds."
    ], title_color=ACCENT_EMERALD)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 5: Liveness Detection & Anti-Spoofing
    # ═════════════════════════════════════════════════════════════════════════
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_header(s5, "4. Anti-Spoofing: MediaPipe Liveness & Kinematics", "05 / 10")
    add_card(s5, 0.8, 1.8, 5.7, 5.0, "Eye Aspect Ratio (EAR) Blink Detection", [
        "468 Facial Mesh Landmarks: Uses MediaPipe FaceMesh to track micro-movements across eyelids and facial contours.",
        "EAR Mathematical Formulation: EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||) tracking vertical vs horizontal eye opening.",
        "Dynamic Blink Validation: Normal eye openness produces EAR ~0.30; a genuine blink drops EAR below 0.22 for 2-3 consecutive frames.",
        "Continuous Tracking State Machine: Maintains per-face tracker state: PROBING -> EYE_BLINK_DETECTED -> LIVENESS_PASSED.",
        "Zero False Acceptance on Photos: Static high-resolution 2D photographs and printed paper faces fail EAR dynamic verification."
    ])
    add_card(s5, 6.8, 1.8, 5.7, 5.0, "Kinematic Head Pose & Replay Defense", [
        "Perspective-n-Point (PnP) Pose Estimation: Estimates 3D head orientation (Yaw, Pitch, Roll) using 2D image landmarks mapped to 3D facial model.",
        "Replay Attack Detection: Digital screens (smartphones/tablets) exhibit planar flatness, lack of depth parallax, and unnatural glare.",
        "Micro-Motion Analysis: Requires subtle natural head movement before granting biometric approval in high-security kiosks.",
        "Automated Anomaly Logging: Unnatural spoof attempts trigger real-time anomaly alerts with snapshot evidence logged to MongoDB audit collection.",
        "Graceful Fallback: Headless/remote server mode supports browser client-side WebRTC frame upload without server GPU dependencies."
    ], title_color=ACCENT_CYAN)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 6: Attendance Rules Engine & Duplicate Prevention
    # ═════════════════════════════════════════════════════════════════════════
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "5. Attendance Engine: Session Rules & Anti-Duplicate Hierarchy", "06 / 10")
    add_card(s6, 0.8, 1.8, 5.7, 5.0, "3-Tier Duplicate Prevention Hierarchy", [
        "Tier 1 — In-Memory Cooldown: 10-second per-student cooldown tracker prevents rapid re-triggering while a student walks past camera.",
        "Tier 2 — Active Session Query: Checks MongoDB attendance collection for existing record matching (student_id, session_id).",
        "Tier 3 — Database Unique Index: Unique compound index on (student_id, session_id, date) enforces atomic constraint at the database engine level.",
        "Zero Double-Counts: Completely prevents race conditions and accidental duplicate entries even under concurrent network uploads.",
        "Informative Client Feedback: Subsequent detections return 'Already marked today' status without creating database write errors."
    ], title_color=ACCENT_EMERALD)
    add_card(s6, 6.8, 1.8, 5.7, 5.0, "Dynamic Session Logic & Reconciliation", [
        "Dynamic Lateness Thresholding: Check-in time evaluated against session start time. If CheckIn > StartTime + LateThreshold, status = 'Late'.",
        "Automated Absentee Reconciliation: Stopping a session (/api/sessions/<id>/stop) triggers bulk-marking of all enrolled students without check-in as 'Absent'.",
        "Session Locking: Once locked, sessions become immutable, preventing post-lecture tampering or fraudulent backdated attendance.",
        "Faculty Override with Audit Log: Faculty can manually adjust status with required justification, creating an immutable audit record.",
        "Real-Time Statistics Sync: Attendance rates, department averages, and student risk meters update automatically upon session close."
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 7: Security, Centralized RBAC & Session Management
    # ═════════════════════════════════════════════════════════════════════════
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "6. Security Architecture, RBAC & HTTPS Session Flow", "07 / 10")
    add_card(s7, 0.8, 1.8, 5.7, 5.0, "Role-Based Access Control (RBAC) Matrix", [
        "Super Admin (*): Complete administrative control over users, cameras, global settings, audit logs, and system configuration.",
        "Department Head: Scope-limited to specific department; can view departmental sessions, analytics, and student rosters.",
        "Faculty: Access to classroom session launcher, live tracking controls, student attendance logs, and report exports.",
        "Student: View-only access restricted strictly to their personal attendance history, percentage, and risk indicators.",
        "Context-Aware Content Negotiation: Centralized decorators redirect browser page requests to /login while returning 401/403 JSON to APIs."
    ], title_color=ACCENT_INDIGO)
    add_card(s7, 6.8, 1.8, 5.7, 5.0, "Enterprise Security & Session Hardening", [
        "Cryptographic Passwords: Salted bcrypt password hashing with production enforcement (default passwords strictly prohibited).",
        "Brute-Force Attack Defense: 5 consecutive failed login attempts trigger an automated 10-minute account lockout.",
        "CSRF Token Validation: State-changing API mutations require valid X-CSRFToken header matching server-issued session token.",
        "Reverse-Proxy Alignment: Werkzeug ProxyFix accurately interprets X-Forwarded-Proto: https behind cloud load balancers.",
        "Hardened Session Cookies: HttpOnly=True, SameSite=Lax, Path=/, and Secure=True on HTTPS connections prevent XSS and session hijacking."
    ], title_color=ACCENT_CYAN)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 8: Cloud Deployment & DevOps Engineering
    # ═════════════════════════════════════════════════════════════════════════
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_header(s8, "7. Cloud Deployment: Docker, Render & MongoDB Atlas", "08 / 10")
    add_card(s8, 0.8, 1.8, 5.7, 5.0, "Production Containerization (Render)", [
        "Multi-Stage Dockerfile: Uses clean Python 3.11/Linux x86_64 base with essential build tools and system dependencies (libgl1, libglib2.0).",
        "Build Memory Optimization: Solved 8GB RAM compilation exhaustion by integrating prebuilt dlib-bin wheel and limiting CMAKE_BUILD_PARALLEL_LEVEL=1.",
        "Production WSGI Server: Gunicorn with eventlet worker running on 0.0.0.0:$PORT supporting persistent WebSockets and high concurrency.",
        "Cloud Health Monitoring: Dedicated /api/health endpoint provides real-time reporting on database engine, dlib status, and cached embeddings.",
        "Zero Downtime Deploys: Automated Git-triggered builds from main branch with rolling health-check verification."
    ])
    add_card(s8, 6.8, 1.8, 5.7, 5.0, "MongoDB Atlas Cloud Architecture", [
        "Global Clustered Replica Set: Production database hosted on MongoDB Atlas with automatic multi-zone failover and 99.9% uptime SLA.",
        "End-to-End Encryption: TLSv1.3 encryption with certifi CA bundle validation ensuring secure cross-cloud transit.",
        "Dual-Engine Fallback Resilience: Intelligent database layer connects to MongoDB Atlas in cloud while preserving SQLite for offline campus labs.",
        "Optimized Schema & Indexing: Indexes on (student_id, session_id), (date), (username), and (created_at) ensure sub-10ms queries.",
        "Automated SQLite Migration: Built-in migration engine safely transfers students, face embeddings, attendance records, and audit logs."
    ], title_color=ACCENT_EMERALD)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 9: Comprehensive Testing & Verified Results
    # ═════════════════════════════════════════════════════════════════════════
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "8. Verification, Performance Benchmarks & Test Results", "09 / 10")
    add_card(s9, 0.8, 1.8, 5.7, 5.0, "Automated Test Suite (29/29 Passing)", [
        "Auth & Session Flow (test_auth_flow.py): 7/7 tests passed — unauthenticated page 302 redirects, API 401 JSON, CSRF, and session cookies.",
        "Security & RBAC (test_security_and_auth.py): 8/8 tests passed — brute force 5-attempt lockout, role isolation, and production password checks.",
        "MongoDB Atlas Integration (test_database_mongo.py): 8/8 tests passed — schema, CRUD, unique compound indexes, and migration consistency.",
        "Browser Camera Workflow (test_browser_camera_workflow.py): 4/4 tests passed — frame ingestion, dlib inference, duplicate checks.",
        "RBAC Scope Helper Tests (test_rbac.py): 2/2 tests passed — data-scope isolation for super admin, department heads, and students."
    ], title_color=ACCENT_EMERALD)
    add_card(s9, 6.8, 1.8, 5.7, 5.0, "Performance & Benchmark Metrics", [
        "Facial Detection & Match Latency: 1.88s (cold model load) | 0.35s - 0.45s (warm cached inference).",
        "Memory Footprint: < 450 MB RAM compute during active face recognition (well below cloud resource limits).",
        "Database Migration Accuracy: 100% record match across students (15/15), attendance (5/5), sessions (23/23), and audit logs (53/53).",
        "Duplicate Prevention Rate: 100% — Zero double-counts across continuous recognition stress tests.",
        "Live Production Health: Verified in production at https://drishti-ai-attendance.onrender.com/api/health (Status: Healthy)."
    ], title_color=ACCENT_CYAN)

    # ═════════════════════════════════════════════════════════════════════════
    # SLIDE 10: Conclusion, Real-World Impact & Future Scope
    # ═════════════════════════════════════════════════════════════════════════
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_header(s10, "9. Conclusion, Real-World Impact & Future Scope", "10 / 10")
    add_card(s10, 0.8, 1.8, 5.7, 5.0, "Project Outcomes & Institutional Impact", [
        "100% Operational Platform: Fully functional contactless AI attendance platform ready for college deployment.",
        "Elimination of Proxy Attendance: Deep metric 128-D biometrics and anti-spoofing ensure indisputable record authenticity.",
        "Recaptured Lecture Time: Automated camera recognition reclaims 10-15 minutes per lecture for active academic teaching.",
        "Early Academic Intervention: Automated risk flags immediately highlight students falling below 75% threshold.",
        "Institutional Cloud Governance: Centralized MongoDB Atlas storage, role-based dashboards, and automated Excel/CSV export."
    ], title_color=ACCENT_EMERALD)
    add_card(s10, 6.8, 1.8, 5.7, 5.0, "Future Research Scope & Q&A", [
        "Edge AI Hardware Deployment: Porting dlib inference pipeline to NVIDIA Jetson Orin Nano for distributed offline classroom terminals.",
        "Infrared / 3D Depth Sensing: Integrating structured-light / IR depth sensors for military-grade 3D facial anti-spoofing.",
        "Automated Multi-Channel Alerts: Instant WhatsApp and SMS push notifications to students and parents when attendance drops below 75%.",
        "Wide-Angle Multi-Face Attendance: Batch recognition of 30+ students simultaneously from wide-angle classroom security cameras.",
        "Project Status: Fully Deployed & Verified. Open for Viva Examination & Live Demonstration."
    ], title_color=ACCENT_CYAN)

    prs.save(PPTX_PATH_10)
    prs.save(PPTX_PATH_DEFAULT)
    print(f"[OK] Generated: {PPTX_PATH_10}")
    print(f"[OK] Updated default: {PPTX_PATH_DEFAULT}")
    return PPTX_PATH_10


if __name__ == '__main__':
    build_10_slide_presentation()
