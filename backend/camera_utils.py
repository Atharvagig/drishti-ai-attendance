import cv2
import time
import numpy as np

def get_working_camera(preferred_index=0):
    """
    Attempts to find and return a working OpenCV VideoCapture instance.
    Probes indices 0, 1, 2 across backends CAP_DSHOW, CAP_ANY, CAP_MSMF.
    Returns (cap, active_index, active_backend_name).
    """
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_ANY, "Auto/ANY"),
        (cv2.CAP_MSMF, "MediaFoundation")
    ]
    indices = [preferred_index] + [i for i in [0, 1, 2] if i != preferred_index]

    for idx in indices:
        for backend_id, name in backends:
            try:
                cap = cv2.VideoCapture(idx, backend_id)
                if cap.isOpened():
                    # Warm up camera briefly
                    time.sleep(0.2)
                    for _ in range(5):
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            print(f"[Camera Utils] Successfully connected to Camera Index {idx} using {name}.")
                            return cap, idx, name
                    cap.release()
            except Exception as e:
                print(f"[Camera Utils] Failed probe on Index {idx} ({name}): {e}")

    print("[Camera Utils] WARNING: No physical camera returned frames.")
    return None, -1, "None"

def create_synthetic_frame(text="Webcam Unavailable / Synthetic Feed"):
    """Generates a fallback test frame when hardware webcam is unavailable or locked."""
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Draw background gradient
    for y in range(720):
        frame[y, :, 0] = int(20 + (y / 720) * 30) # Blue channel
        frame[y, :, 1] = int(30 + (y / 720) * 20) # Green channel
        frame[y, :, 2] = int(45 + (y / 720) * 40) # Red channel

    # Draw grid box
    cv2.rectangle(frame, (100, 100), (1180, 620), (99, 102, 241), 2)
    cv2.putText(frame, "Drishti AI — Camera Diagnostics", (120, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    
    cv2.putText(frame, text, (120, 250),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 255), 2)
    
    cv2.putText(frame, "Status: Please check webcam permissions or device connections.", (120, 320),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

    cv2.putText(frame, "Press 'q' to exit window.", (120, 580),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return frame

if __name__ == '__main__':
    cap, idx, backend = get_working_camera()
    if cap:
        print(f"Test Successful: Camera {idx} ({backend}) is active.")
        cap.release()
    else:
        print("Hardware camera unavailable. Fallback synthetic generator ready.")
