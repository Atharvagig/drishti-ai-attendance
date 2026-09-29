import streamlit as st
import pandas as pd
import os
import subprocess
from datetime import datetime
import glob

# Must be the first Streamlit command
st.set_page_config(page_title="AI Smart Attendance", page_icon="🏫", layout="wide", initial_sidebar_state="expanded")

# --- Custom Premium CSS ---
def local_css():
    st.markdown("""
    <style>
    /* Main Background & Text */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid #334155;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #e2e8f0;
        font-weight: 600;
        letter-spacing: -0.025em;
    }
    h1 {
        background: -webkit-linear-gradient(45deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 10px;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
        width: 100%;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        color: white;
    }
    
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
        color: #3b82f6;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
    }
    
    /* Form input styling */
    .stTextInput>div>div>input {
        background-color: #1e293b;
        color: white;
        border: 1px solid #334155;
        border-radius: 6px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 1px #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- Utility Functions ---
def get_today_csv():
    today = datetime.now().strftime('%Y-%m-%d')
    return f"Attendance_{today}.csv"

def get_total_registered_students():
    dataset_dir = 'dataset'
    if not os.path.exists(dataset_dir):
        return 0
    return len([name for name in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, name))])

# --- Sidebar Navigation ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.title("Admin Panel")
    st.markdown("---")
    menu = st.radio("Navigation", ["📊 Dashboard", "👤 Register Student", "🎥 Take Attendance"], label_visibility="collapsed")

# --- Page: Dashboard ---
if menu == "📊 Dashboard":
    st.title("Today's Attendance")
    st.markdown("Monitor real-time attendance logs for your institution.")
    
    csv_file = get_today_csv()
    
    # Metrics row
    col1, col2, col3 = st.columns(3)
    total_registered = get_total_registered_students()
    
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        present_count = len(df)
    else:
        df = pd.DataFrame(columns=['Name', 'ID', 'Time'])
        present_count = 0
        
    with col1:
        st.metric("Total Present Today", present_count)
    with col2:
        st.metric("Total Registered", total_registered)
    with col3:
        st.metric("Date", datetime.now().strftime("%B %d, %Y"))
        
    st.markdown("### 📋 Attendance Log")
    if present_count > 0:
        # Display as a nice dataframe
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No attendance records found for today yet. Start the camera to begin taking attendance!")

# --- Page: Register Student ---
elif menu == "👤 Register Student":
    st.title("Register New Student")
    st.markdown("Capture face data for a new student so the system can recognize them.")
    
    with st.form("registration_form"):
        st.subheader("Student Details")
        student_name = st.text_input("Full Name (e.g., Atharva)")
        student_id = st.text_input("Student ID (e.g., 101)")
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit_button = st.form_submit_button(label="📸 Capture Face Data & Train Model")
        
        if submit_button:
            if student_name and student_id:
                with st.spinner(f"Starting camera for {student_name}... Please look at the webcam."):
                    try:
                        # Launch capture_faces.py
                        # We pass the name and id as command line arguments
                        st.info("Webcam window will open. Follow the on-screen instructions.")
                        capture_proc = subprocess.run(["py", "capture_faces.py", student_name, student_id], capture_output=True, text=True)
                        
                        if capture_proc.returncode == 0:
                            st.success(f"Face data captured successfully for {student_name}!")
                            
                            with st.spinner("Training the AI model on new data..."):
                                train_proc = subprocess.run(["py", "train_model.py"], capture_output=True, text=True)
                                if train_proc.returncode == 0:
                                    st.success("Model trained successfully! The system can now recognize this student.")
                                else:
                                    st.error(f"Training failed: {train_proc.stderr}")
                        else:
                            st.error(f"Capture failed: {capture_proc.stderr}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
            else:
                st.warning("Please enter both Name and Student ID.")

# --- Page: Take Attendance ---
elif menu == "🎥 Take Attendance":
    st.title("Live Face Recognition")
    st.markdown("Start the smart attendance engine. The system will open your webcam, recognize students, and log their entry time automatically.")
    
    st.info("A separate webcam window will open. To stop taking attendance, press 'q' on your keyboard while focused on the webcam window.")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Launch Attendance Engine", use_container_width=True):
            with st.spinner("Attendance engine is running... Press 'q' on the video window to stop."):
                try:
                    proc = subprocess.run(["py", "recognize_faces.py"])
                    st.success("Attendance session finished! Check the Dashboard for logs.")
                except Exception as e:
                    st.error(f"Failed to start camera: {e}")
