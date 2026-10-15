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
    port = int(os.environ.get('PORT', 5000))
    is_prod = os.environ.get('FLASK_ENV', 'development').lower() == 'production'
    print("=" * 60)
    print("  DRISHTI AI v2.0 — Smart Campus Attendance Platform")
    print(f"  Backend  : {BACKEND_DIR}")
    print(f"  Frontend : {os.path.join(os.path.dirname(BACKEND_DIR), 'frontend')}")
    print(f"  Binding  : 0.0.0.0:{port} (Production: {is_prod})")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=port, debug=not is_prod, use_reloader=False, allow_unsafe_werkzeug=True)
