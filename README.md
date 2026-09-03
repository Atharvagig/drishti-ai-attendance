# 👁️ Drishti AI — Smart Attendance & Biometric Recognition System

> **Drishti AI** is a production-grade, real-time facial recognition attendance system featuring **dlib 128-D facial embeddings**, **Laplacian sharpness face selection**, **dual SQLite database & real-time Excel (.xlsx) synchronization**, and a modern **glassmorphic Web Dashboard**.

---

## ✨ Features

- **⚡ High-Precision Face Recognition**: Uses `face_recognition` (dlib 128-D encodings) with confidence scoring.
- **📸 Smart Sharpness Enrollment**: Automatically selects the crispest photo frame using Laplacian variance during enrollment.
- **📊 Real-Time Excel (.xlsx) Synchronization**: Appends attendance logs dynamically to formatted Excel spreadsheets (`Attendance_Master.xlsx` and `Attendance_YYYY-MM-DD.xlsx`).
- **🎨 openpyxl Professional Formatting**: Styled header rows, dark slate fills, status badges, column width auto-fitting, and timestamp formatting.
- **🗄️ SQLite Database Persistence**: Robust storage for student directory profiles and log history with complete REST API support.
- **📧 Automated Email Alerts**: Asynchronously dispatches SMTP email alerts upon successful check-in.
- **🛡️ Intelligent Cooldown System**: Prevents duplicate attendance logging within a 30-second window.
- **💻 Modern Glassmorphic Web Dashboard**: Real-time analytics cards, student directory management, date range filters, client-side table search, and single-click Excel export.

---

## 🏗️ System Architecture

```
Drishti AI Application Architecture
│
├── 🌐 Web UI (Flask Server)
│   ├── /                 → Dashboard UI (SPA)
│   ├── /api/stats        → Analytics Metrics & Log Data
│   ├── /api/students     → Student Directory Management
│   ├── /api/attendance   → Attendance Log Queries
│   ├── /api/export       → Styled Excel Download (.xlsx)
│   └── /api/register     → Student Enrollment Dispatcher
│
├── ⚙️ Core Engines
│   ├── capture_faces.py  → Camera enrollment & Laplacian sharpness scorer
│   ├── recognize_faces.py→ Live webcam tracking & dlib 128-D matcher
│   ├── database.py       → SQLite ORM context manager (attendance.db)
│   └── excel_manager.py  → Real-time openpyxl spreadsheet formatting
│
└── 📁 Data Persistence
    ├── attendance.db           → SQLite Database File
    ├── Attendance_Master.xlsx  → Historical Master Spreadsheet
    ├── Attendance_YYYY-MM-DD.xlsx → Daily Attendance Sheets
    └── known_faces/            → Reference Face Images (Name_ID.jpg)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Webcam / Integrated Camera
- Virtual Environment (recommended)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/your-username/drishti-ai.git
cd drishti-ai

# Activate Virtual Environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the root directory (refer to `.env.example`):

```env
FLASK_ENV=development
FLASK_PORT=5000

# Optional SMTP Email Alerts
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECEIVER_EMAIL=admin_email@gmail.com
```

### 4. Running the Web Application

```bash
python app_flask.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 📡 REST API Documentation

| Endpoint | Method | Description |
|---|---|---|
| `GET /` | `GET` | Renders Web Dashboard |
| `GET /api/stats` | `GET` | Returns summary metrics & today's logs |
| `GET /api/students` | `GET` | Lists all registered students |
| `POST /api/students/delete` | `POST` | Removes student record & reference photo |
| `GET /api/attendance` | `GET` | Queries attendance logs (`?date=YYYY-MM-DD`) |
| `DELETE /api/attendance/<id>` | `DELETE` | Deletes attendance record |
| `GET /api/export` | `GET` | Downloads styled `.xlsx` Excel sheet |
| `POST /api/register` | `POST` | Enrolls student & launches capture tool |
| `POST /api/start_attendance` | `POST` | Launches live camera tracking engine |

---

## 👨‍💻 Developer & License

Developed with ❤️ by **Atharva Tripathi**  
Licensed under the **MIT License**.
