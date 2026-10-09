/*
  Drishti AI — Frontend Application Logic v2.0
  Handles API communication, SocketIO real-time updates, Chart.js, and DOM manipulation.
*/

// --- Global State ---
let socket = null;
let currentSessionId = null;
let charts = {};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Check Authentication
    const auth = await fetchAPI('/auth/me');
    if (!auth || !auth.authenticated) {
        window.location.href = '/login';
        return;
    }

    // Set User info & RBAC
    window.userPermissions = auth.user.permissions || [];
    window.userRole = auth.user.role;
    window.userId = auth.user.id;
    window.studentId = auth.user.student_id;

    document.getElementById('sidebar-username').textContent = auth.user.full_name || auth.user.username;

    const roleBadge = document.getElementById('sidebar-role-badge');
    if (roleBadge) {
        roleBadge.textContent = auth.user.role.replace('_', ' ');
    }

    // Initialize RBAC UI Elements
    applyRBAC();

    // 2. Initialize SocketIO
    initSocketIO();

    // 3. Update Date Badge
    const dateOpts = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
    document.getElementById('current-date').textContent = new Date().toLocaleDateString('en-US', dateOpts);
    document.getElementById('date-filter').valueAsDate = new Date();

    // 4. Load Initial Data
    fetchStats();
    fetchInsights();
    fetchNotifications();

    // 5. Populate Dropdowns (for sessions/enrollment)
    loadDropdowns();
});

// --- Tab Switching ---
function switchTab(tabId) {
    // Update nav classes
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById(`nav-${tabId}`).classList.add('active');

    // Update views
    document.querySelectorAll('.view-section').forEach(el => {
        el.classList.add('hidden');
        el.classList.remove('active');
    });
    const target = document.getElementById(tabId);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    // Trigger specific data loads based on tab
    if (tabId === 'dashboard') fetchStats();
    if (tabId === 'sessions') loadSessionsTab();
    if (tabId === 'students') fetchStudents();
    if (tabId === 'analytics') loadAnalytics();
    if (tabId === 'cameras') fetchCameras();
    if (tabId === 'attendance') loadLiveTrackingTab();
    if (tabId === 'myattendance') loadMyAttendance();
    if (tabId === 'users') fetchUsers();
    if (tabId === 'audit') fetchAuditLogs();
}

// --- RBAC Helpers ---
function hasPermission(perm) {
    if (!window.userPermissions) return false;
    if (window.userPermissions.includes('*')) return true;
    return window.userPermissions.includes(perm);
}

function applyRBAC() {
    // Show/hide nav items
    document.querySelectorAll('.rbac-nav').forEach(el => {
        const reqPerm = el.getAttribute('data-permission');
        if (reqPerm && hasPermission(reqPerm)) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    });
}

function closeAccessDenied() {
    document.getElementById('access-denied-modal').classList.add('hidden');
}

// --- Global Error Boundary ---
window.addEventListener('error', (event) => {
    console.error('Global Error Boundary Caught:', event.error);
    showToast('System Error', 'An unexpected UI error occurred. Degraded gracefully.', 'error');
    // Prevent full app crash, gracefully degrade
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled Promise Rejection:', event.reason);
    showToast('Network Error', 'A network request failed. Please check your connection.', 'error');
});

// --- SocketIO Integration ---
function initSocketIO() {
    socket = io();

    socket.on('connect', () => {
        document.getElementById('system-dot').className = 'status-dot online';
        document.getElementById('system-status-text').textContent = 'System Connected';
        if (document.getElementById('ws-health-status')) {
            document.getElementById('ws-health-status').textContent = 'Connected';
            document.getElementById('ws-health-status').className = 'health-status online';
        }
    });

    socket.on('disconnect', () => {
        document.getElementById('system-dot').className = 'status-dot error';
        document.getElementById('system-status-text').textContent = 'Disconnected';
        if (document.getElementById('ws-health-status')) {
            document.getElementById('ws-health-status').textContent = 'Disconnected';
            document.getElementById('ws-health-status').className = 'health-status error';
        }
    });

    // Real-time Dashboard Updates
    socket.on('stats_update', (stats) => {
        updateStatsUI(stats);
    });

    // Attendance Marked Event
    socket.on('attendance_marked', (data) => {
        // Add to activity feed on dashboard
        addActivityFeedItem(data);

        // Add to live tracking if active
        if (!document.getElementById('attendance').classList.contains('hidden')) {
            addRecognitionEvent(data);
        }

        // Refresh stats silently
        if (!document.getElementById('dashboard').classList.contains('hidden')) {
            socket.emit('request_stats');
            fetchLogsByDate(); // Refresh table
        }
    });

    // Camera Stats
    socket.on('camera_stats', (stats) => {
        document.getElementById('cam-fps').textContent = stats.fps.toFixed(1);
        document.getElementById('cam-latency').textContent = stats.latency_ms + 'ms';
        document.getElementById('cam-faces').textContent = stats.faces_detected;
        document.getElementById('cam-recognized').textContent = stats.recognized;
        document.getElementById('cam-unknown').textContent = stats.unknown;
        document.getElementById('cam-liveness').textContent = stats.liveness_passed;

        const dot = document.getElementById('cam-status-dot');
        const txt = document.getElementById('cam-status-text');
        if (stats.fps > 0) {
            dot.className = 'status-dot online';
            txt.textContent = 'ONLINE';
        } else {
            dot.className = 'status-dot error';
            txt.textContent = 'ERROR';
        }
    });

    // Session Events
    socket.on('session_started', (data) => {
        showToast('Session Active', `${data.subject} started by ${data.faculty}`, 'info');
        if (!document.getElementById('dashboard').classList.contains('hidden')) fetchStats();
        if (!document.getElementById('sessions').classList.contains('hidden')) loadSessionsTab();
    });

    socket.on('session_stopped', (data) => {
        showToast('Session Ended', `${data.present}/${data.total} attended.`, 'success');
        if (!document.getElementById('dashboard').classList.contains('hidden')) fetchStats();
        if (!document.getElementById('sessions').classList.contains('hidden')) loadSessionsTab();

        // Reset tracking UI if it was this session
        if (currentSessionId == data.session_id) {
            stopTrackingUI();
        }
    });

    // Anomaly Events
    socket.on('anomaly_detected', (data) => {
        addAnomalyAlert(data);
        fetchNotifications();
    });
}

