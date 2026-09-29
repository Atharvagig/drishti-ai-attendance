# 👁️ Drishti AI — Smart Face Recognition Attendance System

> **B.Tech Minor Project Submission**
> **Drishti AI** is a real-time facial recognition attendance system featuring **dlib 128-D facial embeddings**, **MediaPipe liveness detection (anti-spoofing)**, **SQLite database & real-time WebSocket dashboard synchronization**, and a modern **glassmorphic UI**.

---

## ✨ Core Features

- **⚡ High-Precision Face Recognition**: Uses `face_recognition` (dlib 128-D encodings) with confidence scoring.
- **🛡️ Liveness Detection**: Uses MediaPipe Face Mesh to detect blinks (EAR) and head movement to prevent spoofing with photos.
- **📊 Real-Time Dashboard**: WebSocket (Socket.IO) integration for instant attendance updates and dynamic analytics charts.
- **🗄️ SQLite Database Persistence**: Robust local storage with RBAC (Role-Based Access Control) for Admin, Faculty, and Student panels.
- **📈 Advanced Analytics**: Heatmaps, attendance trends, and at-risk student monitoring.
- **📤 Export Engine**: Single-click PDF, CSV, and Excel exports with professional formatting.
- **🚫 Duplicate Prevention**: Intelligent session-based cooldown prevents duplicate attendance logs.

---

## 🚀 Installation & Setup (College Demo Guide)

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.10)
- Webcam (Internal or USB)
- Windows OS (recommended for demo)

### 2. Install Dependencies

```bash
# Clone the project directory (or extract ZIP)
cd drishti-ai-attendance

# Create and activate Virtual Environment (Optional but recommended)
python -m venv venv
.\venv\Scripts\activate

# Install required Python packages
pip install -r requirements.txt
```

### 3. Database Initialization & Demo Data

To demonstrate the dashboard analytics immediately without enrolling 30 students manually, you can generate synthetic demo data. 
**Note:** This uses actual SQL inserts and integrates perfectly with the analytics engine.

```bash
# Initialize DB and seed demo data
python backend/seed_demo.py
```

### 4. Running the Application

To start the application, use the main entry point:

```bash
python run.py
```

### 5. Accessing the System

Open your web browser and navigate to: **`http://127.0.0.1:5000`**

**Default Demo Accounts:**
- **Admin**: `admin` / `admin123` (Access to all panels, User Management)
- **Faculty**: `faculty` / `faculty123` (Manage sessions, view students)
- **Student**: `student` / `student123` (View own attendance only)

---

## 📸 Demo Procedure

1. **Login as Admin (`admin` / `admin123`)**.
2. Go to **Dashboard** to show real-time metrics and historical data (seeded via `seed_demo.py`).
3. Go to **Enroll Student**, type a sample name, and complete the 5-angle face enrollment.
4. Go to **Sessions** and create a new session for today.
5. Go to **Live Tracking** and click **Start Camera Tracking**.
6. Face the camera — observe Liveness Verification (blink/move head) and Identity Match.
7. Switch back to **Dashboard** to see the live feed update.
8. Go to **Analytics** and export the daily report as PDF/Excel.

---

## 👨‍💻 Developer
Developed for B.Tech Minor Project by **Atharva Tripathi**
