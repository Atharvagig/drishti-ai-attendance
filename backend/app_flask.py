"""
Drishti AI — Flask Application v2.1 (RBAC Edition)
Full REST API + SocketIO real-time updates.
Endpoints protected with centralized permission decorators from rbac.py.
"""
from flask import (Flask, render_template, jsonify, request,
                   send_file, session, redirect, url_for, Response)
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import subprocess
import threading
import sys
import os
import io
import csv
import json
import bcrypt
from datetime import datetime, timedelta
from functools import wraps

# ── Path Constants ─────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(BACKEND_DIR, 'data')
FRONTEND_DIR = os.path.join(BACKEND_DIR, '..', 'frontend')

import database
import excel_manager
import camera_utils
from rbac import (
    login_required, permission_required, role_required,
    has_permission, get_user_permissions, get_current_user_scope,
    get_allowed_student_ids, get_allowed_session_ids,
    can_modify_attendance_record, is_super_admin, ROLE_PERMISSIONS,
)

# ── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, 'templates'),
    static_folder=os.path.join(FRONTEND_DIR, 'static'),
)
app.secret_key = os.environ.get('SECRET_KEY', 'drishti-ai-secure-key-v2-change-in-prod')

# Session configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 60))
)

CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading',
                    logger=False, engineio_logger=False)

# Initialize DB + seed RBAC defaults
database.init_db()
database.seed_defaults()

# Active recognition thread reference
_recognition_thread = None
_recognition_session = None


# ── Security Headers ──────────────────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


# ── Session Activity Touch & CSRF ───────────────────────────────────────────
import secrets

@app.before_request
def touch_session_and_csrf():
    """Mark session as permanent and validate CSRF token for state-changing requests."""
    if session.get('user_id'):
        session.permanent = True

    # Exempt login route from CSRF check
    if request.endpoint in ('auth_login', 'static'):
        return

    # CSRF check for mutations
    if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
        # API endpoints
        token = session.get('_csrf_token')
        if not token or token != request.headers.get('X-CSRFToken'):
            return jsonify({'success': False, 'error': 'csrf_failed', 'message': 'CSRF verification failed.'}), 403

