# 🎓 Drishti AI — Comprehensive Viva Voce Preparation Guide (20 Questions & Answers)

> **Project:** Drishti AI — Smart Face Recognition Attendance System  
> **Course:** B.Tech Minor Project Viva Voce  
> **Prepared For:** Academic Review Panel & External Viva Examiner

---

### Q1. What core problem does Drishti AI solve in an educational institution?
**Answer:**
Traditional manual attendance requires 10–15 minutes of every 60-minute lecture, leading to instructional time loss, transcription errors, and rampant proxy attendance through signed rosters or shared RFID badges. Drishti AI automates this workflow using contactless facial recognition, completing student verification in under 2 seconds while logging attendance to a centralized, audited cloud database.

---

### Q2. Why is facial recognition preferred over biometric fingerprints or RFID cards?
**Answer:**
1. **Contactless Hygiene:** Fingerprint sensors degrade through grease, smudges, and physical contact, causing queues and hygiene concerns.
2. **Proxy Elimination:** RFID smartcards are detached from biological identity and are easily passed to peers. Facial biometrics inherently verifies the physical presence of the individual.
3. **High Throughput:** Faces can be acquired dynamically as students enter the classroom without requiring them to pause and tap a sensor.

---

### Q3. What is dlib, and what role does it play in Drishti AI?
**Answer:**
`dlib` is a modern C++ machine learning toolkit. In our project, it provides two essential components:
1. **Face Localization:** Uses a Histogram of Oriented Gradients (HOG) combined with a linear SVM to find face bounding boxes.
2. **Deep Metric Feature Extraction:** Uses a pre-trained ResNet-34 architecture (trained on 3 million faces) to project each face into a 128-dimensional Euclidean embedding space where photos of the same person are clustered closely together.

---

### Q4. How does Face Detection differ from Face Recognition?
**Answer:**
- **Face Detection** is the binary classification and localization task: *"Is there a face in this image, and where is it located?"* In Drishti AI, this is handled by `dlib.get_frontal_face_detector()` returning rectangular bounding coordinates `(top, right, bottom, left)`.
- **Face Recognition** is the identification task: *"Whose face is this?"* In Drishti AI, this takes the cropped face, computes its 128-D vector, and calculates the Euclidean distance against stored enrollment vectors.

---

### Q5. How are face descriptors generated, stored, and compared in your implementation?
**Answer:**
1. **Generation:** `face_recognition.face_encodings(rgb_frame, face_locations)` normalizes 68 facial landmarks (eyes, nose, mouth) via affine transformation, feeds the 150x150 face chip through the dlib deep neural network, and outputs a 128-element float64 NumPy array.
2. **Storage:** In SQLite, vectors are pickled and stored in `face_embeddings.embedding_blob`. In MongoDB Atlas, vectors are stored as BSON `Binary` documents along with `student_id`, `quality_score`, and `angle`.
3. **Comparison:** When a frame arrives, `face_recognition.face_distance(known_embeddings, candidate_vector)` computes the Euclidean distance ($L_2$ norm):
   $$d = \sqrt{\sum_{i=1}^{128} (x_i - y_i)^2}$$
   The minimum distance is matched against `MATCH_TOLERANCE`.

---

### Q6. How was the recognition threshold (`MATCH_TOLERANCE = 0.45`) selected?
**Answer:**
The standard dlib default tolerance is 0.60 (which yields ~99.38% benchmark accuracy on Labeled Faces in the Wild). However, in a smart classroom setting with potential lookalikes, 0.60 allows occasional false positives. Through empirical testing with student face clusters, we tightened `MATCH_TOLERANCE` to `0.45`. This lower threshold drastically reduces False Acceptance Rate (FAR) while multi-angle enrollment (5 poses) ensures False Rejection Rate (FRR) remains minimal.

---

### Q7. Explain the complete attendance processing workflow from video frame to database log.
**Answer:**
1. **Acquisition:** Frame acquired via OpenCV `VideoCapture` or HTTP POST to `/api/recognize_frame`.
2. **Preprocessing:** Downscaled by 50% (`fx=0.5, fy=0.5`) to accelerate HOG detection.
3. **Localization & Extraction:** Bounding box found, normalized landmarks extracted, and 128-D vector computed.
4. **Vector Matching:** Evaluated against in-memory embedding cache using vectorized Euclidean distance.
5. **Rules Engine:**
   - Checks in-memory 10-second student cooldown.
   - Compares current time against session start time + `late_threshold_minutes` (classifies as `Present` or `Late`).
   - Checks MongoDB composite unique index `(student_id, session_id)` for duplicate prevention.
