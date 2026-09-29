"""
Drishti AI — RBAC (Role-Based Access Control) Module
Centralized permission model, Flask decorators, and data-scope helpers.
Do NOT scatter authorization logic across routes — use these helpers.
"""
from functools import wraps
from flask import session, jsonify, request

# ── Permission Definitions ────────────────────────────────────────────────────
# All available permissions in the system. Adding a new permission only
# requires listing it here and mapping it to one or more roles below.

ALL_PERMISSIONS = [
    # Dashboard
    "dashboard.view",

    # User management (admin-level)
    "users.view",
    "users.create",
    "users.update",
    "users.disable",
    "users.reset_password",
    "users.assign_role",

    # Student management
    "students.view",          # see the student directory
    "students.view_own",      # student can see only themselves
    "students.create",
    "students.update",
    "students.delete",

    # Biometric / enrollment
    "biometric.view",
    "biometric.enroll",
    "biometric.delete",

    # Attendance records
    "attendance.view",        # see any attendance
    "attendance.view_own",    # student sees only own
    "attendance.create",
    "attendance.update",
    "attendance.delete",
    "attendance.export",

    # Attendance sessions
    "sessions.view",
    "sessions.create",
    "sessions.start",
    "sessions.stop",
    "sessions.lock",

    # Live tracking / camera ops
    "tracking.view",
    "tracking.start",
    "tracking.stop",

    # Analytics
    "analytics.view",
    "analytics.view_own",

    # Cameras
    "cameras.view",
    "cameras.manage",

    # Audit logs
    "audit.view",
    "audit.export",

    # Reports / exports
    "reports.view",
    "reports.export",
    "reports.view_own",

    # System settings
    "settings.view",
    "settings.update",
]


# ── Role → Permission Mapping ─────────────────────────────────────────────────
# Central source of truth for what each role can do.
# Use '*' for super_admin to grant all permissions.

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ["*"],   # All permissions — checked via has_permission()

    "department_head": [
        "dashboard.view",
        # User mgmt — read only within department (no assign_role / create)
        "users.view",
        # Students
        "students.view",
        "students.create",
        "students.update",
        "students.delete",
        # Biometric
        "biometric.view",
        "biometric.enroll",
        "biometric.delete",
        # Attendance
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "attendance.delete",
        "attendance.export",
        # Sessions
        "sessions.view",
        "sessions.create",
        "sessions.start",
        "sessions.stop",
        "sessions.lock",
        # Tracking
        "tracking.view",
        # Analytics
        "analytics.view",
        # Cameras
        "cameras.view",
        # Audit — limited
        "audit.view",
        # Reports
        "reports.view",
        "reports.export",
    ],

    "faculty": [
        "dashboard.view",
        # Students — view only
        "students.view",
        # Biometric — view only (no delete)
        "biometric.view",
        "biometric.enroll",
        # Attendance — view + update own sessions
        "attendance.view",
        "attendance.create",
        "attendance.update",
        "attendance.export",
        # Sessions
        "sessions.view",
        "sessions.create",
        "sessions.start",
        "sessions.stop",
        "sessions.lock",
        # Tracking — view
        "tracking.view",
        # Analytics
        "analytics.view",
        # Reports
        "reports.view",
        "reports.export",
    ],

    "attendance_operator": [
        "dashboard.view",
        # Students — view (for recognition display)
        "students.view",
        # Attendance — view only (no manual edit)
        "attendance.view",
        # Sessions — view + start/stop (not create/lock)
        "sessions.view",
        "sessions.start",
        "sessions.stop",
        # Tracking — full control
        "tracking.view",
        "tracking.start",
        "tracking.stop",
        # Cameras — view + manage
        "cameras.view",
        "cameras.manage",
        # Reports — view only
        "reports.view",
    ],

    "student": [
        "dashboard.view",
        "students.view_own",
        "attendance.view_own",
        "analytics.view_own",
        "reports.view_own",
    ],
}


