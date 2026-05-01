import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import hashlib

# Supabase connection
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password, hospital):
    response = supabase.table("users").select("*").eq("username", username).execute()
    result = response.data
    if len(result) > 0:
        user = result[0]
        if user['password_hash'] == hash_password(password) and hospital in user['hospitals']:
            return user
    return None

def get_users():
    response = supabase.table("users").select("*").execute()
    result = response.data
    if len(result) > 0:
        return result
    else:
        return []

def get_patients():
    response = supabase.table("patients").select("*").execute()
    result = response.data
    if len(result) > 0:
        return result
    else:
        return []

def get_cultures():
    response = supabase.table("cultures").select("*").execute()
    result = response.data
    if len(result) > 0:
        return result
    else:
        return []

def add_user(data):
    data['password_hash'] = hash_password(data['password'])
    del data['password']
    response = supabase.table("users").insert(data).execute()
    return response.data

def add_patient(data):
    response = supabase.table("patients").insert(data).execute()
    return response.data

def add_culture(data):
    response = supabase.table("cultures").insert(data).execute()
    return response.data

# Streamlit UI
st.set_page_config(page_title="Huduma Poa AMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Huduma Poa AMS - Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        hospital = st.selectbox("Hospital", ["Tanga RRH", "Bombo Hospital", "Muheza Hospital"])
        submit = st.form_submit_button("Login")

        if submit:
            user = authenticate_user(username, password, hospital)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.hospital = hospital
                st.rerun()
            else:
                st.error("Invalid credentials or hospital access")
else:
    st.sidebar.title(f"Welcome {st.session_state.user['full_name']}")
    st.sidebar.write(f"Hospital: {st.session_state.hospital}")

    if st.sidebar.button("Logout"):
        st.session_state
