import streamlit as st
from streamlit import session_state as ss

# Initialize session state variables
if 'logged_in' not in ss:
    ss.logged_in = False
if 'username' not in ss:
    ss.username = ''
if 'users' not in ss:
    ss.users = {}  # Simple in-memory user database (replace with real DB in production)

def login():
    username = ss['login_username']
    password = ss['login_password']
    
    if username in ss.users and ss.users[username] == password:
        ss.logged_in = True
        ss.username = username
        st.success("Logged in successfully!")
    else:
        st.error("Invalid username or password")

def signup():
    username = ss['signup_username']
    password = ss['signup_password']
    
    if username in ss.users:
        st.error("Username already exists")
    elif not username or not password:
        st.error("Username and password cannot be empty")
    else:
        ss.users[username] = password
        st.success("Account created successfully! Please log in.")

def logout():
    ss.logged_in = False
    ss.username = ''

# Main app logic
if ss.logged_in:
    st.title(f"Welcome, {ss.username}!")
    st.button("Logout", on_click=logout)
    
    # Your protected content goes here
    st.write("This is your protected dashboard content.")
    
else:
    # Login/Signup tabs
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        st.text_input("Username", key="login_username")
        st.text_input("Password", type="password", key="login_password")
        st.button("Login", on_click=login)
    
    with tab2:
        st.header("Create Account")
        st.text_input("Username", key="signup_username")
        st.text_input("Password", type="password", key="signup_password")
        st.button("Sign Up", on_click=signup)