6. **Persistence & Broadcast:** Inserts attendance document and emits a `socketio.emit('attendance_marked', ...)` event to update all connected dashboards in real time.

---

### Q8. How does MongoDB Atlas differ from your previous SQLite database?
**Answer:**
| Feature | SQLite (Previous) | MongoDB Atlas (Current) |
| :--- | :--- | :--- |
| **Architecture** | Single-file embedded C-library (`attendance.db`) | Distributed cloud document database cluster |
| **Concurrency** | File-level/WAL lock; limited write scalability | Document-level concurrency control with connection pooling |
| **Availability** | Local to single machine; fails in cloud split | Globally accessible over TLS (`mongodb+srv://`) with high availability |
| **Schema Flexibility** | Rigid relational columns requiring table alters | Dynamic BSON documents supporting nested metrics and logs |
| **Data Replication** | Manual file copies | Automated multi-node replica set with automated backups |

---

### Q9. Why did you choose MongoDB Atlas instead of MySQL or PostgreSQL?
**Answer:**
1. **BSON Native Binary Storage:** Face embeddings (128 float64 numbers) and image metadata are naturally serialized into BSON Binary documents without complex BLOB mapping.
2. **JSON-Native Web Tier:** Flask and our JavaScript frontend operate natively on JSON data structures, removing Object-Relational Impedance Mismatch.
3. **Cloud-Managed Service:** Atlas provides automated clustering, TLS encryption, IP access whitelisting, and auto-scaling without dedicated database server maintenance.
4. **Composite & Partial Indexes:** Atlas natively supports partial filter unique indexes (e.g., unique `(student_id, session_id)` only when `session_id` is non-null).

---

### Q10. How is duplicate attendance prevented in your system?
**Answer:**
Duplicate check is enforced across three distinct architectural layers:
1. **Layer 1 (Memory Cooldown):** In `face_engine.py`, `_check_cooldown(student_id)` rejects repeated marks within 10 seconds to prevent event spamming while a student is in front of the lens.
2. **Layer 2 (Application Query):** In `database.py` / `database_mongo.py`, an explicit query checks if an attendance record exists for the given `student_id` in the current `session_id`.
3. **Layer 3 (Database Constraint):** A compound unique index `[("student_id", 1), ("session_id", 1)]` is enforced at the database engine level. Even if two concurrent requests race past the application check, MongoDB rejects the second insert with `DuplicateKeyError`.

---

### Q11. How is sensitive biometric data protected in Drishti AI?
**Answer:**
1. **No Raw Image Dependency:** Once 128-D vectors are generated during enrollment, the raw face images do not need to be retained for recognition. 
2. **Non-Reversible Embeddings:** Mathematical feature vectors cannot be reverse-engineered back into a recognizable human photo.
3. **Database Access Control:** MongoDB Atlas requires SCRAM-SHA-256 authentication over TLS 1.3 with IP access whitelisting.
4. **Credential Hashing:** All user passwords are salted and hashed using `bcrypt` (work factor 12); raw passwords are never stored or exposed in API responses.

---

### Q12. What is liveness detection, and what are its real-world limitations?
**Answer:**
Liveness detection distinguishes between a live biological face and a spoofing presentation (such as a 2D photograph, printed paper mask, or digital video playback on a smartphone screen).
In Drishti AI, `liveness_detector.py` uses MediaPipe's Face Mesh landmarks to compute:
- **Eye Aspect Ratio (EAR):** Detects involuntary blinking:
  $$\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \|p_1 - p_4\|}$$
- **Kinematic Head Pose:** Evaluates 3D nose-tip displacement across frames.
**Limitations:** 2D RGB cameras cannot measure true physical depth. A high-resolution video replay on a tablet can simulate blinks and head motion. High-security commercial applications require infrared (IR) illumination or structured 3D depth cameras (e.g., Intel RealSense).

---

### Q13. Why did you choose a Split Deployment architecture over a monolithic serverless host?
**Answer:**
When analyzing the hosting constraints (1,024 MB RAM, 10-second execution duration, and 1,000 API requests/month):
1. **Request Quota:** A continuous camera feed (15–30 FPS) would burn through 1,000 monthly requests in under 2 minutes.
2. **Execution Duration:** Serverless functions force termination at 10 seconds, making persistent WebSocket connections (`Flask-SocketIO`) impossible.
3. **Native C++ Dependencies:** dlib requires compiled C++ extensions (`_dlib_pybind11`), which are difficult to package within standard serverless limits.
Therefore, the **Split Deployment** model is optimal:
- **Frontend:** Hosted on Netlify / static cloud host with custom subdomain, SSL, and CDN caching.
- **Backend:** Hosted on a dedicated Python container / persistent server with native dlib support.
- **Database:** Hosted on MongoDB Atlas cloud cluster.

