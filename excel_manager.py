import os
from datetime import datetime
import pandas as pd

MASTER_EXCEL_FILE = "Attendance_Master.xlsx"

def get_daily_excel_filename(date_str=None):
    """Generates standard daily Excel filename."""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    return f"Attendance_{date_str}.xlsx"

def sync_attendance_to_excel(student_id, name, department="General", date_str=None, time_str=None, confidence=0.0, email_sent=0):
    """
    Appends a new attendance record directly into both daily and master Excel spreadsheets.
    Columns: Date, Time, Student ID, Name, Department, Status, Confidence (%), Email Alert
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    if not time_str:
        time_str = datetime.now().strftime('%H:%M:%S')

    new_row = {
        'Date': str(date_str),
        'Time': str(time_str),
        'Student ID': str(student_id),
        'Name': str(name),
        'Department': str(department),
        'Status': 'Present',
        'Confidence (%)': f"{confidence:.1f}%" if isinstance(confidence, (int, float)) else str(confidence),
        'Email Alert': 'Sent' if email_sent else 'Skipped'
    }

    # Update Daily Excel File
    daily_filename = get_daily_excel_filename(date_str)
    _append_row_to_excel(daily_filename, new_row)

    # Update Master Excel File
    _append_row_to_excel(MASTER_EXCEL_FILE, new_row)

    print(f"[Excel Sync] Synchronized record for {name} ({student_id}) to {daily_filename} & {MASTER_EXCEL_FILE}")
    return True

def _append_row_to_excel(filepath, row_dict):
    """Helper method to append a row to an Excel file using pandas."""
    columns = ['Date', 'Time', 'Student ID', 'Name', 'Department', 'Status', 'Confidence (%)', 'Email Alert']
    
    if os.path.exists(filepath):
        try:
            df = pd.read_excel(filepath)
        except Exception:
            df = pd.DataFrame(columns=columns)
    else:
        df = pd.DataFrame(columns=columns)

    # Prevent duplicate ID entries for the same date
    if not df.empty and ('Student ID' in df.columns) and ('Date' in df.columns):
        duplicate_check = df[(df['Student ID'].astype(str) == str(row_dict['Student ID'])) & 
                             (df['Date'].astype(str) == str(row_dict['Date']))]
        if not duplicate_check.empty:
            return  # Already exists in this Excel sheet

    new_entry_df = pd.DataFrame([row_dict])
    df = pd.concat([df, new_entry_df], ignore_index=True)
    df.to_excel(filepath, index=False)

if __name__ == '__main__':
    sync_attendance_to_excel('1001', 'Test Student', 'Computer Science', confidence=98.5)
    print("[Excel Sync] Engine tested successfully.")
