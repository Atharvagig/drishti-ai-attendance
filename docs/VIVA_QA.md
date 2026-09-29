# Drishti AI — Viva Cheat Sheet (Q&A)

**1. Why use face recognition for attendance?**
Face recognition is touchless, non-intrusive, and prevents proxy attendance compared to traditional RFID cards or manual roll calls. It verifies the actual physical presence of the student.

**2. Why did you choose `dlib` over OpenCV's Haar Cascades?**
Haar Cascades are outdated, highly sensitive to lighting, and prone to false positives. `dlib` uses a deep learning-based ResNet network that produces highly robust 128-D facial embeddings, which are much more accurate for identifying specific individuals.

**3. What are 128-D embeddings?**
A 128-D embedding is a numerical array of 128 floating-point numbers. The `dlib` network analyzes a face and maps its structural features into a 128-dimensional space. Faces of the same person will cluster closely together in this space.

**4. How does face matching work?**
Once the system generates a 128-D embedding for a captured face, it compares it against all stored embeddings in the SQLite database by calculating the Euclidean distance between the arrays.

**5. What is Euclidean distance?**
Euclidean distance is the straight-line metric used to measure the distance between two points in multidimensional space. In this project, a smaller distance means the two 128-D arrays (faces) are highly similar.

**6. Why use a threshold of 0.45?**
The threshold determines how strict the matching is. A threshold of 0.6 is `face_recognition`'s default, but it can sometimes cause false positives (identifying the wrong person). We lowered it to 0.45 to ensure higher strictness, prioritizing accuracy over simply matching any face.

**7. What is liveness detection?**
Liveness detection is an anti-spoofing mechanism that verifies the subject is a live, physical human being and not a photograph or video held up to the camera.

**8. What is EAR?**
EAR stands for Eye Aspect Ratio. It is a mathematical calculation based on the distance between the vertical and horizontal facial landmarks around the eyes. 

**9. How is a blink detected?**
Using MediaPipe Face Mesh, we track the coordinates of the eyelids. When a person blinks, the vertical distance drops rapidly while the horizontal distance remains constant, causing the EAR value to drop below a specific threshold (e.g., 0.20).

**10. How is head movement detected?**
By tracking the nose tip landmark over consecutive frames using MediaPipe. If the pixel displacement of the nose tip exceeds a defined threshold, the system registers it as a physical head movement.

**11. How does duplicate prevention work?**
The backend `face_engine.py` maintains an internal dictionary `self.last_marked`. If a student is recognized, their ID and a timestamp are stored. If they are recognized again within the 30-second cooldown window, the system explicitly blocks the database insert and emits a duplicate attempt alert to the frontend.

**12. Why SQLite?**
SQLite is serverless, zero-configuration, and stores the entire database in a single local file (`attendance.db`). It is perfectly suited for a local, edge-deployed college desktop system.

**13. Why use WAL (Write-Ahead Logging) mode?**
Standard SQLite locks the entire database during writes. WAL mode allows concurrent reads and writes, which is critical since the web dashboard constantly queries analytics while the face recognition engine constantly inserts attendance records.

**14. Why Flask?**
Flask is a lightweight Python web framework. It provided the exact control needed to build our REST APIs and integrate directly with Python-based AI libraries (like `dlib` and `MediaPipe`) without the overhead of Django.

**15. Why Socket.IO?**
HTTP is stateless and request-driven. We needed the server to instantly "push" live recognition events to the dashboard without making the client refresh the page. Socket.IO maintains a persistent WebSocket connection for this real-time duplex communication.

**16. What is RBAC?**
Role-Based Access Control. Our system restricts access based on user roles (`super_admin`, `faculty`, `student`). The `@permission_required` Python decorator checks a user's role before executing an API route.

**17. How are passwords protected?**
Passwords are never stored in plain text. They are hashed using `bcrypt` during registration. Bcrypt applies a mathematical salt, meaning even identical passwords produce different hashes, protecting against rainbow table attacks.

**18. How does Excel synchronization work?**
When the user clicks Export, the `/api/export` endpoint fetches data from the database and uses `openpyxl` (and `csv.DictWriter`) to generate formatted spreadsheets on-the-fly. We also maintain a legacy backup sync method in `excel_manager.py`.

**19. What happens if the Excel file is locked?**
If an administrator has the Excel file open, Windows locks it. Our `excel_manager.py` uses a `try...except PermissionError` block to catch this gracefully. The backend logs the error but does NOT crash, ensuring the primary SQLite database still records the attendance.

**20. What happens if the camera fails?**
The `face_engine.py` relies on OpenCV (`cv2.VideoCapture`). If it fails to read a frame or the camera disconnects, it gracefully returns an error status and the WebSocket emits a "Camera Offline" event to the frontend UI.

**21. How are unknown faces handled?**
If a face is detected but its Euclidean distance to all known embeddings is above our 0.45 threshold, the backend categorizes it as `Unknown`. It emits an `anomaly_detected` WebSocket event, and the UI displays a "⚠ UNKNOWN FACE" alert. No database insert occurs.

**22. What are the system limitations?**
The `dlib` CNN and embedding generation are CPU-intensive. Without a dedicated GPU (CUDA), processing multiple high-resolution faces simultaneously can cause frame rate drops. Additionally, poor lighting can hinder MediaPipe's ability to calculate the EAR for blink detection.

**23. What would you improve in the future?**
I would compile `dlib` with CUDA support to offload face encoding to the GPU. I would also architect the system to handle multiple IP camera feeds concurrently via RTSP, pushing data to a centralized cloud database.

**24. Why not deploy this to the cloud right now?**
Streaming uncompressed video frames to a cloud server introduces massive bandwidth requirements and high latency, breaking real-time liveness detection. Processing must happen on the "edge" (local computer) to maintain high FPS, and only lightweight text data (attendance logs) should be synced to the cloud.

**25. How can this scale to thousands of students?**
SQLite is sufficient for thousands of records, but for tens of thousands, we would migrate to PostgreSQL. Furthermore, we would index the 128-D embeddings using vector databases like FAISS or Milvus, which calculate Euclidean distances significantly faster than linear iterations.
