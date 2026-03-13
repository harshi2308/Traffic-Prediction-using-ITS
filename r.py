import cv2
import torch
import tempfile
from ultralytics import YOLO
import streamlit as st
from norfair import Detection, Tracker
import numpy as np
import pandas as pd
import hashlib
import sqlite3

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Password hashing
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# User authentication functions
def create_user(username, password, email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO users(username,password,email) VALUES (?,?,?)', 
              (username, make_hashes(password), email))
    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    
    if data and check_hashes(password, data[1]):
        return True
    return False

# Initialize database
init_db()

# Session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None

# Authentication UI
def auth_ui():
    st.title("Traffic Analysis System Login")
    st.write("Please login to access the video classification system")
    
    menu = ["Login", "Sign Up"]
    choice = st.selectbox("Menu", menu)
    
    if choice == "Login":
        st.subheader("Login Section")
        username = st.text_input("User Name")
        password = st.text_input("Password", type='password')
        
        if st.button("Login"):
            if login_user(username, password):
                st.session_state['authenticated'] = True
                st.session_state['username'] = username
                st.success(f"Logged In as {username}")
                st.rerun()  # Changed from experimental_rerun to rerun
            else:
                st.error("Incorrect Username/Password")
    
    elif choice == "Sign Up":
        st.subheader("Create New Account")
        new_user = st.text_input("Username")
        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type='password')
        confirm_password = st.text_input("Confirm Password", type='password')
        
        if st.button("Sign Up"):
            if new_password == confirm_password:
                try:
                    create_user(new_user, new_password, new_email)
                    st.success("Account created successfully! Please login.")
                except:
                    st.error("Username already exists")
            else:
                st.error("Passwords don't match")

# Main application
def traffic_optimization_app():
    # Load the YOLOv5 model for non-emergency vehicles
    yolo_v5_non_emergency = torch.hub.load('ultralytics/yolov5', 'yolov5s')  # Pre-trained YOLOv5 model

    # Define labels for non-emergency vehicles
    non_emergency_labels = ['car', 'bus', 'truck', 'motorcycle']

    st.title("Advanced Traffic Flow Optimization System")
    st.write(f"Welcome, {st.session_state['username']}!")
    
    st.subheader("Video Classification")
    st.write("Upload traffic videos for analysis")

    # File uploader for multiple videos
    uploaded_files = st.file_uploader(
        "Upload up to 4 Videos", type=["mp4", "mov", "avi", "mkv"], accept_multiple_files=True
    )

    def create_detections(results, labels, model_type="yolov5"):
        """Convert YOLO detection results to Norfair detections for tracking."""
        detections = []
        if model_type == "yolov5":
            if hasattr(results, 'xyxy'):
                for result in results.xyxy[0]:
                    if len(result) >= 6:
                        x1, y1, x2, y2, conf, cls = result[:6]
                        label = labels[int(cls)]
                        centroid = np.array([[(x1 + x2) / 2, (y1 + y2) / 2]])
                        if label in non_emergency_labels:
                            detections.append(
                                Detection(
                                    centroid, 
                                    data={"label": label, "conf": conf, "box": (int(x1), int(y1), int(x2), int(y2))}
                                )
                            )
        return detections

    if uploaded_files:
        total_clearance_time = 0
        video_results = []

        for idx, uploaded_file in enumerate(uploaded_files[:4]):
            st.write(f"### Processing Video {idx + 1}: {uploaded_file.name}")
            
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(uploaded_file.read())

            cap = cv2.VideoCapture(tfile.name)
            stframe = st.empty()

            unique_non_emergency_ids = set()
            tracker = Tracker(distance_function="euclidean", distance_threshold=30)

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                non_emergency_results = yolo_v5_non_emergency(frame)
                detections = create_detections(non_emergency_results, yolo_v5_non_emergency.names, model_type="yolov5")
                tracked_objects = tracker.update(detections)

                for obj in tracked_objects:
                    label = obj.last_detection.data["label"]
                    x1, y1, x2, y2 = obj.last_detection.data["box"]

                    if label in non_emergency_labels:
                        if obj.id not in unique_non_emergency_ids:
                            unique_non_emergency_ids.add(obj.id)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f'{label} {obj.id}', (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                stframe.image(frame, channels="BGR", use_column_width=True)

            cap.release()

            non_emergency_count = len(unique_non_emergency_ids)
            clearance_time = non_emergency_count * 3
            total_clearance_time += clearance_time 

            video_results.append({
                "Video Name": uploaded_file.name,
                "Vehicle Count": non_emergency_count,
                "Estimated Road Clearance Time (seconds)": clearance_time
            })

        video_df = pd.DataFrame(video_results)
        st.write("### Video Detection Summary")
        st.table(video_df)

        st.write(f"### Total Road Clearance Time: {total_clearance_time} seconds")
        max_vehicle_video = video_df.loc[video_df["Vehicle Count"].idxmax()]
        st.write(f"### Priority Route: {max_vehicle_video['Video Name']}")

# Main app flow
if not st.session_state['authenticated']:
    auth_ui()
else:
    if st.sidebar.button("Logout"):
        st.session_state['authenticated'] = False
        st.session_state['username'] = None
        st.rerun() 
    traffic_optimization_app()