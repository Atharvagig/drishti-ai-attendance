// Drishti AI — Client Application Logic

document.addEventListener('DOMContentLoaded', () => {
    // Set current date
    const dateEl = document.getElementById('current-date');
    if (dateEl) {
        const today = new Date();
        dateEl.textContent = today.toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
        });
    }

    // Set today's date in date picker
    const datePicker = document.getElementById('date-filter');
    if (datePicker) {
        datePicker.value = new Date().toISOString().split('T')[0];
    }

    // Load initial dashboard statistics & logs
    fetchStats();
});

// --- Tab Navigation ---
function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.add('hidden'));

    const activeBtn = document.querySelector(`.nav-item[onclick="switchTab('${tabId}')"]`);
    if (activeBtn) activeBtn.classList.add('active');

    const activeSec = document.getElementById(tabId);
    if (activeSec) activeSec.classList.remove('hidden');

    // Trigger tab-specific data fetching
    if (tabId === 'dashboard') {
        fetchStats();
    } else if (tabId === 'students') {
        fetchStudents();
    }
}

// --- Fetch Dashboard Analytics & Logs ---
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        if (data.success) {
            document.getElementById('stat-registered').textContent = data.total_registered || 0;
            document.getElementById('stat-present').textContent = data.present_today || 0;
            document.getElementById('stat-absent').textContent = data.absent_today || 0;
            document.getElementById('stat-rate').textContent = `${data.attendance_rate || 0}%`;

            renderAttendanceTable(data.attendance || []);
        } else {
            showToast(data.error || 'Failed to load stats', 'error');
        }
    } catch (err) {
        console.error('Error fetching stats:', err);
        showToast('Server connection error.', 'error');
    }
}

// --- Fetch Attendance Logs by Date ---
async function fetchLogsByDate() {
    const datePicker = document.getElementById('date-filter');
    const selectedDate = datePicker ? datePicker.value : '';

    try {
        const res = await fetch(`/api/attendance?date=${selectedDate}`);
        const data = await res.json();

        if (data.success) {
            renderAttendanceTable(data.attendance || []);
        } else {
            showToast(data.error || 'Failed to load logs', 'error');
        }
    } catch (err) {
        console.error('Error fetching logs by date:', err);
    }
}

// --- Render Attendance Table ---
function renderAttendanceTable(records) {
    const tbody = document.getElementById('attendance-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!records || records.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">
                    No attendance records logged for this selection.
                </td>
            </tr>
        `;
        return;
    }

    records.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(row.student_id)}</strong></td>
            <td>${escapeHtml(row.name)}</td>
            <td>${escapeHtml(row.department || 'General')}</td>
            <td>${escapeHtml(row.time)}</td>
            <td>${escapeHtml(row.date)}</td>
            <td><span style="color: var(--emerald); font-weight: 600;">${row.confidence ? row.confidence + '%' : '100%'}</span></td>
            <td><span class="badge badge-green">Present</span></td>
            <td>
                <button class="btn-icon" style="color: var(--rose);" onclick="deleteRecord(${row.id})" title="Delete Record">
                    <i class="ph ph-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Filter Table Rows Client-side ---
function filterLogsTable() {
    const query = document.getElementById('log-search').value.toLowerCase();
    const rows = document.querySelectorAll('#attendance-tbody tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

// --- Fetch Registered Students ---
async function fetchStudents() {
    const grid = document.getElementById('students-grid');
    if (!grid) return;

    try {
        const res = await fetch('/api/students');
        const data = await res.json();

        grid.innerHTML = '';

        if (data.success && data.students.length > 0) {
            data.students.forEach(student => {
                const card = document.createElement('div');
                card.className = 'student-card glass-panel';
                card.innerHTML = `
                    <div class="student-avatar">
                        <i class="ph ph-user"></i>
                    </div>
                    <h4>${escapeHtml(student.name)}</h4>
                    <div class="sid">ID: ${escapeHtml(student.student_id)}</div>
                    <div class="dept">${escapeHtml(student.department || 'General')}</div>
                    ${student.email ? `<div class="email" style="font-size:11px; color: var(--text-muted); margin-top:2px;">${escapeHtml(student.email)}</div>` : ''}
                    <button class="btn-delete-student" onclick="deleteStudent('${escapeHtml(student.student_id)}')">
                        <i class="ph ph-trash"></i> Remove
                    </button>
                `;
                grid.appendChild(card);
            });
        } else {
            grid.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 40px;" class="glass-panel">
                    <i class="ph ph-users" style="font-size: 40px; margin-bottom: 10px;"></i>
                    <p>No registered students found. Enroll new students to get started.</p>
                </div>
            `;
        }
    } catch (err) {
        console.error('Error fetching students:', err);
    }
}

// --- Register Student Form Handler ---
async function handleRegister(event) {
    event.preventDefault();

    const name = document.getElementById('student-name').value.trim();
    const sid = document.getElementById('student-id').value.trim();
    const department = document.getElementById('student-dept').value.trim() || 'General';
    const email = document.getElementById('student-email').value.trim();

    const btn = document.getElementById('btn-register');
    const origText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `<span>Opening Camera...</span> <i class="ph ph-spinner spinner"></i>`;

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, sid, department, email })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('register-form').reset();
            fetchStats();
        } else {
            showToast(data.error || 'Registration failed.', 'error');
        }
    } catch (err) {
        showToast('Error connecting to server.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

// --- Start Camera Attendance Session ---
async function startAttendance() {
    const btn = document.getElementById('btn-start-attendance');
    const origText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `<span>Initializing Camera...</span>`;

    try {
        const res = await fetch('/api/start_attendance', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            showToast('Live tracking window launched!', 'success');
        } else {
            showToast(data.error || 'Failed to start camera.', 'error');
        }
    } catch (err) {
        showToast('Error launching camera engine.', 'error');
    } finally {
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = origText;
        }, 2000);
    }
}

// --- Delete Student ---
async function deleteStudent(studentId) {
    if (!confirm(`Are you sure you want to remove student ID: ${studentId}?`)) return;

    try {
        const res = await fetch('/api/students/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: studentId })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message, 'success');
            fetchStudents();
            fetchStats();
        } else {
            showToast(data.error || 'Deletion failed.', 'error');
        }
    } catch (err) {
        showToast('Error communicating with server.', 'error');
    }
}

// --- Delete Attendance Record ---
async function deleteRecord(recordId) {
    if (!confirm('Are you sure you want to delete this log entry?')) return;

    try {
        const res = await fetch(`/api/attendance/${recordId}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            showToast('Log entry removed.', 'success');
            fetchLogsByDate();
        } else {
            showToast(data.error || 'Delete failed.', 'error');
        }
    } catch (err) {
        showToast('Server error.', 'error');
    }
}

// --- Export Excel (.xlsx) ---
function exportExcel() {
    const datePicker = document.getElementById('date-filter');
    const selectedDate = datePicker ? datePicker.value : '';
    let url = '/api/export';
    if (selectedDate) url += `?date=${selectedDate}`;

    window.location.href = url;
    showToast('Downloading Excel spreadsheet...', 'success');
}

// --- Toast Notification Utility ---
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="ph ph-${type === 'success' ? 'check-circle' : 'warning-circle'}"></i>
        <span>${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slide-in 0.3s reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Helper to escape HTML characters
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