# ── Permission Check Helpers ──────────────────────────────────────────────────

def get_current_user_role() -> str | None:
    """Returns the role of the currently logged-in user, or None."""
    return session.get('role')


def get_current_user_id() -> int | None:
    """Returns the user ID of the currently logged-in user, or None."""
    return session.get('user_id')


def get_current_user_department() -> int | None:
    """Returns the department_id of the currently logged-in user, or None."""
    return session.get('department_id')


def get_current_user_student_id() -> str | None:
    """Returns the linked student_id (for student role users), or None."""
    return session.get('student_id')


def has_permission(permission: str) -> bool:
    """
    Check if the current session user has a specific permission.
    super_admin with '*' always passes.
    """
    if not session.get('user_id'):
        return False
    role = session.get('role', '')
    perms = ROLE_PERMISSIONS.get(role, [])
    if '*' in perms:
        return True
    return permission in perms


def get_user_permissions(role: str) -> list[str]:
    """Return a list of permission strings for a given role."""
    perms = ROLE_PERMISSIONS.get(role, [])
    if '*' in perms:
        return ALL_PERMISSIONS
    return perms


# ── Flask Decorators ──────────────────────────────────────────────────────────

def login_required(f):
    """Decorator: require authenticated session. Returns 401 otherwise."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({
                'success': False,
                'error': 'authentication_required',
                'message': 'Authentication required.',
            }), 401
        return f(*args, **kwargs)
    return decorated


def permission_required(*permissions):
    """
    Decorator factory: require one or more permissions (AND logic).
    Returns 401 if unauthenticated, 403 if lacking permission.

    Usage:
        @permission_required("students.view")
        @permission_required("students.view", "students.update")
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('user_id'):
                _log_unauthorized_access(request.path)
                return jsonify({
                    'success': False,
                    'error': 'authentication_required',
                    'message': 'Authentication required.',
                }), 401

            role = session.get('role', '')
            role_perms = ROLE_PERMISSIONS.get(role, [])
            is_super = '*' in role_perms

            for perm in permissions:
                if not is_super and perm not in role_perms:
                    _log_unauthorized_access(request.path, perm)
                    return jsonify({
                        'success': False,
                        'error': 'permission_denied',
                        'message': 'You do not have permission to perform this action.',
                    }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def role_required(*roles):
    """
    Decorator factory: restrict to specific roles.
    Prefer permission_required() over this where possible.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('user_id'):
                return jsonify({
                    'success': False,
                    'error': 'authentication_required',
                    'message': 'Authentication required.',
                }), 401
            if session.get('role') not in roles:
                _log_unauthorized_access(request.path)
                return jsonify({
                    'success': False,
                    'error': 'permission_denied',
                    'message': 'You do not have permission to perform this action.',
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def _log_unauthorized_access(path: str, permission: str = ''):
    """Internal helper to log unauthorized access attempts."""
    try:
        import database
        database.log_audit(
            user_id=session.get('user_id'),
            username=session.get('username', 'anonymous'),
            action='UNAUTHORIZED_ACCESS',
            entity_type='route',
            entity_id=path,
            old_value=permission,
            new_value='denied',
            ip_address=request.remote_addr or '',
        )
    except Exception:
        pass  # Never let audit logging break the auth flow


# ── Data-Scope Helpers ────────────────────────────────────────────────────────
# These helpers build query filters based on the current user's role.
# Use them inside API endpoints to enforce object-level authorization.

def get_current_user_scope() -> dict:
    """
    Returns a dict describing the current user's data scope.

    Keys:
        scope_type: 'global' | 'department' | 'faculty' | 'student'
        department_id: int | None
        student_id: str | None
        user_id: int | None
    """
    role = session.get('role', '')
    return {
        'role': role,
        'scope_type': _scope_type_for_role(role),
        'department_id': session.get('department_id'),
        'student_id': session.get('student_id'),
        'user_id': session.get('user_id'),
        'username': session.get('username'),
    }


def _scope_type_for_role(role: str) -> str:
    mapping = {
        'super_admin': 'global',
        'department_head': 'department',
        'faculty': 'faculty',
        'attendance_operator': 'operator',
        'student': 'student',
    }
    return mapping.get(role, 'student')


def get_allowed_student_ids(db_conn) -> list[str] | None:
    """
    Returns the list of student IDs the current user may access,
    or None if all students are accessible (super_admin / global).

    Pass a database connection obtained from database.get_db_connection().
    """
    scope = get_current_user_scope()

    if scope['scope_type'] == 'global':
        return None  # No restriction

    if scope['scope_type'] == 'student':
        sid = scope['student_id']
        return [sid] if sid else []

    if scope['scope_type'] == 'department':
        dept_id = scope['department_id']
        if not dept_id:
            return []
        c = db_conn.cursor()
        # department in students is stored as a text name, join via departments
        c.execute('''
            SELECT s.student_id FROM students s
            JOIN departments d ON d.name = s.department
            WHERE d.id = ?
        ''', (dept_id,))
        return [r['student_id'] for r in c.fetchall()]

    if scope['scope_type'] == 'faculty':
        # Faculty can see students in sessions they created
        user_id = scope['user_id']
        username = scope['username']
        if not username:
            return []
        c = db_conn.cursor()
        c.execute('''
            SELECT DISTINCT a.student_id
            FROM attendance a
            JOIN attendance_sessions s ON s.id = a.session_id
            WHERE s.created_by = ?
        ''', (username,))
        rows = c.fetchall()
        return [r['student_id'] for r in rows] if rows else []

    if scope['scope_type'] == 'operator':
        # Operators can see all students (for recognition UI), but limited edit
        return None

    return []


def get_allowed_session_ids(db_conn) -> list[int] | None:
    """
    Returns allowed session IDs or None for unrestricted access.
    """
    scope = get_current_user_scope()

    if scope['scope_type'] == 'global':
        return None

    if scope['scope_type'] == 'department':
        dept_id = scope['department_id']
        if not dept_id:
            return []
        c = db_conn.cursor()
        c.execute('''
            SELECT s.id FROM attendance_sessions s
            JOIN departments d ON d.name = s.department
            WHERE d.id = ?
        ''', (dept_id,))
        return [r['id'] for r in c.fetchall()]

    if scope['scope_type'] in ('faculty', 'operator'):
        username = scope['username']
        if not username:
            return []
        c = db_conn.cursor()
        c.execute('SELECT id FROM attendance_sessions WHERE created_by = ?', (username,))
        return [r['id'] for r in c.fetchall()]

    if scope['scope_type'] == 'student':
        return []  # Students can't manage sessions

    return []


def can_modify_attendance_record(record: dict) -> bool:
    """
    Check if the current user may modify a specific attendance record.
    record: dict with at least 'session_id' and 'student_id'.
    """
    role = session.get('role', '')
    if role == 'super_admin':
        return True
    if role in ('student', 'attendance_operator'):
        return False

    import database
    # Check if session is locked
    sess = database.get_session(record.get('session_id'))
    if sess and sess.get('status') == 'locked':
        if role != 'super_admin':
            return False

    if role == 'department_head':
        dept_id = session.get('department_id')
        if not dept_id:
            return False
        with database.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT s.department FROM students s WHERE s.student_id = ?
            ''', (record.get('student_id', ''),))
            row = c.fetchone()
            if not row:
                return False
            c.execute('SELECT id FROM departments WHERE name = ?', (row['department'],))
            dept_row = c.fetchone()
            return dept_row and dept_row['id'] == dept_id

    if role == 'faculty':
        username = session.get('username', '')
        if not username:
            return False
        import database
        sess = database.get_session(record.get('session_id'))
        return sess and sess.get('created_by') == username

    return False


def is_super_admin() -> bool:
    """Convenience check for super_admin role."""
    return session.get('role') == 'super_admin'
