# 👁️ Drishti AI — Smart Face Recognition Attendance System

> **B.Tech Minor Project Submission**
> **Drishti AI** is an enterprise-grade real-time facial recognition attendance platform featuring **dlib 128-D facial embeddings**, **MediaPipe anti-spoofing**, **MongoDB Atlas cloud clustering (with SQLite dual-engine fallback)**, **WebSocket live dashboard synchronization**, and a modern **glassmorphic UI**.

---

## ✨ Core Features

- **⚡ High-Precision Face Recognition**: Uses `face_recognition` (dlib 128-D ResNet metric learning) with configurable tolerance (`0.45`).
- **🛡️ Liveness Detection**: MediaPipe Face Mesh analyzes Eye Aspect Ratio (EAR) and head kinematics to prevent photo/screen spoofing.
- **☁️ MongoDB Atlas Cloud Persistence**: Migrated from local SQLite to MongoDB Atlas with connection pooling, document models, and backward-compatible integer sequence counters.
- **🔄 Dual-Engine Resilience**: Seamlessly detects `MONGODB_URI` for cloud operation and auto-falls back to SQLite offline.
- **📊 Real-Time Dashboard**: WebSocket (Socket.IO) integration for instant attendance updates and dynamic analytics charts.
- **🚫 3-Tier Duplicate Prevention**: In-memory cooldown + session query + database-level compound unique constraints.
- **🔐 RBAC Security**: Role-Based Access Control for Super Admin, Faculty, and Student portals with bcrypt salted hashes and CSRF protection.
- **🌐 Dual-Mode Camera Tracking**: Local hardware DirectShow camera capture + Browser WebRTC frame recognition (`/api/recognize_frame`).
- **📤 Export Engine**: Single-click PDF, CSV, and Excel exports with professional formatting.

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

### 4. Running the Application (One-Click or CLI)

**Option A (Recommended on Windows):**
Simply double-click `start.bat` in the project root folder. It automatically activates the Python 3.14 virtual environment with native `dlib` and starts the server.

**Option B (CLI):**
```bash
.\venv314\Scripts\activate
python run.py
```

### 5. MongoDB Atlas Migration (Cloud Setup)

To migrate from local SQLite to MongoDB Atlas:
```bash
# Validate schema and counts (dry run)
python backend/migrate_to_mongo.py --dry-run

# Run migration to MongoDB Atlas
python backend/migrate_to_mongo.py --uri "mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
```

### 6. Accessing the System

Open your web browser and navigate to: **`http://127.0.0.1:5000`**

**Default Demo Accounts:**
- **Super Admin**: `admin` / `admin123` (Access to all panels, User Management)
- **Faculty**: `faculty` / `faculty123` (Manage sessions, view students, manual overrides)
- **Student**: `student` / `student123` (View personal attendance history and monthly heatmap)

---

## 📁 College Submission Package (`submission/`)

All materials required for academic evaluation and viva voce are prepared in the `submission/` folder:
- **`submission/Drishti_AI_BTech_Minor_Project_Presentation.pptx`**: 12-slide editable PowerPoint presentation in dark slate tech theme.
- **`submission/DEMO_RECORDING_SCRIPT.md`**: Complete timed 2m 45s demonstration video script.
- **`submission/VIVA_PREPARATION_GUIDE.md`**: 20 comprehensive technical questions and answers.
- **`submission/TEST_RESULTS_REPORT.md`**: 18-point QA verification report with benchmark metrics.
- **`submission/DEPLOYMENT_GUIDE_MONGODB_ATLAS.md`**: Step-by-step Atlas setup and split-deployment guide.
- **`submission/FINAL_SUBMISSION_CHECKLIST.md`**: Pre-viva preparation checklist.

---

## 👨‍💻 Developer
Developed for B.Tech Minor Project by **Atharva Tripathi**
