# 🎬 Drishti AI — Video Demonstration & Presentation Script (2m 45s)

> **Project Title:** Drishti AI — Smart Face Recognition Attendance System  
> **Course:** B.Tech Minor Project Submission  
> **Target Duration:** 2 minutes 45 seconds  
> **Target Audience:** College External Examiner, Project Review Committee, and Viva Panel

---

## ⏱️ Timeline & Narration Breakdown

```
[0:00 - 0:15]  Intro & Problem Statement
[0:15 - 0:35]  Architecture & Tech Stack
[0:35 - 0:55]  Login & Dashboard Overview
[0:55 - 1:25]  Student Enrollment & Multi-Angle Capture
[1:25 - 1:50]  Live Face Recognition & Attendance Marking
[1:50 - 2:10]  Attendance History, Duplicate Check & Reports
[2:10 - 2:30]  MongoDB Atlas Cloud Persistence & Architecture
[2:30 - 2:45]  Conclusion & Future Scope
```

---

### [0:00 – 0:15] Section 1: Introduction & Problem Statement
* **Screen:** Title slide from PowerPoint or the Drishti AI Login Page (`http://localhost:5000/login`).
* **Visual Action:** Cursor rests on the Drishti AI branding.
* **Narration Script:**
  > *"Respected panel members, welcome to the demonstration of Drishti AI, an automated facial recognition attendance platform designed for smart educational campuses. Traditional manual roll-calls consume 10 to 15 minutes of every lecture and are prone to proxy attendance. Drishti AI replaces paper registers with sub-second, contactless biometric verification powered by deep metric learning."*

---

### [0:15 – 0:35] Section 2: Architecture & Technology Stack
* **Screen:** Architecture Diagram slide or transition into browser.
* **Visual Action:** Display system block diagram showing Input -> Vision -> Cloud Database -> WebSocket Dashboard.
* **Narration Script:**
  > *"Our system is architected around a high-performance Python 3.14 backend using Flask and WebSockets for real-time synchronization. The computer vision pipeline leverages dlib’s 128-dimensional deep metric embeddings with Euclidean distance matching, backed by MediaPipe liveness detection. For scalable persistence, our database layer is fully integrated with MongoDB Atlas cloud clusters with backward-compatible SQLite dual-engine support."*

---

### [0:35 – 0:55] Section 3: Authentication & Dashboard Overview
* **Screen:** Browser window at `http://localhost:5000/login`.
* **Visual Action:**
  1. Log in with `admin` / `admin123`.
  2. Navigate through the glassmorphic Dashboard.
  3. Point to Total Enrolled Students (15), Attendance Rate, Active Sessions, and 30-day Trend Charts.
* **Narration Script:**
  > *"Logging in as the System Administrator with role-based access control and bcrypt authentication, we reach the real-time glassmorphic dashboard. Here, faculty and department heads can immediately inspect campus attendance rates, identify at-risk students below the mandatory 75% threshold, and review dynamic analytics powered by Chart.js."*

---

### [0:55 – 1:25] Section 4: Student Enrollment & Multi-Angle Biometric Capture
* **Screen:** Click on **Enroll Student** tab.
* **Visual Action:**
  1. Show student enrollment form with fields for Name, Student ID, Department, Semester.
  2. Explain the 5-angle capture workflow (Front, Left, Right, Up, Down).
  3. Show the enrolled student roster with 128-D vector count.
* **Narration Script:**
  > *"Enrolling a new student takes seconds. The enrollment module captures five distinct facial angles to account for head tilt and lighting variations. Each valid frame is validated using a Laplacian variance sharpness filter before extracting 128-D descriptors. The embeddings are pickled and stored securely as BSON Binary data in MongoDB Atlas, updating our active recognition cache instantaneously."*

---

### [1:25 – 1:50] Section 5: Live Tracking & Attendance Recognition
* **Screen:** Click on **Live Tracking** tab.
* **Visual Action:**
  1. Select an active class session (e.g., 'Machine Learning Foundations').
  2. Click **Start Hardware Camera** (or **Browser Webcam**).
  3. Position face in front of camera — observe green bounding box, student identity match (e.g., 'Atharva', ID 11), high confidence score (> 70%), and instant WebSocket notification: *'Marked Present'*.
* **Narration Script:**
  > *"Now let's launch Live Tracking for today's active session. As the camera captures the stream, frames are optimized and compared against our loaded embeddings in under 500 milliseconds. When distance falls below our 0.45 threshold, the student is recognized, liveness is verified, and attendance is recorded with a live WebSocket broadcast to the dashboard."*

---

### [1:50 – 2:10] Section 6: Duplicate Prevention, Rules Engine & Reporting
* **Screen:** Keep camera running to show duplicate attempt; then switch to **Attendance** and **Analytics** tabs.
* **Visual Action:**
  1. Camera re-encounters the same student face: UI displays *'Already marked for this session'*.
  2. Switch to **Attendance Logs** table to show the freshly logged record with timestamp.
  3. Click **Export** and download the attendance sheet as Excel (.xlsx) / CSV.
* **Narration Script:**
  > *"Notice our three-tier duplicate prevention: when the same student remains in front of the camera, the system rejects double-marking with an 'Already marked' status enforced by both in-memory cooldown and MongoDB compound unique constraints. Furthermore, our session rules automatically flag late arrivals. All logs are exportable with one click into formatted Excel or CSV registers."*

---

### [2:10 – 2:30] Section 7: MongoDB Atlas Cloud Persistence & Deployment
* **Screen:** Show terminal / MongoDB Compass or Atlas web dashboard with collections: `students`, `attendance`, `face_embeddings`, `users`.
* **Visual Action:** Point out the 15 migrated student documents and compound indexes.
* **Narration Script:**
  > *"On the backend, our migration engine migrated all 15 relational tables to MongoDB Atlas with 100% verification and atomic sequence counters for backward compatibility. Our dual-engine architecture allows deploying the frontend to platforms like Netlify while running the persistent dlib vision engine on a containerized backend connected securely to Atlas."*

---

### [2:30 – 2:45] Section 8: Conclusion & Future Scope
* **Screen:** Return to PowerPoint presentation concluding slide.
* **Narration Script:**
  > *"In conclusion, Drishti AI delivers a reliable, production-ready, and contactless attendance management solution. Future work includes infrared 3D depth sensors and automated WhatsApp parent alerts. Thank you, and I look forward to your questions."*

---

## 🛠️ Recording Setup & Equipment Checklist

1. **Resolution:** 1920x1080 (1080p Full HD) at 30 or 60 FPS.
2. **Audio:** USB microphone or clear headset mic; test microphone level to avoid clipping.
3. **Lighting:** Front-facing warm/white light on face so dlib HOG detector gets clear facial landmarks.
4. **Browser Setup:** Chrome / Edge at 100% zoom with bookmarks bar hidden (F11 or clean window).
5. **Pre-Seeded Data:** Run `python backend/migrate_to_mongo.py --mock` or verify `attendance.db` has demo students loaded.
6. **Backup Plan if Live Webcam Stalls:**
   - Have the **Browser Webcam** button ready as fallback if DirectShow camera index is locked.
   - Alternatively, demonstrate the pre-recorded video clip or run the automated test suite `python tests/test_database_mongo.py`.