// --- API Helpers ---
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

async function fetchAPI(endpoint, options = {}) {
    try {
        if (!options.headers) options.headers = {};

        // Add CSRF token for mutations
        if (options.method && !['GET', 'HEAD', 'OPTIONS'].includes(options.method.toUpperCase())) {
            const csrfToken = getCookie('csrf_token');
            if (csrfToken) {
                options.headers['X-CSRFToken'] = csrfToken;
            }
        }

        const res = await fetch(endpoint, options);
        if (res.status === 401 && endpoint !== '/auth/me') {
            window.location.href = '/login';
            return { success: false, error: 'Unauthorized' };
        }
        if (res.status === 403) {
            document.getElementById('access-denied-modal')?.classList.remove('hidden');
            return { success: false, error: 'Access Denied' };
        }
        if (!res.ok) {
            // Graceful fallback for API 500s or 404s
            let errMsg = 'API Error';
            try {
                const errData = await res.json();
                errMsg = errData.message || errData.error || errMsg;
            } catch (e) { }
            console.warn(`[fetchAPI] Non-OK response from ${endpoint}:`, errMsg);
            return { success: false, error: errMsg };
        }
        return await res.json();
    } catch (e) {
        console.error('API Error:', e);
        return { success: false, error: 'Network error or server unreachable. Operating in offline/fallback mode if possible.' };
    }
}