---

### Q14. How does your system manage memory and compute constraints?
**Answer:**
1. **Singleton Model Loading:** Models are loaded once into RAM at process startup (`load_embedding_cache`), avoiding repeated multi-hundred-megabyte disk loads per request.
2. **Frame Downscaling:** Input frames are capped at max 800px dimension and downscaled by 50% for HOG detection, keeping memory consumption < 450 MB.
3. **No Frame Leakage:** Frame buffers are processed in-place and garbage collected immediately; unbounded image queues are avoided.
4. **Connection Pooling:** PyMongo reuses connection pools (`maxPoolSize=50, minPoolSize=5`) instead of opening new TLS handshakes per query.

---

### Q15. What happens when a student checks in after the class has started?
**Answer:**
Every session created in Drishti AI has a `start_time` and a configurable `late_threshold_minutes` (default: 10 minutes). When a student is recognized, the system calculates:
$$\text{Cutoff Time} = \text{Session Start Time} + \text{Late Threshold Minutes}$$
If the current timestamp exceeds the cutoff, their attendance record is stored with `status = 'Late'`. Both Present and Late counts are surfaced dynamically on the faculty dashboard.

---

### Q16. How does the system handle students who do not attend the session?
**Answer:**
When faculty or admin terminates an active session via `/api/sessions/<session_id>/stop`, the backend invokes `mark_absent_for_session(session_id)`. This queries all enrolled active students in the department, compares them against the session's recorded attendance, and automatically inserts `status = 'Absent'` records for all missing students.

---

### Q17. How is Role-Based Access Control (RBAC) structured in the application?
**Answer:**
Drishti AI defines 5 distinct roles in `rbac.py`:
1. `super_admin`: Full system control (User management, system configuration, audit logs).
2. `department_head`: Departmental analytics, curriculum management, faculty oversight.
3. `faculty`: Session creation, live tracking control, student attendance overrides.
4. `attendance_operator`: Camera terminal monitoring and check-in operations.
5. `student`: Restricted to viewing personal attendance history and individual monthly heatmap.
Every route is guarded by `@permission_required('<perm_key>')` or `@login_required`.

---

### Q18. How did you verify the database migration from SQLite to MongoDB?
**Answer:**
We built an automated migration and verification script (`backend/migrate_to_mongo.py`). The script:
1. Iterates through all 15 SQLite tables and extracts rows.
2. Converts binary blobs into BSON `Binary` types and maps primary keys to integer sequences in `counters`.
3. Performs upsert operations into MongoDB Atlas.
4. Validates source count vs. destination count for all tables (e.g., 15/15 students, 5/5 attendance, 23/23 sessions, 53/53 audit logs).
5. Deserializes sample embeddings in MongoDB to verify that numpy float64 arrays remain intact.

---

### Q19. What testing methodology was applied to ensure production readiness?
**Answer:**
We implemented an 18-point verification test suite covering:
1. Database schema initialization, indexes, and atomic sequence generation.
2. In-memory `mongomock` integration tests (8/8 unit tests passing).
3. Real face recognition on actual enrolled faces (`atharva_11.jpg`) yielding positive match in 1.88s.
4. False detection rejection on blank/non-face frames returning a clean 200 response.
5. Duplicate attendance rejection on second identical frame.
6. CSRF token validation and brute-force lockout (5 failed logins locks account for 10 minutes).
7. Single-frame REST endpoint (`/api/recognize_frame`) and health check (`/api/health`).

---

### Q20. What are the key limitations of the current system and realistic future enhancements?
**Answer:**
- **Current Limitations:**
  1. Relies on standard 2D webcams; cannot perform hardware-level infrared depth mapping.
  2. MediaPipe FaceMesh in Python 3.14 requires updating to new Tasks API for full mesh landmarks.
  3. Single-threaded recognition loop processes one primary face per bounding box sequentially.
- **Future Enhancements:**
  1. **Batch Multi-Face Detection:** Recognize an entire row of students in a single wide-angle frame using YOLO-Face or RetinaFace.
  2. **Edge Hardware Acceleration:** Port inference to an NVIDIA Jetson Orin Nano with TensorRT optimization for 60+ FPS edge execution.
  3. **Automated Notification Gateway:** Connect Twilio / WhatsApp Business API to dispatch automated absence alerts directly to parents when monthly attendance drops below 75%.
