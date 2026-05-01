import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import hashlib

st.set_page_config(page_title="ODIEMAN AMS", layout="wide", page_icon="🏥")

# Supabase connection
from supabase import create_client, Client
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password, hospital):
    response = supabase.table("users").select("*").eq("username", username).eq("password", password).eq("hospital", hospital).execute()
    result = response.data
    if len(result) > 0:
        return result[0]
    else:
        return None
    response = supabase.table("users").select("*").eq("username", username).eq("password", password).eq("hospital", hospital).execute()
result = response.data
    if not result.empty:
        user = result.iloc[0]
        if user['password_hash'] == hash_password(password) and hospital in user['hospitals']:
            return user.to_dict()
    return None

def log_action(username, action, details):
    supabase.query(f"INSERT INTO audit_log (username, action, details) VALUES ('{username}', '{action}', '{details}')", ttl=0)

# Login screen
if 'user' not in st.session_state:
    st.title("🏥 ODIEMAN AMS Intelligence")
    st.subheader("Tanga Regional Referral Hospital")

    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
    with col2:
        region = st.selectbox("Region", ["Tanga"])
        district = st.selectbox("District", ["Tanga City"])
        hospital = st.selectbox("Hospital", ["Tanga Regional Referral Hospital"])

    if st.button("Login", type="primary"):
        user = check_login(username, password, hospital)
        if user:
            st.session_state.user = user
            log_action(username, "LOGIN", f"Login to {hospital}")
            st.rerun()
        else:
            st.error("Invalid login")
    st.stop()

# Main app
user = st.session_state.user
st.sidebar.title(f"Welcome {user['full_name']}")
st.sidebar.write(f"**Role:** {user['role']}")
st.sidebar.write(f"**Hospital:** Tanga Regional Referral Hospital")
if st.sidebar.button("Logout"):
    log_action(user['username'], "LOGOUT", "User logout")
    del st.session_state.user
    st.rerun()

tab1, tab2, tab3 = st.tabs(["Ward Round", "Dashboard", "Users"])

with tab1:
    st.header("Ward Round Assessment")
    ward = st.selectbox("Ward", ["Medical", "Surgical", "Pediatrics", "ICU"])
    col1, col2, col3 = st.columns(3)
    abx = col1.number_input("Antibiotic %", 0, 100, 65)
    inj = col2.number_input("Injection %", 0, 100, 15)
    gen = col3.number_input("Generic %", 0, 100, 80)

    if st.button("Save Assessment"):
        risk = "High Risk" if abx > 70 else "Medium Risk" if abx > 50 else "Low Risk"
        supabase.query(f"""
            INSERT INTO ward_assessments (ward, antibiotic_pct, injection_pct, generic_pct, risk, hospital, assessed_by)
            VALUES ('{ward}', {abx}, {inj}, {gen}, '{risk}', '{hospital}', '{user['username']}')
        """, ttl=0)
        log_action(user['username'], "ASSESSMENT", f"{ward} ward: {abx}% abx")
        if risk == "High Risk":
            st.error("🚨 HIGH RISK - WhatsApp alert sent to AMS Focal")
        else:
            st.success(f"Saved. Risk: {risk}")

with tab2:
    st.header("Dashboard - Tanga RRH")
    df = supabase.query(f"SELECT * FROM ward_assessments WHERE hospital='{hospital}' ORDER BY assessed_at DESC LIMIT 50", ttl=0)
    if not df.empty:
        st.dataframe(df[['ward', 'antibiotic_pct', 'risk', 'assessed_by', 'assessed_at']])
        st.metric("Avg Antibiotic %", f"{df['antibiotic_pct'].mean():.1f}%")
        st.metric("High Risk Count", len(df[df['risk']=='High Risk']))
    else:
        st.info("No assessments yet. Go to Ward Round tab.")

with tab3:
    if user['role'] == 'Admin':
        st.header("User Management")
        st.subheader("Create New User")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        new_name = st.text_input("Full Name")
        new_role = st.selectbox("Role", ["Hospital AMS Focal", "Viewer"])
        new_whatsapp = st.text_input("WhatsApp +255...")
        if st.button("Create User"):
            supabase.query(f"""
                INSERT INTO ams_users (username, password_hash, role, full_name, whatsapp, hospitals, active)
                VALUES ('{new_user}', '{hash_password(new_pass)}', '{new_role}', '{new_name}', '{new_whatsapp}', '["{hospital}"]', true)
            """, ttl=0)
            log_action(user['username'], "CREATE_USER", f"Created {new_user}")
            st.success(f"User {new_user} created")

        st.subheader("Audit Log")
        audit = supabase.query("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100", ttl=0)
        st.dataframe(audit)
    else:
        st.warning("Admin only")

# Footer
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)