function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'ph-info';
    if (type === 'success') icon = 'ph-check-circle toast-success-icon';
    if (type === 'error') icon = 'ph-x-circle toast-error-icon';
    if (type === 'warning') icon = 'ph-warning-circle';

    toast.innerHTML = `
        <i class="ph ${icon}"></i>
        <div>
            <strong>${title}</strong>
            <p style="margin:0; font-size:12px; opacity:0.8">${message}</p>
        </div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- Dashboard ---
async function fetchStats() {
    const data = await fetchAPI('/api/stats');
    if (!data || !data.success) return;

    updateStatsUI(data);
    renderAttendanceTable(data.attendance);
    renderTodaySessions(data.today_sessions);

    // Notifications count
    updateNotifBadge(data.unread_notifications);
}

function updateStatsUI(stats) {
    document.querySelectorAll('.skeleton-card').forEach(el => el.classList.remove('skeleton-card'));

    document.getElementById('stat-registered').textContent = stats.total_registered;
    document.getElementById('stat-present').textContent = stats.present_today;
    document.getElementById('stat-late').textContent = stats.late_today || 0;
    document.getElementById('stat-absent').textContent = stats.absent_today || 0;
    document.getElementById('stat-rate').textContent = `${stats.attendance_rate}%`;
    document.getElementById('stat-sessions').textContent = stats.active_sessions || 0;

    const badge = document.getElementById('active-sessions-badge');
    if (stats.active_sessions > 0) {
        badge.textContent = stats.active_sessions;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

async function fetchInsights() {
    const data = await fetchAPI('/api/analytics/insights');
    if (!data || !data.success) return;

    const list = document.getElementById('insights-list');
    list.innerHTML = '';

    data.insights.forEach(insight => {
        const div = document.createElement('div');
        div.className = `insight-card ${insight.type}`;
        div.innerHTML = `
            <i class="ph ph-${insight.icon} insight-icon"></i>
            <div>${insight.text}</div>
        `;
        list.appendChild(div);
    });
}

function addActivityFeedItem(event) {
    const feed = document.getElementById('activity-feed');
    // Remove empty state
    const empty = feed.querySelector('.empty-state-sm');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'activity-item';

    let iconClass = 'ph-check';
    let iconBg = 'rgba(16,185,129,0.1)';
    let iconCol = 'var(--emerald)';

    if (event.status === 'Late') {
        iconClass = 'ph-clock';
        iconBg = 'rgba(245,158,11,0.1)';
        iconCol = 'var(--amber)';
    }

    div.innerHTML = `
        <div class="activity-icon" style="background:${iconBg}; color:${iconCol}">
            <i class="ph ${iconClass}"></i>
        </div>
        <div class="activity-content">
            <h4>${event.name}</h4>
            <p>${event.department} — Conf: ${event.confidence}%</p>
        </div>
        <div class="activity-time">${event.time}</div>
    `;

    feed.prepend(div);
    if (feed.children.length > 20) feed.lastChild.remove();
}

function addAnomalyAlert(anomaly) {
    const list = document.getElementById('anomaly-list');
    const empty = list.querySelector('.empty-state-sm');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = `anomaly-item ${anomaly.severity}`;
    div.innerHTML = `
        <strong>${anomaly.type.replace('_', ' ').toUpperCase()}</strong><br>
        <span style="opacity:0.8">${anomaly.description}</span>
        <div style="font-size:10px; margin-top:4px; opacity:0.6">${anomaly.time}</div>
    `;

    list.prepend(div);

    const countEl = document.getElementById('anomaly-count');
    countEl.textContent = parseInt(countEl.textContent) + 1;
    countEl.classList.add('red-badge');
}

// --- Attendance Table ---
async function fetchLogsByDate() {
    const d = document.getElementById('date-filter').value;
    const data = await fetchAPI(`/api/attendance?date=${d}`);
    if (data && data.success) {
        renderAttendanceTable(data.attendance);
    }
}

function renderAttendanceTable(logs) {
    const tbody = document.getElementById('attendance-tbody');
    tbody.innerHTML = '';

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:30px;">
            <div class="empty-state-sm"><i class="ph ph-folder-dashed"></i><p>No records found</p></div>
        </td></tr>`;
        return;
    }

    logs.forEach(log => {
        let badgeClass = 'scheduled';
        if (log.status === 'Present') badgeClass = 'present';
        if (log.status === 'Late') badgeClass = 'late';
        if (log.status === 'Absent') badgeClass = 'absent';
        if (log.status === 'Excused' || log.status === 'HalfDay') badgeClass = 'excused';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-family:monospace">${log.student_id}</td>
            <td><strong>${log.name}</strong></td>
            <td>${log.department || '—'}</td>
            <td>${log.time || '—'}</td>
            <td><span class="badge ${badgeClass}">${log.status}</span></td>
            <td>${log.confidence > 0 ? log.confidence.toFixed(1) + '%' : '—'}</td>
            <td>${log.liveness_passed ? '<span style="color:var(--emerald)"><i class="ph ph-check"></i> Pass</span>' : '<span style="color:var(--rose)">Fail</span>'}</td>
            <td>${log.face_quality}</td>
            <td>
                <button class="btn-icon" onclick="openOverrideModal(${log.id}, '${log.status}')" title="Edit/Override">
                    <i class="ph ph-pencil-simple"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterLogsTable() {
    const term = document.getElementById('log-search').value.toLowerCase();
    const rows = document.getElementById('attendance-tbody').querySelectorAll('tr');

    rows.forEach(row => {
        if (row.cells.length < 2) return;
        const text = row.cells[0].textContent.toLowerCase() + ' ' + row.cells[1].textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
    });
}

// --- Sessions ---
async function loadSessionsTab() {
    const data = await fetchAPI('/api/sessions');
    if (data && data.success) {
        renderSessionsGrid(data.sessions);
    }
}

function renderTodaySessions(sessions) {
    const list = document.getElementById('today-sessions-list');
    list.innerHTML = '';

    if (!sessions || sessions.length === 0) {
        list.innerHTML = `<div class="empty-state-sm"><i class="ph ph-calendar-slash"></i><p>No sessions scheduled today</p></div>`;
        return;
    }

    sessions.forEach(s => {
        const div = document.createElement('div');
        div.className = 'session-card';
        div.style.marginBottom = '12px';
        div.innerHTML = `
            <div class="sess-header">
                <div>
                    <div class="sess-title">${s.subject_name}</div>
                    <div class="sess-meta"><i class="ph ph-user"></i> ${s.faculty_name}</div>
                </div>
                <span class="badge ${s.status}">${s.status.toUpperCase()}</span>
            </div>
            <div style="font-size:12px; display:flex; gap:16px;">
                <span><i class="ph ph-clock"></i> ${s.start_time} ${s.end_time ? '- ' + s.end_time : ''}</span>
                <span><i class="ph ph-map-pin"></i> ${s.classroom_name}</span>
            </div>
        `;
        list.appendChild(div);
    });
}

function renderSessionsGrid(sessions) {
    const grid = document.getElementById('sessions-grid');
    grid.innerHTML = '';
    let activeSessionFound = false;

    if (!sessions || sessions.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1" class="empty-state-sm"><i class="ph ph-calendar-slash"></i><p>No sessions found</p></div>`;
        return;
    }

    sessions.forEach(s => {
        if (s.status === 'active') {
            activeSessionFound = true;
            currentSessionId = s.id;
            document.getElementById('active-session-banner').classList.remove('hidden');
            document.getElementById('active-sess-name').textContent = s.subject_name;
            document.getElementById('active-sess-time').textContent = `Started at ${s.start_time} | ${s.faculty_name}`;
        }

        const div = document.createElement('div');
        div.className = 'session-card glass-panel';

        let actionBtn = '';
        if (s.status === 'scheduled') {
            actionBtn = `<button class="btn-primary" onclick="startSession(${s.id})"><i class="ph ph-play"></i> Start</button>`;
        } else if (s.status === 'active') {
            actionBtn = `<button class="btn-danger" onclick="stopSession(${s.id})"><i class="ph ph-stop"></i> Stop</button>`;
        } else if (s.status === 'completed') {
            actionBtn = `<button class="btn-secondary" onclick="lockSession(${s.id})"><i class="ph ph-lock"></i> Lock</button>`;
        }

        div.innerHTML = `
            <div class="sess-header">
                <div class="sess-title">${s.subject_name}</div>
                <span class="badge ${s.status}">${s.status.toUpperCase()}</span>
            </div>
            <div class="sess-meta"><i class="ph ph-user"></i> ${s.faculty_name}</div>
            <div class="sess-meta"><i class="ph ph-map-pin"></i> ${s.classroom_name} | ${s.department}</div>
            <div class="sess-meta"><i class="ph ph-calendar"></i> ${s.date} <i class="ph ph-clock" style="margin-left:8px;"></i> ${s.start_time} ${s.end_time ? '- ' + s.end_time : ''}</div>
            <div class="sess-footer">
                <span style="font-size:11px; color:var(--text-muted)">Created by ${s.created_by}</span>
                ${actionBtn}
            </div>
        `;
        grid.appendChild(div);
    });

    if (!activeSessionFound) {
        document.getElementById('active-session-banner').classList.add('hidden');
        currentSessionId = null;
    }
}

function openSessionModal() { document.getElementById('session-modal').classList.remove('hidden'); }
function closeSessionModal() { document.getElementById('session-modal').classList.add('hidden'); }

async function handleCreateSession(e) {
    e.preventDefault();
    const payload = {
        subject_name: document.getElementById('sess-subject').value,
        faculty_name: document.getElementById('sess-faculty').value,
        classroom_name: document.getElementById('sess-classroom').value,
        department: document.getElementById('sess-dept').value,
        date: document.getElementById('sess-date').value,
        start_time: document.getElementById('sess-time').value,
        semester: document.getElementById('sess-semester').value,
        late_threshold_minutes: document.getElementById('sess-late').value,
        camera_id: document.getElementById('sess-camera').value,
    };

    const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
        showToast('Success', 'Session created successfully', 'success');
        closeSessionModal();
        loadSessionsTab();
    } else {
        showToast('Error', data.error, 'error');
    }
}

async function startSession(id) {
    const data = await fetchAPI(`/api/sessions/${id}/start`, { method: 'POST' });
    if (data && data.success) {
        loadSessionsTab();
    } else {
        showToast('Error', data?.error || 'Failed to start', 'error');
    }
}

async function stopSession(id) {
    const data = await fetchAPI(`/api/sessions/${id}/stop`, { method: 'POST' });
    if (data && data.success) {
        loadSessionsTab();
    } else {
        showToast('Error', data?.error || 'Failed to stop', 'error');
    }
}
function stopCurrentSession() {
    if (currentSessionId) stopSession(currentSessionId);
}

async function lockSession(id) {
    if (!confirm('Locking a session prevents further attendance marking. Continue?')) return;
    const data = await fetchAPI(`/api/sessions/${id}/lock`, { method: 'POST' });
    if (data && data.success) loadSessionsTab();
}


// --- Students Directory ---
async function fetchStudents() {
    const data = await fetchAPI('/api/students');
    if (data && data.success) {
        // Populate dept filter
        const depts = new Set(data.students.map(s => s.department).filter(Boolean));
        const sel = document.getElementById('dept-filter');
        sel.innerHTML = '<option value="">All Departments</option>';
        depts.forEach(d => {
            sel.innerHTML += `<option value="${d}">${d}</option>`;
        });

        window._allStudents = data.students;
        renderStudentsGrid(data.students);
    }
}

function renderStudentsGrid(students) {
    const grid = document.getElementById('students-grid');
    grid.innerHTML = '';

    students.forEach(s => {
        const div = document.createElement('div');
        div.className = 'student-card';
        div.onclick = () => openStudentModal(s.student_id);

        // Initial fallback
        let avatarStr = s.name.charAt(0);

        div.innerHTML = `
            <div class="student-avatar">${avatarStr}</div>
            <div class="student-info">
                <h3>${s.name}</h3>
                <p>${s.student_id} | Sem ${s.semester}</p>
                <p>${s.department}</p>
                <div class="embed-badge"><i class="ph ph-scan"></i> Enrolled</div>
            </div>
        `;
        grid.appendChild(div);
    });
}

function filterStudents() {
    const term = document.getElementById('student-search').value.toLowerCase();
    const dept = document.getElementById('dept-filter').value;

    if (!window._allStudents) return;

    const filtered = window._allStudents.filter(s => {
        const matchName = s.name.toLowerCase().includes(term) || s.student_id.toLowerCase().includes(term);
        const matchDept = dept === '' || s.department === dept;
        return matchName && matchDept;
    });

    renderStudentsGrid(filtered);
}

async function loadMyAttendance() {
    if (!window.studentId) {
        document.getElementById('myattendance').innerHTML = '<div class="empty-state-sm"><i class="ph ph-warning-circle"></i><p>No student ID linked to this account.</p></div>';
        return;
    }
    const content = document.getElementById('myattendance');
    content.innerHTML = '<div class="empty-state-sm"><i class="ph ph-spinner-gap"></i><p>Loading...</p></div>';

    const data = await fetchAPI(`/api/students/${window.studentId}/analytics`);
    if (!data || !data.success) {
        content.innerHTML = '<p class="text-danger">Failed to load student data.</p>';
        return;
    }

    let riskColor = 'var(--emerald)';
    if (data.risk === 'MEDIUM') riskColor = 'var(--amber)';
    if (data.risk === 'HIGH') riskColor = 'var(--rose)';

    let historyHtml = '';
    data.history.forEach(h => {
        historyHtml += `
            <tr>
                <td>${h.date}</td>
                <td>${h.subject_name || 'Global'}</td>
                <td><span class="badge ${h.status.toLowerCase()}">${h.status}</span></td>
            </tr>
        `;
    });

    content.innerHTML = `
        <header class="section-header">
            <div>
                <h1>My Attendance Profile</h1>
                <p>${data.student.name} | ${data.student.student_id} | ${data.student.department} (Sem ${data.student.semester})</p>
            </div>
        </header>

        <div class="analytics-kpi" style="grid-template-columns: repeat(3, 1fr); margin-top:24px;">
            <div class="metric-card glass-panel" style="padding:20px; flex-direction:column; align-items:flex-start; gap:12px;">
                <p style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Attendance Rate</p>
                <h3 style="font-size:32px; color:${riskColor}">${data.attendance_rate}%</h3>
            </div>
            <div class="metric-card glass-panel" style="padding:20px; flex-direction:column; align-items:flex-start; gap:12px;">
                <p style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Risk Level</p>
                <h3 style="font-size:24px; color:${riskColor}">${data.risk}</h3>
            </div>
            <div class="metric-card glass-panel" style="padding:20px; flex-direction:column; align-items:flex-start; gap:12px;">
                <p style="font-size:12px; color:var(--text-muted); text-transform:uppercase;">Biometric Status</p>
                <h3 style="font-size:24px;">${data.embeddings_stored > 0 ? '<span class="badge active"><i class="ph ph-check-circle"></i> Enrolled</span>' : '<span class="badge missed"><i class="ph ph-warning"></i> Not Enrolled</span>'}</h3>
            </div>
        </div>
        
        <h3 style="margin:32px 0 16px;">Recent Attendance History</h3>
        <div class="table-container glass-panel">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Session / Subject</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${historyHtml || '<tr><td colspan="3" style="text-align:center">No attendance records found</td></tr>'}
                </tbody>
            </table>
        </div>
    `;
}

async function openStudentModal(sid) {
    const modal = document.getElementById('student-modal');
    const content = document.getElementById('modal-content');
    content.innerHTML = '<div class="empty-state-sm"><i class="ph ph-spinner-gap"></i><p>Loading...</p></div>';
    modal.classList.remove('hidden');

    const data = await fetchAPI(`/api/students/${sid}/analytics`);
    if (!data || !data.success) {
        content.innerHTML = '<p class="text-danger">Failed to load student data.</p>';
        return;
    }

    document.getElementById('modal-student-name').textContent = data.student.name;

    let riskColor = 'var(--emerald)';
    if (data.risk === 'MEDIUM') riskColor = 'var(--amber)';
    if (data.risk === 'HIGH') riskColor = 'var(--rose)';

    let historyHtml = '';
    data.history.forEach(h => {
        historyHtml += `
            <tr>
                <td>${h.date}</td>
                <td>${h.subject_name || 'Global'}</td>
                <td><span class="badge ${h.status.toLowerCase()}">${h.status}</span></td>
            </tr>
        `;
    });

    content.innerHTML = `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:24px;">
            <div>
                <p class="text-muted" style="font-size:12px; margin-bottom:4px;">Student ID</p>
                <div style="font-family:monospace; font-size:16px;">${data.student.student_id}</div>
            </div>
            <div>
                <p class="text-muted" style="font-size:12px; margin-bottom:4px;">Department</p>
                <div style="font-size:14px;">${data.student.department} (Sem ${data.student.semester})</div>
            </div>
        </div>
        
        <div class="analytics-kpi" style="grid-template-columns: repeat(3, 1fr);">
            <div class="metric-card glass-panel" style="padding:12px; flex-direction:column; align-items:flex-start; gap:8px;">
                <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Attendance Rate</p>
                <h3 style="font-size:24px; color:${riskColor}">${data.attendance_rate}%</h3>
            </div>
            <div class="metric-card glass-panel" style="padding:12px; flex-direction:column; align-items:flex-start; gap:8px;">
                <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Risk Level</p>
                <h3 style="font-size:18px; color:${riskColor}">${data.risk}</h3>
            </div>
            <div class="metric-card glass-panel" style="padding:12px; flex-direction:column; align-items:flex-start; gap:8px;">
                <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Embeddings</p>
                <h3 style="font-size:24px;">${data.embeddings_stored}/5</h3>
            </div>
        </div>
        
        <h4 style="margin:20px 0 10px;">Recent Attendance</h4>
        <div class="table-scroll" style="max-height:200px;">
            <table class="premium-table">
                <thead><tr><th>Date</th><th>Session</th><th>Status</th></tr></thead>
                <tbody>${historyHtml || '<tr><td colspan="3">No history</td></tr>'}</tbody>
            </table>
        </div>
        
        <div style="margin-top:24px; text-align:right;">
            <button class="btn-danger" onclick="deleteStudent('${data.student.student_id}')">
                <i class="ph ph-trash"></i> Remove Student
            </button>
        </div>
    `;
}
function closeStudentModal() { document.getElementById('student-modal').classList.add('hidden'); }

async function deleteStudent(sid) {
    if (!confirm('Are you sure? This will delete the student, all their biometric data, and attendance records.')) return;

    const res = await fetch('/api/students/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: sid })
    });
    const data = await res.json();
    if (data.success) {
        showToast('Deleted', data.message, 'success');
        closeStudentModal();
        fetchStudents();
    }
}


