import os, re

def main():
    with open('frontend/templates/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # admin_panel.html
    with open('frontend/templates/admin_panel.html', 'w', encoding='utf-8') as f:
        f.write(content)

    # faculty_panel.html: remove user management, audit logs, cameras, enroll student
    faculty = content
    faculty = re.sub(r'<!-- ─── 8\. USER MANAGEMENT ──.*?<!-- ─── 9\. AUDIT LOGS', '<!-- ─── 9. AUDIT LOGS', faculty, flags=re.DOTALL)
    faculty = re.sub(r'<!-- ─── 9\. AUDIT LOGS ──.*?</section>\n', '', faculty, flags=re.DOTALL)
    faculty = re.sub(r'<button class="nav-item" onclick="switchTab\(\'register\'\)".*?</button>', '', faculty, flags=re.DOTALL)
    faculty = re.sub(r'<button class="nav-item" onclick="switchTab\(\'cameras\'\)".*?</button>', '', faculty, flags=re.DOTALL)
    faculty = re.sub(r'<!-- ─── 4\. ENROLL STUDENT ──.*?<!-- ─── 5\. LIVE TRACKING', '<!-- ─── 5. LIVE TRACKING', faculty, flags=re.DOTALL)
    faculty = re.sub(r'<!-- ─── 7\. CAMERA HEALTH ──.*?</section>\n', '', faculty, flags=re.DOTALL)
    with open('frontend/templates/faculty_panel.html', 'w', encoding='utf-8') as f:
        f.write(faculty)

    # student_panel.html: remove register, cameras, sessions, users, audit, tracking
    student = content
    student = re.sub(r'<!-- ─── 8\. USER MANAGEMENT ──.*?<!-- ─── 9\. AUDIT LOGS', '<!-- ─── 9. AUDIT LOGS', student, flags=re.DOTALL)
    student = re.sub(r'<!-- ─── 9\. AUDIT LOGS ──.*?</section>\n', '', student, flags=re.DOTALL)
    student = re.sub(r'<button class="nav-item" onclick="switchTab\(\'register\'\)".*?</button>', '', student, flags=re.DOTALL)
    student = re.sub(r'<button class="nav-item" onclick="switchTab\(\'cameras\'\)".*?</button>', '', student, flags=re.DOTALL)
    student = re.sub(r'<button class="nav-item" onclick="switchTab\(\'sessions\'\)".*?</button>', '', student, flags=re.DOTALL)
    student = re.sub(r'<button class="nav-item" onclick="switchTab\(\'attendance\'\)".*?</button>', '', student, flags=re.DOTALL)
    student = re.sub(r'<!-- ─── 4\. ENROLL STUDENT ──.*?<!-- ─── 5\. LIVE TRACKING', '<!-- ─── 5. LIVE TRACKING', student, flags=re.DOTALL)
    student = re.sub(r'<!-- ─── 5\. LIVE TRACKING ──.*?<!-- ─── 6\. ANALYTICS', '<!-- ─── 6. ANALYTICS', student, flags=re.DOTALL)
    student = re.sub(r'<!-- ─── 7\. CAMERA HEALTH ──.*?</section>\n', '', student, flags=re.DOTALL)
    student = re.sub(r'<!-- ─── 2\. SESSIONS ──.*?<!-- ─── 3\. STUDENT DIRECTORY', '<!-- ─── 3. STUDENT DIRECTORY', student, flags=re.DOTALL)
    with open('frontend/templates/student_panel.html', 'w', encoding='utf-8') as f:
        f.write(student)
    print('Templates split successfully.')

if __name__ == '__main__':
    main()
