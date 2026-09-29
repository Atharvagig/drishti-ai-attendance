"""
Drishti AI — Project Root Launcher
Run this from d:\\project to start the backend server.
It sets the working directory to backend/ and imports app_flask.
"""
import sys
import os

# Ensure backend/ is the working directory and on sys.path
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from app_flask import socketio, app  # noqa: E402

if __name__ == '__main__':
    print("=" * 60)
    print("  DRISHTI AI v2.0 — Smart Campus Attendance Platform")
    print(f"  Backend  : {BACKEND_DIR}")
    print(f"  Frontend : {os.path.join(os.path.dirname(BACKEND_DIR), 'frontend')}")
    print("  URL      : http://localhost:5000")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