@app.after_request
def set_csrf_cookie(response):
    """Set CSRF token in a cookie that JS can read to send back in header."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    # httponly=False so JS can read it for the X-CSRFToken header
    response.set_cookie('csrf_token', session['_csrf_token'], httponly=False, samesite='Lax')
    return response


# ── Consistent Error Helpers ──────────────────────────────────────────────────
def err401():
    return jsonify({'success': False, 'error': 'authentication_required',
                    'message': 'Authentication required.'}), 401


def err403():
    return jsonify({'success': False, 'error': 'permission_denied',
                    'message': 'You do not have permission to perform this action.'}), 403


def err404(msg='Resource not found.'):
    return jsonify({'success': False, 'error': 'not_found', 'message': msg}), 404


def err400(msg='Bad request.'):
    return jsonify({'success': False, 'error': 'bad_request', 'message': msg}), 400


def err500(e):
    # Never expose internal details to client
    print(f'[Server Error] {e}')
    return jsonify({'success': False, 'error': 'server_error',
                    'message': 'An internal server error occurred.'}), 500


# ── Page Routes ───────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect('/login')
    
    role = session.get('role', '')
    if role in ('super_admin', 'attendance_operator'):
        return redirect('/admin')
    elif role in ('department_head', 'faculty'):
        return redirect('/faculty')
    else:
        return redirect('/student')

@app.route('/admin')
@login_required
@role_required('super_admin', 'attendance_operator')
def admin_panel():
    return render_template('admin_panel.html')

@app.route('/faculty')
@login_required
@role_required('department_head', 'faculty', 'super_admin')
def faculty_panel():
    return render_template('faculty_panel.html')

@app.route('/student')
@login_required
def student_panel():
    return render_template('student_panel.html')

@app.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect('/')
    return render_template('login.html')


# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400

    result = database.verify_user(username, password)

    # Handle error codes from the new verify_user
    if isinstance(result, str):
        error_code = result
        # Log failed attempt
        database.log_audit(None, username, 'LOGIN_FAILED', 'auth',
                           '', '', error_code, request.remote_addr)

        if error_code == 'account_disabled':
            return jsonify({
                'success': False,
                'error': 'account_disabled',
                'message': 'This account has been disabled. Contact an administrator.',
            }), 403

        if error_code == 'account_locked':
            return jsonify({
                'success': False,
                'error': 'account_locked',
                'message': 'Account temporarily locked due to too many failed attempts. Try again later.',
            }), 403

        # Generic message — do NOT reveal whether username exists
        return jsonify({
            'success': False,
            'error': 'invalid_credentials',
            'message': 'Invalid username or password.',
        }), 401

    # Successful login
    user = result
    session.permanent = True
    session['user_id']      = user['id']
    session['username']     = user['username']
    session['role']         = user['role']
    session['name']         = user.get('full_name') or user.get('name', '')
    session['department_id'] = user.get('department_id')
    session['student_id']  = user.get('student_id')

    permissions = get_user_permissions(user['role'])

    database.log_audit(user['id'], user['username'], 'LOGIN_SUCCESS', 'auth',
                       str(user['id']), '', '', request.remote_addr)

    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': session['name'],
            'role': user['role'],
            'permissions': permissions,
            'department_id': user.get('department_id'),
            'department_name': user.get('department_name', ''),
        },
    })


@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    username = session.get('username', 'unknown')
    user_id  = session.get('user_id')
    session.clear()
    database.log_audit(user_id, username, 'LOGOUT', 'auth', '', '', '', request.remote_addr)
    return jsonify({'success': True})


@app.route('/auth/me', methods=['GET'])
def auth_me():
    if not session.get('user_id'):
        return jsonify({'success': False, 'authenticated': False})

    role = session.get('role', '')
    permissions = get_user_permissions(role)

    return jsonify({
        'success': True,
        'authenticated': True,
        'user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'full_name': session.get('name'),
            'role': role,
            'permissions': permissions,
            'department_id': session.get('department_id'),
        },
    })


@app.route('/auth/change-password', methods=['POST'])
@login_required
def auth_change_password():
    data = request.json or {}
    current_pw = data.get('current_password', '')
    new_pw     = data.get('new_password', '')

    if not current_pw or not new_pw:
        return err400('current_password and new_password are required.')

    try:
        database.change_own_password(session['user_id'], current_pw, new_pw)
        database.log_audit(session['user_id'], session['username'],
                           'PASSWORD_CHANGED', 'user', str(session['user_id']),
                           '', '', request.remote_addr)
        return jsonify({'success': True, 'message': 'Password changed successfully.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return err500(e)


# ── User Management API ───────────────────────────────────────────────────────

@app.route('/api/users', methods=['GET'])
@permission_required('users.view')
def get_users():
    try:
        users = database.get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return err500(e)


@app.route('/api/users', methods=['POST'])
@permission_required('users.create')
def create_user():
    try:
        data = request.json or {}
        required = ['username', 'password', 'role', 'full_name']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return err400(f'Missing fields: {", ".join(missing)}')

        # Only super_admin can create other super_admins
        if data['role'] == 'super_admin' and not is_super_admin():
            return err403()

        user_id = database.create_user(
            username=data['username'],
            password=data['password'],
            role=data['role'],
            full_name=data['full_name'],
            email=data.get('email', ''),
            department_id=data.get('department_id') or None,
            student_id=data.get('student_id') or None,
        )

        database.log_audit(session['user_id'], session['username'],
                           'USER_CREATED', 'user', str(user_id),
                           '', data['role'], request.remote_addr)

        return jsonify({'success': True, 'user_id': user_id,
                        'message': f"User '{data['username']}' created."}), 201

    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        if 'UNIQUE constraint' in str(e):
            return jsonify({'success': False,
                            'message': 'Username already exists.'}), 409
        return err500(e)


@app.route('/api/users/<int:user_id>', methods=['GET'])
@permission_required('users.view')
def get_user(user_id):
    try:
        user = database.get_user_by_id(user_id)
        if not user:
            return err404('User not found.')
        return jsonify({'success': True, 'user': user})
    except Exception as e:
        return err500(e)


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@permission_required('users.update')
def update_user(user_id):
    try:
        data = request.json or {}
        # Prevent non-super_admin from promoting someone to super_admin
        if data.get('role') == 'super_admin' and not is_super_admin():
            return err403()
        # Prevent editing a super_admin's role unless you are super_admin
        target = database.get_user_by_id(user_id)
        if not target:
            return err404('User not found.')
        if target['role'] == 'super_admin' and not is_super_admin():
            return err403()

        old_role = target.get('role', '')
        fields = {k: v for k, v in data.items()
                  if k in ('full_name', 'email', 'role', 'department_id', 'student_id')}
        database.update_user(user_id, **fields)

        if 'role' in fields and fields['role'] != old_role:
            database.log_audit(session['user_id'], session['username'],
                               'ROLE_CHANGED', 'user', str(user_id),
                               old_role, fields['role'], request.remote_addr)
        else:
            database.log_audit(session['user_id'], session['username'],
                               'USER_UPDATED', 'user', str(user_id),
                               '', '', request.remote_addr)

        return jsonify({'success': True, 'message': 'User updated.'})
    except Exception as e:
        return err500(e)


@app.route('/api/users/<int:user_id>/disable', methods=['POST'])
@permission_required('users.disable')
def disable_user(user_id):
    try:
        target = database.get_user_by_id(user_id)
        if not target:
            return err404('User not found.')
        if target['role'] == 'super_admin' and not is_super_admin():
            return err403()
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'message': 'Cannot disable your own account.'}), 400

        database.set_user_active(user_id, False)
        database.log_audit(session['user_id'], session['username'],
                           'USER_DISABLED', 'user', str(user_id),
                           'active', 'disabled', request.remote_addr)
        return jsonify({'success': True, 'message': 'User account disabled.'})
    except Exception as e:
        return err500(e)


@app.route('/api/users/<int:user_id>/enable', methods=['POST'])
@permission_required('users.disable')
def enable_user(user_id):
    try:
        target = database.get_user_by_id(user_id)
        if not target:
            return err404('User not found.')
        database.set_user_active(user_id, True)
        database.log_audit(session['user_id'], session['username'],
                           'USER_ENABLED', 'user', str(user_id),
                           'disabled', 'active', request.remote_addr)
        return jsonify({'success': True, 'message': 'User account enabled.'})
    except Exception as e:
        return err500(e)


@app.route('/api/users/<int:user_id>/unlock', methods=['POST'])
@permission_required('users.disable')
def unlock_user_account(user_id):
    try:
        database.unlock_user(user_id)
        database.log_audit(session['user_id'], session['username'],
                           'USER_UNLOCKED', 'user', str(user_id),
                           'locked', 'active', request.remote_addr)
        return jsonify({'success': True, 'message': 'Account unlocked.'})
    except Exception as e:
        return err500(e)


@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@permission_required('users.reset_password')
def reset_user_password(user_id):
    try:
        data = request.json or {}
        new_pw = data.get('new_password', '')
        if not new_pw:
            return err400('new_password is required.')
        database.reset_user_password(user_id, new_pw)
        database.log_audit(session['user_id'], session['username'],
                           'PASSWORD_RESET', 'user', str(user_id),
                           '', '', request.remote_addr)
        return jsonify({'success': True, 'message': 'Password reset successfully.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return err500(e)


# ── Dashboard Stats ────────────────────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
@permission_required('dashboard.view')
def get_stats():
    try:
        role = session.get('role', '')
        stats = database.get_dashboard_stats()
        today = stats['today_date']
        attendance_logs = database.get_attendance_logs(date_str=today)
        today_sessions  = database.get_all_sessions(date_str=today)
        unread_notifs   = database.get_unread_count()

        # Scope: students can only see their own attendance
        if role == 'student':
            sid = session.get('student_id', '')
            attendance_logs = [a for a in attendance_logs if a['student_id'] == sid]
            today_sessions  = []
            # Return personal stats only
            personal_total = len(attendance_logs)
            personal_present = sum(1 for a in attendance_logs if a['status'] in ('Present', 'Late'))
            stats = {
                'total_registered': personal_total,
                'present_today': personal_present,
                'late_today': sum(1 for a in attendance_logs if a['status'] == 'Late'),
                'absent_today': personal_total - personal_present,
                'attendance_rate': round(personal_present / personal_total * 100, 1) if personal_total else 0.0,
                'active_sessions': 0,
                'unresolved_anomalies': 0,
                'at_risk_count': 0,
                'today_date': today,
            }

        # Scope: faculty sees only their sessions' attendance
        elif role == 'faculty':
            username = session.get('username', '')
            today_sessions = [s for s in today_sessions if s.get('created_by') == username]

        # Scope: department_head sees department data
        elif role == 'department_head':
            dept_id = session.get('department_id')
            if dept_id:
                with database.get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('SELECT name FROM departments WHERE id = ?', (dept_id,))
                    row = c.fetchone()
                    dept_name = row['name'] if row else ''
                attendance_logs = [a for a in attendance_logs
                                   if a.get('department') == dept_name]
                today_sessions = [s for s in today_sessions
                                  if s.get('department') == dept_name]

        return jsonify({
            'success': True,
            **stats,
            'attendance': attendance_logs,
            'today_sessions': today_sessions,
            'unread_notifications': unread_notifs,
        })
    except Exception as e:
        return err500(e)


# ── Students ──────────────────────────────────────────────────────────────────
@app.route('/api/students', methods=['GET'])
@login_required
def get_students():
    try:
        role = session.get('role', '')

        # Students can only see themselves
        if role == 'student':
            if not has_permission('students.view_own'):
                return err403()
            sid = session.get('student_id', '')
            if not sid:
                return jsonify({'success': True, 'students': []})
            student = database.get_student_by_id(sid)
            return jsonify({'success': True, 'students': [student] if student else []})

        if not has_permission('students.view'):
            return err403()

        students = database.get_all_students()

        # Department head: filter by department
        if role == 'department_head':
            dept_id = session.get('department_id')
            if dept_id:
                with database.get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('SELECT name FROM departments WHERE id = ?', (dept_id,))
                    row = c.fetchone()
                    dept_name = row['name'] if row else ''
                students = [s for s in students if s.get('department') == dept_name]

        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return err500(e)


@app.route('/api/students/<student_id>/attendance', methods=['GET'])
@login_required
def get_student_attendance(student_id):
    try:
        role = session.get('role', '')
        # Students can only see their own
        if role == 'student' and student_id != session.get('student_id', ''):
            return err403()
        if not (has_permission('attendance.view') or
                has_permission('attendance.view_own')):
            return err403()

        history = database.get_student_attendance_history(student_id)
        return jsonify({'success': True, 'attendance': history})
    except Exception as e:
        return err500(e)


@app.route('/api/students/<student_id>/analytics', methods=['GET'])
@login_required
def get_student_analytics(student_id):
    try:
        role = session.get('role', '')
        # Students can only see their own analytics
        if role == 'student' and student_id != session.get('student_id', ''):
            return err403()
        if not (has_permission('analytics.view') or
                has_permission('analytics.view_own')):
            return err403()

        history = database.get_student_attendance_history(student_id, limit=200)
        total = len(history)
        if total == 0:
            rate = 0.0
            late_count = absent_count = 0
        else:
            attended    = sum(1 for r in history if r['status'] in ('Present', 'Late'))
            late_count  = sum(1 for r in history if r['status'] == 'Late')
            absent_count = sum(1 for r in history if r['status'] == 'Absent')
            rate = round(attended / total * 100, 1)

        required = 75.0
        if rate < 60:
            risk = 'HIGH'
        elif rate < 75:
            risk = 'MEDIUM'
        else:
            risk = 'LOW'

        classes_needed = 0
        if rate < required and total > 0:
            attended_count = sum(1 for r in history if r['status'] in ('Present', 'Late'))
            n = int(((0.75 * total - attended_count) / 0.25) + 1)
            classes_needed = max(0, n)

        student = database.get_student_by_id(student_id)
        embed_count = database.count_student_embeddings(student_id)

        return jsonify({
            'success': True,
            'student': student,
            'attendance_rate': rate,
            'total_sessions': total,
            'late_count': late_count,
            'absent_count': absent_count,
            'risk': risk,
            'classes_needed_for_75': classes_needed,
            'embeddings_stored': embed_count,
            'history': history[:50],
        })
    except Exception as e:
        return err500(e)


@app.route('/api/students/delete', methods=['POST'])
@permission_required('students.delete')
def delete_student():
    try:
        data = request.json or {}
        student_id = data.get('student_id')
        if not student_id:
            return err400('Student ID required.')

        # Remove reference photo
        known_dir = os.path.join(DATA_DIR, 'known_faces')
        if os.path.exists(known_dir):
            for fname in os.listdir(known_dir):
                if fname.endswith(f'_{student_id}.jpg') or fname.endswith(f'_{student_id}.png'):
                    try:
                        os.remove(os.path.join(known_dir, fname))
                    except Exception:
                        pass

        database.delete_student(student_id)
        database.log_audit(session.get('user_id'), session.get('username', 'unknown'),
                           'STUDENT_DELETED', 'student', student_id,
                           '', '', request.remote_addr)
        return jsonify({'success': True, 'message': f'Student {student_id} removed.'})
    except Exception as e:
        return err500(e)


# ── Attendance ────────────────────────────────────────────────────────────────
@app.route('/api/attendance', methods=['GET'])
@login_required
def get_attendance():
    try:
        role = session.get('role', '')
        date_param = request.args.get('date')
        session_id = request.args.get('session_id')

        if not (has_permission('attendance.view') or
                has_permission('attendance.view_own')):
            return err403()

        logs = database.get_attendance_logs(
            date_str=date_param,
            session_id=int(session_id) if session_id else None
        )

        # Object-level scoping
        if role == 'student':
            sid = session.get('student_id', '')
            logs = [a for a in logs if a['student_id'] == sid]

        elif role == 'department_head':
            dept_id = session.get('department_id')
            if dept_id:
                with database.get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('SELECT name FROM departments WHERE id = ?', (dept_id,))
                    row = c.fetchone()
                    dept_name = row['name'] if row else ''
                logs = [a for a in logs if a.get('department') == dept_name]

        elif role == 'faculty':
            username = session.get('username', '')
            with database.get_db_connection() as conn:
                allowed_sessions = get_allowed_session_ids(conn)
            if allowed_sessions is not None:
                logs = [a for a in logs
                        if a.get('session_id') in (allowed_sessions or [])]

        return jsonify({'success': True, 'attendance': logs})
    except Exception as e:
        return err500(e)


@app.route('/api/attendance/<int:record_id>', methods=['DELETE'])
@permission_required('attendance.delete')
def delete_attendance(record_id):
    try:
        # Check locked session
        with database.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM attendance WHERE id = ?', (record_id,))
            row = c.fetchone()
        if not row:
            return err404('Attendance record not found.')
        record = dict(row)

        if not is_super_admin():
            sess = database.get_session(record.get('session_id'))
            if sess and sess.get('status') == 'locked':
                return jsonify({'success': False,
                                'message': 'Cannot delete records from a locked session.'}), 403

        database.delete_attendance_record(record_id)
        database.log_audit(session.get('user_id'), session.get('username', 'unknown'),
                           'ATTENDANCE_DELETED', 'attendance', str(record_id),
                           '', '', '')
        return jsonify({'success': True, 'message': 'Record deleted.'})
    except Exception as e:
        return err500(e)


@app.route('/api/attendance/<int:record_id>/override', methods=['POST'])
@permission_required('attendance.update')
def override_attendance(record_id):
    try:
        data = request.json or {}
        new_status  = data.get('status')
        reason      = data.get('reason', '')
        override_by = session.get('username', data.get('override_by', 'admin'))

        if not new_status:
            return err400('New status required.')

        valid_statuses = ['Present', 'Late', 'Absent', 'Excused', 'HalfDay', 'ManualOverride']
        if new_status not in valid_statuses:
            return err400(f'Invalid status. Must be one of: {valid_statuses}')

        # Fetch record for permission check
        with database.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM attendance WHERE id = ?', (record_id,))
            row = c.fetchone()
        if not row:
            return err404('Attendance record not found.')

        record = dict(row)
        if not can_modify_attendance_record(record):
            return err403()

        success, old_status = database.override_attendance(record_id, new_status, reason, override_by)
        if not success:
            return jsonify({'success': False, 'error': old_status}), 404

        database.log_audit(session.get('user_id'), override_by,
                           'ATTENDANCE_UPDATED', 'attendance', str(record_id),
                           old_status, new_status, request.remote_addr)

        return jsonify({
            'success': True,
            'message': f'Attendance updated from {old_status} to {new_status}',
            'old_status': old_status,
            'new_status': new_status,
        })
    except Exception as e:
        return err500(e)


# ── Attendance Sessions ────────────────────────────────────────────────────────
@app.route('/api/sessions', methods=['GET'])
@permission_required('sessions.view')
def get_sessions():
    try:
        role = session.get('role', '')
        date_param = request.args.get('date')
        sessions = database.get_all_sessions(date_str=date_param)

        # Faculty sees only their own sessions
        if role == 'faculty':
            username = session.get('username', '')
            sessions = [s for s in sessions if s.get('created_by') == username]

        # Department head sees department sessions
        elif role == 'department_head':
            dept_id = session.get('department_id')
            if dept_id:
                with database.get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('SELECT name FROM departments WHERE id = ?', (dept_id,))
                    row = c.fetchone()
                    dept_name = row['name'] if row else ''
                sessions = [s for s in sessions if s.get('department') == dept_name]

        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return err500(e)


@app.route('/api/sessions', methods=['POST'])
@permission_required('sessions.create')
def create_session():
    try:
        data = request.json or {}
        required = ['subject_name', 'faculty_name', 'classroom_name', 'date', 'start_time']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return err400(f'Missing fields: {", ".join(missing)}')

        session_id = database.create_session(
            subject_name=data['subject_name'],
            faculty_name=data['faculty_name'],
            classroom_name=data['classroom_name'],
            department=data.get('department', 'General'),
            semester=int(data.get('semester', 1)),
            date_str=data['date'],
            start_time=data['start_time'],
            late_threshold_minutes=int(data.get('late_threshold_minutes', 10)),
            camera_id=data.get('camera_id', 'CAM-01'),
            created_by=session.get('username', 'admin'),
        )

        database.log_audit(session.get('user_id'), session.get('username', 'admin'),
                           'SESSION_CREATED', 'session', str(session_id),
                           '', json.dumps(data), '')

        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'Session created (ID: {session_id})',
        })
    except Exception as e:
        return err500(e)


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
@permission_required('sessions.view')
def get_session(session_id):
    try:
        sess = database.get_session(session_id)
        if not sess:
            return err404('Session not found.')
        att = database.get_attendance_logs(session_id=session_id)
        return jsonify({'success': True, 'session': sess, 'attendance': att})
    except Exception as e:
        return err500(e)


@app.route('/api/sessions/<int:session_id>/start', methods=['POST'])
@permission_required('sessions.start')
def start_session(session_id):
    global _recognition_thread, _recognition_session
    try:
        sess = database.get_session(session_id)
        if not sess:
            return err404('Session not found.')
        if sess['status'] == 'locked':
            return jsonify({'success': False, 'error': 'Session is locked'}), 400
        if sess['status'] == 'active':
            return jsonify({'success': False, 'error': 'Session already active'}), 400

        # Faculty can only start their own sessions (unless super_admin/dept_head)
        role = session.get('role', '')
        if role == 'faculty':
            if sess.get('created_by') != session.get('username', ''):
                return err403()

        database.update_session_status(session_id, 'active')

        from face_engine import RecognitionSession
        _recognition_session = RecognitionSession(session_id=session_id, socketio=socketio)

        if _recognition_thread and _recognition_thread.is_alive():
            old = _recognition_session
            if old:
                old.stop()

        _recognition_thread = threading.Thread(
            target=_recognition_session.run, daemon=True)
        _recognition_thread.start()

        database.log_audit(session.get('user_id'), session.get('username', 'admin'),
                           'SESSION_STARTED', 'session', str(session_id),
                           'scheduled', 'active', '')
        database.create_notification(
            title='Session Started',
            message=f"Session '{sess['subject_name']}' is now active",
            type='info'
        )

        socketio.emit('session_started', {
            'session_id': session_id,
            'subject': sess['subject_name'],
            'faculty': sess['faculty_name'],
        })

        return jsonify({'success': True, 'message': f'Session {session_id} started.'})
    except Exception as e:
        return err500(e)


@app.route('/api/sessions/<int:session_id>/stop', methods=['POST'])
@permission_required('sessions.stop')
def stop_session(session_id):
    global _recognition_session
    try:
        sess = database.get_session(session_id)
        if not sess:
            return err404('Session not found.')

        role = session.get('role', '')
        if role == 'faculty' and sess.get('created_by') != session.get('username', ''):
            return err403()

        if _recognition_session:
            _recognition_session.stop()

        end_time = datetime.now().strftime('%H:%M:%S')
        database.update_session_status(session_id, 'completed', end_time)
        database.mark_absent_for_session(session_id)

        att   = database.get_attendance_logs(session_id=session_id)
        present = sum(1 for a in att if a['status'] in ('Present', 'Late'))
        total   = len([s for s in database.get_all_students()])

        database.create_notification(
            title='Session Completed',
            message=f"{sess['subject_name']}: {present}/{total} students attended",
            type='success'
        )

        socketio.emit('session_stopped', {
            'session_id': session_id,
            'present': present,
            'total': total,
        })

        database.log_audit(session.get('user_id'), session.get('username', 'admin'),
                           'SESSION_STOPPED', 'session', str(session_id),
                           'active', 'completed', '')

        return jsonify({
            'success': True,
            'message': f'Session stopped. {present}/{total} attended.',
            'present': present,
            'total': total,
        })
    except Exception as e:
        return err500(e)


@app.route('/api/sessions/<int:session_id>/lock', methods=['POST'])
@permission_required('sessions.lock')
def lock_session(session_id):
    try:
        sess = database.get_session(session_id)
        if not sess:
            return err404('Session not found.')
        if sess['status'] == 'active':
            return jsonify({'success': False, 'error': 'Stop the session before locking'}), 400

        role = session.get('role', '')
        if role == 'faculty' and sess.get('created_by') != session.get('username', ''):
            return err403()

        database.update_session_status(session_id, 'locked')
        database.log_audit(session.get('user_id'), session.get('username', 'admin'),
                           'SESSION_LOCKED', 'session', str(session_id),
                           sess['status'], 'locked', '')

        return jsonify({'success': True, 'message': f'Session {session_id} locked.'})
    except Exception as e:
        return err500(e)


@app.route('/api/sessions/<int:session_id>/attendance', methods=['GET'])
@permission_required('sessions.view')
def get_session_attendance(session_id):
    try:
        att  = database.get_attendance_logs(session_id=session_id)
        sess = database.get_session(session_id)
        return jsonify({'success': True, 'session': sess, 'attendance': att})
    except Exception as e:
        return err500(e)


# ── Registration / Biometric Enrollment ───────────────────────────────────────
@app.route('/api/register', methods=['POST'])
@permission_required('biometric.enroll')
def register():
    try:
        data = request.json or {}
        name     = data.get('name', '').strip()
        sid      = data.get('sid', '').strip()
        dept     = data.get('department', 'General').strip()
        email    = data.get('email', '').strip()
        semester = int(data.get('semester', 1))

        if not name or not sid:
            return err400('Name and Student ID are required.')

        existing = database.get_student_by_id(sid)
        if existing and request.json.get('force') is not True:
            return jsonify({
                'success': False,
                'error': f'Student ID {sid} already exists. Use force=true to re-enroll.',
                'existing': {'name': existing['name'], 'department': existing['department']}
            }), 409

        capture_cmd = [
            sys.executable, os.path.join(BACKEND_DIR, 'capture_faces.py'),
            name, sid, dept, email, str(semester)
        ]
        proc = subprocess.run(
            capture_cmd,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() if proc.stderr else 'Unknown capture error'
            return jsonify({'success': False, 'error': f'Capture failed: {err_msg}'}), 500

        embed_count = database.count_student_embeddings(sid)
        database.log_audit(session.get('user_id'), session.get('username', 'admin'),
                           'BIOMETRIC_ENROLLED', 'student', sid,
                           '', name, request.remote_addr)

        return jsonify({
            'success': True,
            'message': f'Enrolled {name} (ID: {sid}) with {embed_count} face embeddings.',
            'embeddings': embed_count,
        })
    except Exception as e:
        return err500(e)


@app.route('/api/start_attendance', methods=['POST'])
@permission_required('tracking.start')
def start_attendance_legacy():
    """Legacy endpoint — launches recognition without a session."""
    try:
        global _recognition_thread, _recognition_session
        from face_engine import RecognitionSession
        _recognition_session = RecognitionSession(session_id=None, socketio=socketio)
        _recognition_thread = threading.Thread(
            target=_recognition_session.run, daemon=True)
        _recognition_thread.start()
        database.log_audit(session.get('user_id'), session.get('username', 'system'),
                           'TRACKING_STARTED', 'camera', '', '', '', request.remote_addr)
        return jsonify({'success': True, 'message': 'Live tracking engine started (no session).'})
    except Exception as e:
        return err500(e)


# ── Analytics ─────────────────────────────────────────────────────────────────
@app.route('/api/analytics/overview', methods=['GET'])
@permission_required('analytics.view')
def analytics_overview():
    try:
        stats     = database.get_dashboard_stats()
        trends    = database.get_attendance_trends(days=30)
        dept_stats = database.get_department_stats()
        at_risk   = database.get_at_risk_students()
        return jsonify({
            'success': True,
            'stats': stats,
            'trends': trends,
            'department_stats': dept_stats,
            'at_risk': at_risk,
        })
    except Exception as e:
        return err500(e)


@app.route('/api/analytics/trends', methods=['GET'])
@permission_required('analytics.view')
def analytics_trends():
    try:
        days = int(request.args.get('days', 30))
        trends = database.get_attendance_trends(days=days)
        return jsonify({'success': True, 'trends': trends})
    except Exception as e:
        return err500(e)


@app.route('/api/analytics/insights', methods=['GET'])
@permission_required('analytics.view')
def analytics_insights():
    try:
        insights = database.get_ai_insights()
        return jsonify({'success': True, 'insights': insights})
    except Exception as e:
        return err500(e)


@app.route('/api/analytics/heatmap', methods=['GET'])
@login_required
def analytics_heatmap():
    try:
        role = session.get('role', '')
        student_id = request.args.get('student_id')
        months     = int(request.args.get('months', 3))

        # Students can only see their own heatmap
        if role == 'student':
            if not has_permission('analytics.view_own'):
                return err403()
            student_id = session.get('student_id', '')

        elif not has_permission('analytics.view'):
            return err403()

        data = database.get_heatmap_data(student_id=student_id, months=months)
        return jsonify({'success': True, 'heatmap': data})
    except Exception as e:
        return err500(e)


# ── Camera Management ─────────────────────────────────────────────────────────
@app.route('/api/cameras', methods=['GET'])
@permission_required('cameras.view')
def get_cameras():
    try:
        cams = database.get_all_cameras()
        return jsonify({'success': True, 'cameras': cams})
    except Exception as e:
        return err500(e)


@app.route('/api/cameras/heartbeat', methods=['POST'])
@permission_required('cameras.manage')
def camera_heartbeat():
    try:
        data = request.json or {}
        camera_id = data.get('camera_id', 'CAM-01')
        status    = data.get('status', 'online')
        fps       = float(data.get('fps', 0.0))
        database.update_camera_heartbeat(camera_id, status, fps)
        return jsonify({'success': True})
    except Exception as e:
        return err500(e)


@app.route('/api/camera/stream')
@permission_required('tracking.view')
def camera_stream():
    """MJPEG live stream endpoint — requires tracking.view permission."""
    import cv2
    import time

    def generate():
        cap, _, _ = camera_utils.get_working_camera(preferred_index=0)
        use_synth = cap is None

        while True:
            if not use_synth and cap:
                ret, frame = cap.read()
                if not ret:
                    use_synth = True
                    frame = camera_utils.create_synthetic_frame('Camera unavailable')
            else:
                frame = camera_utils.create_synthetic_frame('Demo Feed — No Camera')
                time.sleep(0.033)

            frame = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                   buffer.tobytes() + b'\r\n')

        if cap:
            cap.release()

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ── Notifications ─────────────────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    try:
        notifs = database.get_notifications(limit=30)
        unread = database.get_unread_count()
        return jsonify({'success': True, 'notifications': notifs, 'unread': unread})
    except Exception as e:
        return err500(e)


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def read_notification(notif_id):
    try:
        database.mark_notification_read(notif_id)
        return jsonify({'success': True})
    except Exception as e:
        return err500(e)


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    try:
        notifs = database.get_notifications(limit=200)
        for n in notifs:
            database.mark_notification_read(n['id'])
        return jsonify({'success': True})
    except Exception as e:
        return err500(e)


# ── Anomalies ─────────────────────────────────────────────────────────────────
@app.route('/api/anomalies', methods=['GET'])
@permission_required('dashboard.view')
def get_anomalies():
    try:
        unresolved_only = request.args.get('unresolved', 'false') == 'true'
        anomalies = database.get_anomalies(limit=50, unresolved_only=unresolved_only)
        return jsonify({'success': True, 'anomalies': anomalies})
    except Exception as e:
        return err500(e)


# ── Audit Logs ────────────────────────────────────────────────────────────────
@app.route('/api/audit-logs', methods=['GET'])
@permission_required('audit.view')
def get_audit_logs():
    try:
        limit       = int(request.args.get('limit', 100))
        username    = request.args.get('username')
        action      = request.args.get('action')
        entity_type = request.args.get('entity_type')
        date_from   = request.args.get('date_from')
        date_to     = request.args.get('date_to')

        # Department heads can only see logs related to their department users
        logs = database.get_audit_logs_filtered(
            limit=limit,
            username=username,
            action=action,
            entity_type=entity_type,
            date_from=date_from,
            date_to=date_to,
        )
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        return err500(e)


# ── Export ────────────────────────────────────────────────────────────────────
@app.route('/api/export', methods=['GET'])
@permission_required('attendance.export')
def export_excel():
    """Original Excel export — preserved for backwards compatibility."""
    try:
        date_param = request.args.get('date')
        if date_param:
            excel_filename = excel_manager.get_daily_excel_filename(date_param)
        else:
            excel_filename = excel_manager.MASTER_EXCEL_FILE

        if not os.path.exists(excel_filename):
            logs = database.get_attendance_logs(date_str=date_param)
            for item in logs:
                excel_manager.sync_attendance_to_excel(
                    student_id=item['student_id'],
                    name=item['name'],
                    department=item.get('department', 'General'),
                    date_str=item['date'],
                    time_str=item['time'],
                    confidence=item.get('confidence', 0.0),
                    email_sent=item.get('email_sent', 0),
                )

        if os.path.exists(excel_filename):
            database.log_audit(session.get('user_id'), session.get('username', ''),
                               'EXPORT_GENERATED', 'attendance', 'excel',
                               '', date_param or 'all', request.remote_addr)
            return send_file(excel_filename, as_attachment=True,
                             download_name=os.path.basename(excel_filename))
        else:
            return err404('No records to export.')
    except Exception as e:
        return err500(e)


@app.route('/api/export/csv', methods=['GET'])
@permission_required('attendance.export')
def export_csv():
    try:
        date_param  = request.args.get('date')
        session_id  = request.args.get('session_id')
        dept_filter = request.args.get('department', '')

        logs = database.get_attendance_logs(
            date_str=date_param,
            session_id=int(session_id) if session_id else None,
        )

        # Scope: non-admin export only their own data
        role = session.get('role', '')
        if role == 'faculty':
            username = session.get('username', '')
            with database.get_db_connection() as conn:
                allowed_sessions = get_allowed_session_ids(conn)
            if allowed_sessions is not None:
                logs = [a for a in logs
                        if a.get('session_id') in (allowed_sessions or [])]

        if dept_filter:
            logs = [r for r in logs if r.get('department', '') == dept_filter]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'id', 'student_id', 'name', 'department', 'date', 'time',
            'status', 'confidence', 'liveness_passed', 'face_quality', 'session_id'
        ])
        writer.writeheader()
        for row in logs:
            writer.writerow({k: row.get(k, '') for k in writer.fieldnames})

        output.seek(0)
        fname = f'Attendance_{date_param or "all"}.csv'
        database.log_audit(session.get('user_id'), session.get('username', ''),
                           'EXPORT_GENERATED', 'attendance', 'csv',
                           '', date_param or 'all', request.remote_addr)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            as_attachment=True,
            download_name=fname,
            mimetype='text/csv',
        )
    except Exception as e:
        return err500(e)


@app.route('/api/export/pdf', methods=['GET'])
@permission_required('reports.export')
def export_pdf():
    """PDF attendance report using fpdf2."""
    try:
        from fpdf import FPDF
        date_param  = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        dept_filter = request.args.get('department', '')

        logs = database.get_attendance_logs(date_str=date_param)
        if dept_filter:
            logs = [r for r in logs if r.get('department', '') == dept_filter]

        stats = database.get_dashboard_stats()

        pdf = FPDF()
        pdf.add_page()

        pdf.set_fill_color(15, 23, 42)
        pdf.rect(0, 0, 210, 40, 'F')
        pdf.set_font('Helvetica', 'B', 22)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 14, 'DRISHTI AI', ln=True, align='C')
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, 'Smart Campus Attendance Report', ln=True, align='C')
        pdf.ln(4)

        pdf.set_text_color(50, 50, 50)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_xy(10, 48)
        pdf.cell(90, 6, f'Date: {date_param}')
        pdf.cell(90, 6, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True)
        if dept_filter:
            pdf.cell(0, 6, f'Department: {dept_filter}', ln=True)
        pdf.ln(4)

        pdf.set_fill_color(240, 245, 255)
        pdf.set_font('Helvetica', 'B', 10)
        col_w = 46
        for label, val in [
            ('Total Registered', stats['total_registered']),
            ('Present', stats['present_today']),
            ('Late', stats.get('late_today', 0)),
            ('Absent', stats.get('absent_today', 0)),
        ]:
            pdf.set_fill_color(235, 240, 255)
            pdf.cell(col_w, 12, f'{label}\n{val}', border=1, align='C', fill=True)
        pdf.ln(16)

        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 9)
        headers = ['Student ID', 'Name', 'Department', 'Time', 'Status', 'Confidence', 'Liveness']
        widths  = [25,            40,      40,           20,     18,       22,            20]
        for h, w in zip(headers, widths):
            pdf.cell(w, 8, h, border=1, fill=True, align='C')
        pdf.ln()

        pdf.set_font('Helvetica', '', 8)
        status_colors = {
            'Present': (212, 250, 228),
            'Late':    (254, 243, 199),
            'Absent':  (254, 226, 226),
        }
        for row in logs:
            fill_color = status_colors.get(row.get('status', ''), (255, 255, 255))
            pdf.set_fill_color(*fill_color)
            pdf.set_text_color(30, 30, 30)
            vals = [
                row.get('student_id', ''),
                row.get('name', '')[:20],
                row.get('department', '')[:18],
                row.get('time', ''),
                row.get('status', ''),
                f"{row.get('confidence', 0):.1f}%",
                '✓ Pass' if row.get('liveness_passed') else '—',
            ]
            for v, w in zip(vals, widths):
                pdf.cell(w, 7, str(v), border=1, fill=True, align='C')
            pdf.ln()

        pdf.ln(6)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 5, 'Generated by Drishti AI — Smart Campus Attendance Platform', align='C')

        pdf_bytes = pdf.output()
        fname = f'Attendance_Report_{date_param}.pdf'
        database.log_audit(session.get('user_id'), session.get('username', ''),
                           'EXPORT_GENERATED', 'attendance', 'pdf',
                           '', date_param, request.remote_addr)
        return send_file(
            io.BytesIO(bytes(pdf_bytes)),
            as_attachment=True,
            download_name=fname,
            mimetype='application/pdf',
        )
    except Exception as e:
        return err500(e)


# ── Subjects & Classrooms ─────────────────────────────────────────────────────
@app.route('/api/subjects', methods=['GET'])
@login_required
def get_subjects():
    try:
        return jsonify({'success': True, 'subjects': database.get_subjects()})
    except Exception as e:
        return err500(e)


@app.route('/api/classrooms', methods=['GET'])
@login_required
def get_classrooms():
    try:
        return jsonify({'success': True, 'classrooms': database.get_classrooms()})
    except Exception as e:
        return err500(e)


@app.route('/api/departments', methods=['GET'])
@login_required
def get_departments():
    try:
        with database.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM departments ORDER BY name')
            depts = [dict(r) for r in c.fetchall()]
        return jsonify({'success': True, 'departments': depts})
    except Exception as e:
        return err500(e)


@app.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    """Returns all available roles (used by User Management form)."""
    try:
        with database.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM roles ORDER BY name')
            roles = [dict(r) for r in c.fetchall()]
        return jsonify({'success': True, 'roles': roles})
    except Exception as e:
        return err500(e)


# ── SocketIO Events ───────────────────────────────────────────────────────────
@socketio.on('connect')
def on_connect():
    emit('connected', {'status': 'ok', 'message': 'Drishti AI connected'})


@socketio.on('ping_server')
def on_ping():
    emit('pong', {'time': datetime.now().strftime('%H:%M:%S')})


@socketio.on('request_stats')
def on_request_stats():
    try:
        stats = database.get_dashboard_stats()
        emit('stats_update', stats)
    except Exception:
        pass


# ── Demo Mode Seeder ──────────────────────────────────────────────────────────
@app.route('/api/demo/seed', methods=['POST'])
@permission_required('settings.update')
def demo_seed():
    """Seeds demo data for presentation purposes. Only works in DEMO_MODE."""
    if os.environ.get('DEMO_MODE', 'false').lower() != 'true':
        return jsonify({'success': False, 'error': 'Demo mode not enabled'}), 403
    try:
        import random
        from datetime import date

        students = database.get_all_students()
        today    = date.today().isoformat()

        sess_id = database.create_session(
            subject_name='Deep Learning',
            faculty_name='Dr. Demo Faculty',
            classroom_name='LAB-204',
            department='Artificial Intelligence & Data Science',
            semester=5,
            date_str=today,
            start_time='16:00',
            late_threshold_minutes=10,
            created_by='admin',
        )
        database.update_session_status(sess_id, 'completed', '17:00')

        statuses = ['Present', 'Present', 'Present', 'Late', 'Absent']
        for s in students:
            status   = random.choice(statuses)
            time_str = f"16:{random.randint(0,15):02d}:{random.randint(0,59):02d}"
            with database.get_db_connection() as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO attendance
                        (student_id, name, department, date, time, status,
                         confidence, session_id, liveness_passed, face_quality)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'Good')
                ''', (s['student_id'], s['name'], s['department'], today, time_str,
                      status, round(random.uniform(85, 99), 1), sess_id))
                conn.commit()

        database.log_anomaly('duplicate_attempt',
                             'Demo: Repeated recognition attempt detected', sess_id, '', 'low')

        return jsonify({'success': True, 'message': f'Demo data seeded. Session {sess_id} created.'})
    except Exception as e:
        return err500(e)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port  = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    print(f"\n{'='*60}")
    print(f"  DRISHTI AI — Smart Campus Attendance Platform v2.1 (RBAC)")
    print(f"  Running on http://localhost:{port}")
    print(f"  Super Admin: admin / admin123")
    print(f"  Faculty:     faculty / faculty123")
    print(f"{'='*60}\n")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
