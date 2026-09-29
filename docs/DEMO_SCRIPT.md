# Drishti AI — Final Demo Script

**Estimated Duration:** 5–7 minutes

## 0:00–0:30: Problem Statement
"Hello, my name is Atharva Tripathi, and I am presenting my B.Tech Minor Project: **Drishti AI**. Traditional college attendance systems rely on roll calls or RFID cards, which are prone to proxy attendance, time-consuming, and hard to manage. Drishti AI solves this by introducing a highly precise, touchless facial recognition attendance system equipped with anti-spoofing liveness detection and real-time dashboard analytics."

## 0:30–1:00: Architecture
"The system is built on a Flask python backend. We utilize `dlib` 128-D facial embeddings for high-accuracy recognition and `MediaPipe` Face Mesh to ensure liveness—verifying that a physical human is present, not a photograph. Data is persisted in a local SQLite database, and we use WebSocket (`Socket.IO`) to push updates instantly to our glassmorphic frontend."

## 1:00–2:00: Faculty Login + Session
*(Action: Open browser to `http://127.0.0.1:5000`)*
"We implement a strict Role-Based Access Control (RBAC) system. I'll log in as a Faculty member using the credentials `faculty` / `faculty123`. The Faculty dashboard allows us to create isolated attendance sessions. I will navigate to the 'Sessions' tab and start a new class session for today. Notice that the UI instantly confirms the active session without page reloads."

## 2:00–3:30: Face Recognition + Liveness + Attendance
*(Action: Navigate to 'Live Tracking' and click 'Start Camera Tracking')*
"This is the core engine. When a student steps in front of the camera, the system first detects the face. Next, it analyzes the Eye Aspect Ratio (EAR) and head movement to verify liveness. Only upon passing the liveness check does it calculate the Euclidean distance against our stored 128-D embeddings. You can see the visual confirmation card popping up here: 'IDENTITY VERIFIED' and 'LIVENESS VERIFIED'. If someone tries to scan twice within the cooldown period, it explicitly blocks it, stating 'ATTENDANCE ALREADY MARKED', preventing duplicates in the database."

## 3:30–4:30: Live Dashboard + Analytics
*(Action: Switch to 'Dashboard' or log in as Admin)*
"Because of our WebSocket integration, these attendance events are pushed directly to the dashboard. Let's look at the Admin analytics. Here we have a rich UI displaying Present/Late ratios, department distributions, and at-risk student monitoring. All these metrics are aggregated live from raw SQLite data—not hardcoded fakes."

## 4:30–5:15: Student Attendance View
*(Action: Log out, and log in as `student` / `student123`)*
"Transparency is key. When a student logs in, they are restricted strictly to their own data. They can view a personal heatmap of their attendance trends, giving them direct feedback on their current standing without exposing the entire campus directory."

## 5:15–6:00: Excel/CSV/PDF Report
*(Action: Log back into Faculty or Admin, navigate to 'Analytics' or 'Dashboard', click Export)*
"Finally, for college administrative requirements, the system supports single-click exports. I'll generate a PDF report now. The system utilizes `fpdf2` and `openpyxl` to produce styled, professional campus reports containing the Date, Time, Identity Confidence, and Liveness Status."

## 6:00–7:00: Security + Future Scope
"Security is integrated at multiple levels: passwords are hashed via `bcrypt`, API endpoints enforce `@permission_required` decorators, and no hardcoded credentials are included in the source code. For future scope, we plan to implement GPU/CUDA acceleration for the dlib embedding generator to handle higher frame rates, and potentially integrate a mobile application for manual fallback marking. Thank you."
