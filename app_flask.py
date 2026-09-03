from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import subprocess
import sys
import os
from datetime import datetime

import database
import excel_manager

app = Flask(__name__)
CORS(app)

# Ensure SQLite database is initialized
database.init_db()

@app.route('/')
def index():
    """Renders the main glassmorphic Web Dashboard."""
    return render_template('index.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns analytics counters and recent attendance logs for today."""
    try:
        stats = database.get_dashboard_stats()
        today = stats['today_date']
        attendance_logs = database.get_attendance_logs(date_str=today)
        
        return jsonify({
            'success': True,
            'total_registered': stats['total_registered'],
            'present_today': stats['present_today'],
            'absent_today': stats['absent_today'],
            'attendance_rate': stats['attendance_rate'],
            'today_date': today,
            'attendance': attendance_logs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students', methods=['GET'])
def get_students():
    """Returns the list of registered students from the SQLite database."""
    try:
        students = database.get_all_students()
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/students/delete', methods=['POST'])
def delete_student():
    """Deletes a student record and their reference photo from known_faces/."""
    try:
        data = request.json or {}
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({'success': False, 'error': 'Student ID is required'}), 400

        # Remove reference photo if present
        known_dir = 'known_faces'
        if os.path.exists(known_dir):
            for fname in os.listdir(known_dir):
                if fname.endswith(f"_{student_id}.jpg") or fname.endswith(f"_{student_id}.png"):
                    try:
                        os.remove(os.path.join(known_dir, fname))
                    except Exception:
                        pass

        # Remove from database
        database.delete_student(student_id)
        return jsonify({'success': True, 'message': f'Student {student_id} deleted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """Retrieves attendance records with optional date filtering (?date=YYYY-MM-DD)."""
    try:
        date_param = request.args.get('date')
        logs = database.get_attendance_logs(date_str=date_param)
        return jsonify({'success': True, 'attendance': logs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/attendance/<int:record_id>', methods=['DELETE'])
def delete_attendance(record_id):
    """Deletes a specific attendance log entry by ID."""
    try:
        database.delete_attendance_record(record_id)
        return jsonify({'success': True, 'message': 'Record deleted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export', methods=['GET'])
def export_excel():
    """Generates and downloads the styled Excel spreadsheet for today's or master attendance."""
    try:
        date_param = request.args.get('date')
        if date_param:
            excel_filename = excel_manager.get_daily_excel_filename(date_param)
        else:
            excel_filename = excel_manager.MASTER_EXCEL_FILE

        if not os.path.exists(excel_filename):
            # If excel doesn't exist yet, build from DB
            logs = database.get_attendance_logs(date_str=date_param)
            for item in logs:
                excel_manager.sync_attendance_to_excel(
                    student_id=item['student_id'],
                    name=item['name'],
                    department=item.get('department', 'General'),
                    date_str=item['date'],
                    time_str=item['time'],
                    confidence=item.get('confidence', 0.0),
                    email_sent=item.get('email_sent', 0)
                )

        if os.path.exists(excel_filename):
            return send_file(excel_filename, as_attachment=True, download_name=os.path.basename(excel_filename))
        else:
            return jsonify({'success': False, 'error': 'No attendance records available for export.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register():
    """Triggers face capture and registers a new student."""
    try:
        data = request.json or {}
        name = data.get('name')
        sid = data.get('sid')
        dept = data.get('department', 'General')
        email = data.get('email', '')

        if not name or not sid:
            return jsonify({'success': False, 'error': 'Name and Student ID are required.'}), 400

        # Launch capture faces subprocess
        capture_cmd = [sys.executable, "capture_faces.py", name, sid, dept, email]
        proc = subprocess.run(capture_cmd, capture_output=True, text=True)

        if proc.returncode != 0:
            return jsonify({'success': False, 'error': f'Capture failed: {proc.stderr}'}), 500

        return jsonify({'success': True, 'message': f'Successfully registered {name} (ID: {sid})!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/start_attendance', methods=['POST'])
def start_attendance():
    """Spawns the camera recognition tracking engine in a separate console window."""
    try:
        if sys.platform == "win32":
            subprocess.Popen([sys.executable, "recognize_faces.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen([sys.executable, "recognize_faces.py"])
        return jsonify({'success': True, 'message': 'Live tracking engine initialized!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(debug=True, port=port)