// --- Multi-Angle Enrollment ---
async function handleRegister(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-register');
    const btnText = document.getElementById('btn-register-text');

    const payload = {
        name: document.getElementById('student-name').value,
        sid: document.getElementById('student-id').value,
        department: document.getElementById('student-dept').value,
        semester: document.getElementById('student-sem').value,
        email: document.getElementById('student-email').value,
    };

    if (!document.getElementById('consent-check').checked) {
        showToast('Error', 'Consent is required', 'error');
        return;
    }

    btn.disabled = true;
    btnText.textContent = 'Camera Window Opened...';

    // Reset steps UI
    document.querySelectorAll('.step-item').forEach(el => {
        el.classList.remove('done'); el.classList.remove('active');
    });
    document.getElementById('step-2').classList.add('active');

    try {
        const headers = { 'Content-Type': 'application/json' };
        const csrfToken = getCookie('csrf_token');
        if (csrfToken) headers['X-CSRFToken'] = csrfToken;

        const res = await fetch('/api/register', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            document.querySelectorAll('.step-item').forEach(el => el.classList.add('done'));
            showToast('Success', data.message, 'success');
            e.target.reset();
        } else {
            showToast('Error', data.error, 'error');
            document.getElementById('step-1').classList.add('active');
        }
    } catch (err) {
        showToast('Error', 'Connection failed', 'error');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Capture Face & Enroll';
    }
}


