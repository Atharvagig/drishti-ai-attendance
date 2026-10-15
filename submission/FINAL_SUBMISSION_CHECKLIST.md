# 📋 Drishti AI — Final B.Tech Submission Checklist

Use this checklist on the day of your minor project submission and viva presentation.

---

## 💻 1. Local Application Setup & Execution
- [ ] Ensure **Python 3.14 virtual environment** (`venv314`) is present with native `dlib` wheel.
- [ ] Double-click [`start.bat`](file:///d:/project/start.bat) (or run `.\start.bat` from terminal).
- [ ] Confirm startup banner displays:
  ```text
  DRISHTI AI v2.0 — Smart Campus Attendance Platform
  URL : http://localhost:5000
  ```
- [ ] Open Chrome or Edge to **`http://localhost:5000`**.
- [ ] Check `/api/health` in browser: confirm status is `healthy`.

---

## 🔑 2. Account Credentials for Live Demo
- [ ] **Super Admin:** Username `admin` / Password `admin123` (Local demo default; rejected in production if `ADMIN_PASSWORD` is unset)
- [ ] **Faculty:** Username `faculty` / Password `faculty123` (Session and attendance management)
- [ ] **Student:** Username `student` / Password `student123` (Individual attendance history)

---

## 🗄️ 3. Database & MongoDB Atlas Migration
- [ ] Local SQLite backup verified at [`backend/data/attendance.db.bak`](file:///d:/project/backend/data/attendance.db.bak).
- [ ] Migration script tested: `python backend/migrate_to_mongo.py --mock` (15/15 tables verified).
- [ ] To use live Atlas: add your verified `MONGODB_URI` to [`.env`](file:///d:/project/.env) and run `python backend/migrate_to_mongo.py`.
- [ ] Production Fail-Fast verified: if MongoDB is active or in production and Atlas is unreachable, it raises `RuntimeError` (silent fallback to SQLite is blocked).
- [ ] Explicit local demo option: set `DB_BACKEND=sqlite` in `.env` for offline viva presentations.

---

## 📸 4. Live Camera & Face Recognition Demo
- [ ] Test webcam permissions in browser (Settings -> Privacy & Security -> Camera).
- [ ] Verify **Hardware Camera** button (DirectShow OpenCV local camera).
- [ ] Verify **Browser Webcam** button (WebRTC `/api/recognize_frame` mode for remote evaluation).
- [ ] Verify attendance confirmation card and instant WebSocket badge.
- [ ] Verify duplicate prevention rejection message (*'Already marked today'*).

---

## 📊 5. Presentation & Submission Deliverables
- [ ] **PowerPoint Presentation:** [`submission/Drishti_AI_BTech_Minor_Project_Presentation.pptx`](file:///d:/project/submission/Drishti_AI_BTech_Minor_Project_Presentation.pptx) (12 editable slides in dark slate tech theme).
- [ ] **Demonstration Video Script:** [`submission/DEMO_RECORDING_SCRIPT.md`](file:///d:/project/submission/DEMO_RECORDING_SCRIPT.md) (Timed 2m 45s script).
- [ ] **Viva Voce Guide:** [`submission/VIVA_PREPARATION_GUIDE.md`](file:///d:/project/submission/VIVA_PREPARATION_GUIDE.md) (20 in-depth technical Q&As).
- [ ] **QA Test Report:** [`submission/TEST_RESULTS_REPORT.md`](file:///d:/project/submission/TEST_RESULTS_REPORT.md) (18 verified checkpoints).
- [ ] **Deployment Guide:** [`submission/DEPLOYMENT_GUIDE_MONGODB_ATLAS.md`](file:///d:/project/submission/DEPLOYMENT_GUIDE_MONGODB_ATLAS.md).

---

## 🚀 6. Viva Voce Confidence Tips
1. When asked about **dlib**: Emphasize that it projects faces into a 128-dimensional Euclidean space where photos of the same person have small Euclidean distance ($L_2$ norm), matched via threshold `0.45`.
2. When asked about **MongoDB**: Highlight that BSON Binary format cleanly encapsulates 128-D NumPy embeddings, and compound unique indexes enforce duplicate prevention at the database constraint level.
3. When asked about **Hosting Limits**: Clearly explain the difference between Monolithic Serverless (which exhausts 1,000 monthly requests in 2 minutes of video) and the **Split Deployment** model (Netlify static frontend + Persistent container backend).
