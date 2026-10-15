# 🚀 Drishti AI — MongoDB Atlas Migration & Deployment Guide

This guide walks you through setting up a free **MongoDB Atlas** cloud cluster, migrating your existing SQLite attendance data, and deploying the application under the split-architecture model.

---

## 📋 Table of Contents
1. [Creating a Free MongoDB Atlas Cluster](#1-creating-a-free-mongodb-atlas-cluster)
2. [Configuring Network Access & Database User](#2-configuring-network-access--database-user)
3. [Configuring Environment Variables](#3-configuring-environment-variables)
4. [Running the Database Migration Engine](#4-running-the-database-migration-engine)
5. [Verifying the Migration in Atlas](#5-verifying-the-migration-in-atlas)
6. [Hosting & Split-Deployment Architecture](#6-hosting--split-deployment-architecture)
7. [Rollback Procedure](#7-rollback-procedure)

---

## 1. Creating a Free MongoDB Atlas Cluster

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and sign in (or create a free account).
2. Click **Create Deployment** (or **Build a Database**).
3. Select the **M0 Free Tier** (512 MB storage, shared RAM, free forever).
4. Choose a cloud provider and region closest to your college/location (e.g., AWS / Mumbai `ap-south-1`).
5. Enter a cluster name (e.g., `Cluster0`) and click **Create Deployment**.

---

## 2. Configuring Network Access & Database User

### A. Create a Database User
1. In the Atlas left sidebar, navigate to **Security** -> **Database Access**.
2. Click **Add New Database User**.
3. Authentication Method: **Password**.
4. Set a Username (e.g., `drishti_admin`) and a secure Password (e.g., `SmartCampus2026!`).
5. Database User Privileges: Select **Read and write to any database** (or built-in `readWrite`).
6. Click **Add User**.

### B. Configure Network Access (IP Whitelist)
1. In the Atlas left sidebar, navigate to **Security** -> **Network Access**.
2. Click **Add IP Address**.
3. For deployment flexibility across mobile networks, college Wi-Fi, and cloud hosts, select **Allow Access from Anywhere** (`0.0.0.0/0`).
4. Click **Confirm**. (Takes ~1 minute to activate).

### C. Obtain the Connection String
1. In the Atlas left sidebar, click **Database** -> **Connect**.
2. Choose **Drivers** (Python / PyMongo).
3. Copy the SRV connection URI:
   ```text
   mongodb+srv://drishti_admin:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
4. Replace `<password>` with your actual database user password.

---

## 3. Configuring Environment Variables

Open or create your `.env` file in the project root (`d:\project\.env`):

```bash
# Database Engine Selection
DB_BACKEND=mongodb
MONGODB_URI=mongodb+srv://drishti_admin:SmartCampus2026!@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=drishti_attendance

# Local SQLite fallback path (used if MONGODB_URI is absent or network unreachable)
DB_PATH=data/attendance.db

# Flask Server Settings
FLASK_ENV=production
FLASK_PORT=5000
SECRET_KEY=drishti-ai-secure-v2-production-key-9921
SESSION_TIMEOUT_MINUTES=60

# Camera & Recognition Settings
CAMERA_INDEX=0
COOLDOWN_SECONDS=10
MATCH_TOLERANCE=0.45
```

---

## 4. Running the Database Migration Engine

To migrate all 15 relational tables, student records, and binary face embeddings from your local `attendance.db` to MongoDB Atlas:

```bash
# Activate your Python virtual environment (Python 3.14 with dlib)
.\venv314\Scripts\activate

# Step 1: Dry run validation (checks schema & counts without writing)
python backend/migrate_to_mongo.py --dry-run

# Step 2: Live migration to Atlas
python backend/migrate_to_mongo.py --uri "mongodb+srv://drishti_admin:SmartCampus2026!@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"
```

### Expected Output:
```text
======================================================================
  MIGRATION VERIFICATION AUDIT REPORT
======================================================================
TABLE / COLLECTION        | SQLITE   | MONGODB  | STATUS
----------------------------------------------------------------------
students                  | 15       | 15       | VERIFIED
attendance                | 5        | 5        | VERIFIED
departments               | 6        | 6        | VERIFIED
subjects                  | 5        | 5        | VERIFIED
classrooms                | 5        | 5        | VERIFIED
cameras                   | 3        | 3        | VERIFIED
face_embeddings           | 15       | 15       | VERIFIED
attendance_sessions       | 23       | 23       | VERIFIED
audit_logs                | 53       | 53       | VERIFIED
users                     | 4        | 4        | VERIFIED
======================================================================
```

---

## 5. Verifying the Migration in Atlas

1. Open MongoDB Atlas web console and navigate to **Database** -> **Browse Collections**.
2. Select database `drishti_attendance`.
3. Verify that the following collections appear with documents:
   - `students` (15 documents)
   - `attendance` (5 documents)
   - `face_embeddings` (15 documents with Binary blobs)
   - `attendance_sessions` (23 documents)
   - `users` (4 documents)
   - `counters` (sequence tracking documents)
4. Start the application locally with MongoDB active:
   ```bash
   python run.py
   ```
5. Check terminal output:
   ```text
   [Database Layer] Connected to MongoDB Atlas. Active Engine: MONGODB
   ```
6. Open your browser to `http://localhost:5000/api/health` to confirm:
   ```json
   {
     "database": {
       "active_backend": "mongodb",
       "is_mongo_active": true
     },
     "status": "healthy"
   }
   ```

---

## 6. Hosting & Split-Deployment Architecture

### Analysis of the Hosting Constraints:
- **Compute:** 1,024 MB RAM
- **Execution Limit:** 10 seconds
- **Monthly API Traffic:** 1,000 requests/month

### Why Split Deployment (Option B) is Required:
- Continuous video streaming (15–30 FPS) consumes 1,000 requests in less than 2 minutes.
- Serverless functions kill connections after 10 seconds, terminating persistent WebSockets.
- C++ compiled libraries (`dlib`, `OpenCV`) are heavy for standard serverless zip packaging.

### Split Deployment Architecture:
```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│     CLIENT BROWSER / WEBCAM     │       │       MONGODB ATLAS CLOUD       │
│  • WebRTC Camera Capture        │       │  • 15 Relational Collections    │
│  • Glassmorphic SPA Frontend    │       │  • Compound Unique Indexes      │
│  • Chart.js Analytics           │       │  • High-Availability Replica Set│
└────────────────┬────────────────┘       └────────────────▲────────────────┘
                 │                                         │
        HTTP / WebSockets                                 TLS
                 │                                         │
┌────────────────▼─────────────────────────────────────────┴────────────────┐
│                   PERSISTENT BACKEND (DOCKER / RENDER / VM)               │
│  • Python 3.14 + Flask + Flask-SocketIO                                  │
│  • dlib 128-D Facial Recognition Engine (< 500ms cached inference)        │
│  • Throttled Frame Upload Endpoint: POST /api/recognize_frame             │
└───────────────────────────────────────────────────────────────────────────┘
```

1. **Frontend Hosting (Netlify / Vercel):**
   - Push repository to GitHub.
   - Connect repository to Netlify with build directory `frontend/`.
   - Automatic Git push deployment, free SSL certificate, and custom subdomain.
2. **Backend Hosting (Render / Railway / AWS EC2 / Campus Server):**
   - Deploy as a persistent Docker container or Python service.
   - Set environment variables: `MONGODB_URI`, `SECRET_KEY`, `FLASK_PORT=5000`.
   - Handles dlib native compute and WebSocket streams.

---

## 7. Rollback Procedure

If MongoDB Atlas is temporarily unreachable or internet is disconnected during college presentation:

1. **Option A (Environment Switch):**
   In `.env`, comment out or delete `MONGODB_URI`, or set:
   ```bash
   DB_BACKEND=sqlite
   ```
2. **Option B (Zero-Config Automatic Fallback):**
   If MongoDB Atlas connection fails or times out, the database layer automatically logs:
   ```text
   [Database Layer] MongoDB Atlas connection failed. Active Engine: SQLITE
   ```
   and immediately runs off the local `data/attendance.db` without crashing!
3. **Immutable SQLite Backup:**
   An untouched backup exists at `backend/data/attendance.db.bak` to ensure your original records can never be lost.