// --- Live Tracking ---
async function loadLiveTrackingTab() {
    // Populate session select
    const data = await fetchAPI('/api/sessions?date=' + new Date().toISOString().split('T')[0]);
    if (data && data.success) {
        const sel = document.getElementById('session-select');
        sel.innerHTML = '<option value="">— Select Session (optional) —</option>';
        data.sessions.forEach(s => {
            if (s.status === 'scheduled' || s.status === 'active') {
                sel.innerHTML += `<option value="${s.id}">${s.subject_name} (${s.start_time})</option>`;
                if (s.status === 'active') sel.value = s.id;
            }
        });
    }
}

async function startAttendance() {
    const sessId = document.getElementById('session-select').value;

    document.getElementById('btn-start-attendance').disabled = true;

    let url = '/api/start_attendance'; // legacy global mode
    if (sessId) {
        url = `/api/sessions/${sessId}/start`; // session-bound mode
    }

    const data = await fetchAPI(url, { method: 'POST' });
    if (data && data.success) {
        startTrackingUI();
    } else {
        showToast('Error', data?.error || 'Failed to start camera', 'error');
        document.getElementById('btn-start-attendance').disabled = false;
    }
}

function startTrackingUI() {
    document.getElementById('camera-offline').classList.add('hidden');
    document.getElementById('camera-live').classList.remove('hidden');

    // Start MJPEG stream
    const img = document.getElementById('camera-stream');
    img.src = '/api/camera/stream?' + new Date().getTime(); // cache bust
}

async function stopAttendanceSession() {
    const sessId = document.getElementById('session-select').value;
    if (sessId) {
        await fetchAPI(`/api/sessions/${sessId}/stop`, { method: 'POST' });
    }
    stopTrackingUI();
}

function stopTrackingUI() {
    document.getElementById('camera-offline').classList.remove('hidden');
    document.getElementById('camera-live').classList.add('hidden');
    document.getElementById('btn-start-attendance').disabled = false;
    document.getElementById('camera-stream').src = '';

    // Reset stats
    document.getElementById('cam-status-dot').className = 'status-dot offline';
    document.getElementById('cam-status-text').textContent = 'OFFLINE';
    document.getElementById('cam-fps').textContent = '0';
    document.getElementById('cam-faces').textContent = '0';
}

function addRecognitionEvent(data) {
    const list = document.getElementById('recognition-events');
    const empty = list.querySelector('.empty-state-sm');
    if (empty) empty.remove();

    const div = document.createElement('div');

    let typeClass = 'success';
    if (data.status === 'Late') typeClass = 'warning';
    if (data.name === 'Unknown') typeClass = 'error';

    div.className = `rec-event-card ${typeClass}`;

    div.innerHTML = `
        <div class="rec-avatar">${data.name.charAt(0)}</div>
        <div class="rec-info">
            <h4>${data.name}</h4>
            <p>${data.department} | ${data.student_id || '---'}</p>
        </div>
        <div class="rec-meta">
            <span class="score">${data.confidence.toFixed(1)}%</span>
            <span class="time">${data.time}</span>
        </div>
    `;

    list.prepend(div);
    if (list.children.length > 50) list.lastChild.remove();
}


// --- Analytics ---
async function loadAnalytics() {
    const days = document.getElementById('analytics-range').value;

    const overview = await fetchAPI('/api/analytics/overview');
    if (!overview || !overview.success) return;

    // KPI
    const kpi = document.getElementById('analytics-kpi');
    kpi.innerHTML = `
        <div class="metric-card glass-panel" style="flex-direction:column; align-items:flex-start; padding:16px; gap:8px;">
            <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Platform Avg</p>
            <h3 style="font-size:24px;">${overview.stats.attendance_rate}%</h3>
        </div>
        <div class="metric-card glass-panel" style="flex-direction:column; align-items:flex-start; padding:16px; gap:8px;">
            <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Active Students</p>
            <h3 style="font-size:24px;">${overview.stats.total_registered}</h3>
        </div>
        <div class="metric-card glass-panel" style="flex-direction:column; align-items:flex-start; padding:16px; gap:8px;">
            <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Total Sessions</p>
            <h3 style="font-size:24px;">${overview.today_sessions?.length || 0} (Today)</h3>
        </div>
        <div class="metric-card glass-panel" style="flex-direction:column; align-items:flex-start; padding:16px; gap:8px;">
            <p style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">At Risk</p>
            <h3 style="font-size:24px; color:var(--rose)">${overview.stats.at_risk_count}</h3>
        </div>
    `;

    // Draw Charts
    drawTrendChart(overview.trends);
    drawDeptChart(overview.department_stats);

    // Draw Heatmap
    const heatmapRes = await fetchAPI('/api/analytics/heatmap?months=3');
    if (heatmapRes && heatmapRes.success) {
        drawHeatmap(heatmapRes.heatmap);
    }

    // Risk Table
    const rtbody = document.getElementById('risk-tbody');
    rtbody.innerHTML = '';
    overview.at_risk.forEach(r => {
        rtbody.innerHTML += `
            <tr>
                <td><strong>${r.name}</strong><br><span class="text-muted" style="font-size:11px">${r.student_id}</span></td>
                <td>${r.department}</td>
                <td>${r.total_sessions}</td>
                <td>${r.attended}</td>
                <td><strong style="color:var(--rose)">${r.rate}%</strong></td>
                <td><span class="badge absent">HIGH RISK</span></td>
                <td>
                    <button class="btn-secondary" style="padding:6px" onclick="openStudentModal('${r.student_id}')">
                        View
                    </button>
                </td>
            </tr>
        `;
    });
}

function drawTrendChart(data) {
    if (charts.trend) charts.trend.destroy();
    const ctx = document.getElementById('trend-chart').getContext('2d');

    const labels = data.map(d => d.date.split('-').slice(1).join('/'));
    const vals = data.map(d => {
        return d.total_marked > 0 ? (d.attended / d.total_marked * 100).toFixed(1) : 0;
    });

    charts.trend = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Attendance %',
                data: vals,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });
}

function drawDeptChart(data) {
    if (charts.dept) charts.dept.destroy();
    const ctx = document.getElementById('dept-chart').getContext('2d');

    const labels = data.map(d => d.department.substring(0, 15));
    const vals = data.map(d => d.rate);

    charts.dept = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Avg Rate %',
                data: vals,
                backgroundColor: '#a855f7',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } }
            }
        }
    });
}

function drawHeatmap(data) {
    const container = document.getElementById('heatmap-container');
    container.innerHTML = '';

    // Fill 90 days grid
    const today = new Date();
    const days = 90;

    const dataMap = {};
    data.forEach(d => { dataMap[d.date] = d.rate; });

    for (let i = days; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const dStr = d.toISOString().split('T')[0];

        const cell = document.createElement('div');
        cell.className = 'hm-cell';
        cell.title = dStr;

        if (dataMap[dStr] !== undefined) {
            const r = dataMap[dStr];
            cell.title += `: ${r}%`;
            if (r >= 85) cell.classList.add('level-3');
            else if (r >= 70) cell.classList.add('level-2');
            else if (r >= 50) cell.classList.add('level-1');
            else cell.classList.add('absent');
        }
        container.appendChild(cell);
    }
}


// --- Cameras & System Health ---
async function fetchCameras() {
    const data = await fetchAPI('/api/cameras');
    if (data && data.success) {
        const grid = document.getElementById('cameras-grid');
        grid.innerHTML = '';
        data.cameras.forEach(c => {
            const statusColor = c.status === 'online' ? 'var(--emerald)' : 'var(--rose)';
            grid.innerHTML += `
                <div class="camera-card glass-panel">
                    <div class="cam-header">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <i class="ph ph-webcam" style="font-size:24px; color:var(--primary)"></i>
                            <span style="font-weight:700">${c.name}</span>
                        </div>
                        <span class="cam-id">${c.camera_id}</span>
                    </div>
                    <div class="cam-details">
                        <div><span>Location</span>${c.building || ''} ${c.room}</div>
                        <div><span>Status</span><strong style="color:${statusColor}">${c.status.toUpperCase()}</strong></div>
                        <div><span>Resolution</span>${c.resolution}</div>
                        <div><span>Last Heartbeat</span>${c.last_heartbeat || 'Never'}</div>
                    </div>
                </div>
            `;
        });
    }
    fetchAuditLogs();
}

async function fetchAuditLogs() {
    const data = await fetchAPI('/api/audit-logs');
    if (data && data.success) {
        const tbody = document.getElementById('audit-tbody');
        tbody.innerHTML = '';
        data.logs.forEach(l => {
            tbody.innerHTML += `
                <tr>
                    <td style="font-size:12px; color:var(--text-muted)">${l.created_at}</td>
                    <td><strong>${l.username}</strong></td>
                    <td><span class="badge scheduled" style="font-size:10px">${l.action}</span></td>
                    <td>${l.entity_type} <span class="text-muted">#${l.entity_id}</span></td>
                    <td style="font-size:12px">${l.old_value} &rarr; ${l.new_value}</td>
                </tr>
            `;
        });
    }
}


// --- Overrides ---
function openOverrideModal(id, currentStatus) {
    document.getElementById('override-record-id').value = id;
    document.getElementById('override-current').value = currentStatus;
    document.getElementById('override-modal').classList.remove('hidden');
}
function closeOverrideModal() {
    document.getElementById('override-modal').classList.add('hidden');
}

async function submitOverride() {
    const id = document.getElementById('override-record-id').value;
    const status = document.getElementById('override-status').value;
    const reason = document.getElementById('override-reason').value;

    if (!reason) {
        showToast('Error', 'Reason is required for audit trail', 'warning');
        return;
    }

    const data = await fetchAPI(`/api/attendance/${id}/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, reason })
    });

    if (data && data.success) {
        showToast('Success', 'Attendance overridden', 'success');
        closeOverrideModal();
        fetchLogsByDate(); // refresh table
    } else {
        showToast('Error', data?.error || 'Update failed', 'error');
    }
}


// --- Notifications ---
async function fetchNotifications() {
    const data = await fetchAPI('/api/notifications');
    if (data && data.success) {
        updateNotifBadge(data.unread);

        const list = document.getElementById('notif-list');
        list.innerHTML = '';

        if (data.notifications.length === 0) {
            list.innerHTML = `<div class="empty-state-sm"><i class="ph ph-bell-slash"></i><p>No notifications</p></div>`;
            return;
        }

        data.notifications.forEach(n => {
            const div = document.createElement('div');
            div.className = `notif-item ${n.type} ${n.read ? '' : 'unread'}`;
            div.onclick = () => { if (!n.read) markRead(n.id, div); };
            div.innerHTML = `
                <h4>${n.title}</h4>
                <p>${n.message}</p>
                <div style="font-size:10px; color:var(--text-muted); margin-top:4px; text-align:right">${n.created_at}</div>
            `;
            list.appendChild(div);
        });
    }
}

function updateNotifBadge(count) {
    const badge = document.getElementById('notif-count');
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function toggleNotifPanel() {
    const panel = document.getElementById('notif-panel');
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) fetchNotifications();
}

async function markRead(id, el) {
    await fetchAPI(`/api/notifications/${id}/read`, { method: 'POST' });
    el.classList.remove('unread');

    const badge = document.getElementById('notif-count');
    let cnt = parseInt(badge.textContent) || 0;
    cnt = Math.max(0, cnt - 1);
    updateNotifBadge(cnt);
}

async function markAllRead() {
    await fetchAPI('/api/notifications/read-all', { method: 'POST' });
    fetchNotifications();
}


// --- Exports ---
function exportExcel() {
    const d = document.getElementById('date-filter').value;
    window.open(`/api/export?date=${d}`, '_blank');
}
function exportCSV() {
    const d = document.getElementById('date-filter').value;
    window.open(`/api/export/csv?date=${d}`, '_blank');
}
function exportPDF() {
    const d = document.getElementById('date-filter').value;
    window.open(`/api/export/pdf?date=${d}`, '_blank');
}


// --- Helpers ---
async function doLogout() {
    await fetchAPI('/auth/logout', { method: 'POST' });
    window.location.href = '/login';
}

function loadDropdowns() {
    // Populate session departments and classrooms statically for UI speed
    const depts = ['Artificial Intelligence & Data Science', 'Computer Science & Engineering', 'Information Technology', 'Electronics', 'Mechanical', 'General'];
    const rooms = ['LAB-101', 'LAB-102', 'LAB-204', 'ROOM-101', 'ROOM-202', 'SEMINAR HALL'];

    const deptSel = document.getElementById('sess-dept');
    if (deptSel && deptSel.tagName === 'SELECT') {
        depts.forEach(d => deptSel.innerHTML += `<option value="${d}">${d}</option>`);
    }

    const userDeptSel = document.getElementById('um-dept');
    if (userDeptSel && userDeptSel.tagName === 'SELECT') {
        depts.forEach(d => userDeptSel.innerHTML += `<option value="${d}">${d}</option>`);
    }
}

// ============================================================================
// RBAC / User Management / Profile Functions
// ============================================================================

// --- Profile Modal ---
function openProfileModal() {
    document.getElementById('profile-cur-pw').value = '';
    document.getElementById('profile-new-pw').value = '';
    document.getElementById('profile-confirm-pw').value = '';
    document.getElementById('profile-info').innerHTML = `
        <div style="font-size:14px; margin-bottom:8px;"><strong>Username:</strong> ${document.getElementById('sidebar-username').textContent}</div>
        <div style="font-size:14px; margin-bottom:8px;"><strong>Role:</strong> <span class="badge scheduled">${window.userRole}</span></div>
    `;
    document.getElementById('profile-modal').classList.remove('hidden');
}

function closeProfileModal() {
    document.getElementById('profile-modal').classList.add('hidden');
}

async function submitChangePassword() {
    const cur = document.getElementById('profile-cur-pw').value;
    const npw = document.getElementById('profile-new-pw').value;
    const cnf = document.getElementById('profile-confirm-pw').value;
    if (!cur || !npw) return showToast('Error', 'Current and new passwords required', 'error');
    if (npw !== cnf) return showToast('Error', 'Passwords do not match', 'error');

    const data = await fetchAPI('/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: cur, new_password: npw })
    });
    if (!data) return;
    if (data.success) {
        showToast('Success', data.message, 'success');
        closeProfileModal();
    } else {
        showToast('Error', data.message || 'Failed to change password', 'error');
    }
}

// --- User Management ---
async function fetchUsers() {
    const data = await fetchAPI('/api/users');
    if (data && data.success) renderUsersTable(data.users);
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '';
    if (!users || users.length === 0) return;

    users.forEach(u => {
        let statusBadge = u.is_active ? `<span class="badge present">Active</span>` : `<span class="badge absent">Disabled</span>`;
        if (u.locked_until && new Date(u.locked_until) > new Date()) {
            statusBadge = `<span class="badge late">Locked</span>`;
        }

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${u.username}</strong></td>
            <td>${u.full_name || '—'}</td>
            <td>${u.email || '—'}</td>
            <td><span class="badge scheduled" style="text-transform:lowercase">${u.role}</span></td>
            <td>${u.department_name || '—'}</td>
            <td>${statusBadge}</td>
            <td style="font-size:12px; color:var(--text-muted)">${u.last_login || 'Never'}</td>
            <td>
                <button class="btn-icon" onclick="openEditUserModal(${u.id})" title="Edit"><i class="ph ph-pencil-simple"></i></button>
                <button class="btn-icon" onclick="openResetPwModal(${u.id}, '${u.username}')" title="Reset Password"><i class="ph ph-lock-key"></i></button>
                ${u.is_active
                ? `<button class="btn-icon text-danger" onclick="toggleUserStatus(${u.id}, false)" title="Disable"><i class="ph ph-user-minus"></i></button>`
                : `<button class="btn-icon text-success" onclick="toggleUserStatus(${u.id}, true)" title="Enable"><i class="ph ph-user-plus"></i></button>`
            }
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterUsersTable() {
    const term = document.getElementById('user-search').value.toLowerCase();
    const rows = document.getElementById('users-tbody').querySelectorAll('tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
    });
}

function openAddUserModal() {
    document.getElementById('user-modal-title').innerHTML = '<i class="ph ph-user-plus"></i> Add User';
    document.getElementById('user-modal-submit-text').textContent = 'Create User';
    document.getElementById('user-modal-id').value = '';
    document.getElementById('um-username').value = '';
    document.getElementById('um-username').disabled = false;
    document.getElementById('um-fullname').value = '';
    document.getElementById('um-email').value = '';
    document.getElementById('um-role').value = 'faculty';
    document.getElementById('um-dept').value = '';
    document.getElementById('um-student-id').value = '';
    document.getElementById('um-password').value = '';
    document.getElementById('um-password-group').style.display = 'block';
    document.getElementById('user-modal').classList.remove('hidden');
}

async function openEditUserModal(id) {
    const data = await fetchAPI(`/api/users/${id}`);
    if (!data || !data.success) return;
    const u = data.user;

    document.getElementById('user-modal-title').innerHTML = '<i class="ph ph-pencil-simple"></i> Edit User';
    document.getElementById('user-modal-submit-text').textContent = 'Save Changes';
    document.getElementById('user-modal-id').value = u.id;
    document.getElementById('um-username').value = u.username;
    document.getElementById('um-username').disabled = true; // Cannot edit username
    document.getElementById('um-fullname').value = u.full_name || '';
    document.getElementById('um-email').value = u.email || '';
    document.getElementById('um-role').value = u.role;
    // Note: department dropdown logic simplified for UI speed
    document.getElementById('um-student-id').value = u.student_id || '';
    document.getElementById('um-password-group').style.display = 'none'; // Password changed elsewhere
    document.getElementById('user-modal').classList.remove('hidden');
}

function closeUserModal() {
    document.getElementById('user-modal').classList.add('hidden');
}

async function submitUserForm() {
    const id = document.getElementById('user-modal-id').value;
    const payload = {
        username: document.getElementById('um-username').value,
        full_name: document.getElementById('um-fullname').value,
        email: document.getElementById('um-email').value,
        role: document.getElementById('um-role').value,
        student_id: document.getElementById('um-student-id').value || null,
        // Hacky string-to-id mapping omitted for brevity, passing null
    };

    if (!id) {
        payload.password = document.getElementById('um-password').value;
        const data = await fetchAPI('/api/users', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!data) return;
        if (data.success) { showToast('Success', 'User created', 'success'); closeUserModal(); fetchUsers(); }
        else showToast('Error', data.message || 'Failed to create', 'error');
    } else {
        const data = await fetchAPI(`/api/users/${id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!data) return;
        if (data.success) { showToast('Success', 'User updated', 'success'); closeUserModal(); fetchUsers(); }
        else showToast('Error', data.message || 'Failed to update', 'error');
    }
}

async function toggleUserStatus(id, activate) {
    const endpoint = activate ? `/api/users/${id}/enable` : `/api/users/${id}/disable`;
    const data = await fetchAPI(endpoint, { method: 'POST' });
    if (data && data.success) { showToast('Success', data.message, 'success'); fetchUsers(); }
}

function openResetPwModal(id, username) {
    document.getElementById('reset-pw-user-id').value = id;
    document.getElementById('reset-pw-username').textContent = `Resetting password for: ${username}`;
    document.getElementById('reset-pw-new').value = '';
    document.getElementById('reset-pw-modal').classList.remove('hidden');
}
function closeResetPwModal() { document.getElementById('reset-pw-modal').classList.add('hidden'); }

async function submitResetPassword() {
    const id = document.getElementById('reset-pw-user-id').value;
    const npw = document.getElementById('reset-pw-new').value;
    if (!npw) return;
    const data = await fetchAPI(`/api/users/${id}/reset-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: npw })
    });
    if (!data) return;
    if (data.success) { showToast('Success', 'Password reset', 'success'); closeResetPwModal(); }
    else showToast('Error', data.message, 'error');
}

// --- Audit Logs ---
async function fetchAuditLogs() {
    const usr = document.getElementById('audit-user-filter').value;
    const act = document.getElementById('audit-action-filter').value;
    const from = document.getElementById('audit-date-from').value;
    const to = document.getElementById('audit-date-to').value;

    let url = '/api/audit-logs?limit=200';
    if (usr) url += `&username=${encodeURIComponent(usr)}`;
    if (act) url += `&action=${encodeURIComponent(act)}`;
    if (from) url += `&date_from=${from}`;
    if (to) url += `&date_to=${to}`;

    const data = await fetchAPI(url);
    if (data && data.success) renderAuditTable(data.logs);
}

function renderAuditTable(logs) {
    const tbody = document.getElementById('audit-tbody');
    tbody.innerHTML = '';
    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center"><div class="empty-state-sm">No audit logs found</div></td></tr>`;
        return;
    }
    logs.forEach(l => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-size:12px; color:var(--text-muted)">${l.created_at}</td>
            <td><strong>${l.username}</strong></td>
            <td><span class="badge scheduled" style="font-size:10px">${l.action}</span></td>
            <td>${l.entity_type} <span class="text-muted">#${l.entity_id}</span></td>
            <td style="font-size:12px">${l.old_value} &rarr; ${l.new_value}</td>
            <td style="font-size:11px; color:var(--text-muted)">${l.ip_address}</td>
        `;
        tbody.appendChild(tr);
    });
}

function exportAuditLogs() {
    showToast('Info', 'Audit export initiated', 'info');
    // Implement standard CSV download logic here if needed
}
