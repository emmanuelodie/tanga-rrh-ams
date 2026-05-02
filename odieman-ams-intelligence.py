import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import hashlib

# ── Supabase connection ───────────────────────────────────────────
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ── Helpers ───────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password, hospital):
    response = supabase.table("users").select("*").eq("username", username).execute()
    result = response.data                          # ✅ FIXED (was [response.data](http://...))
    if len(result) > 0:
        user = result[0]
        if user['password_hash'] == hash_password(password) and hospital in user['hospitals']:
            return user
    return None

def get_users():
    response = supabase.table("users").select("*").execute()
    result = response.data                          # ✅ FIXED
    return result if len(result) > 0 else []

def get_patients():
    response = supabase.table("patients").select("*").execute()
    result = response.data                          # ✅ FIXED
    return result if len(result) > 0 else []

def get_cultures():
    response = supabase.table("cultures").select("*").execute()
    result = response.data                          # ✅ FIXED
    return result if len(result) > 0 else []

def add_user(data):
    data['password_hash'] = hash_password(data['password'])
    del data['password']
    response = supabase.table("users").insert(data).execute()
    return response.data                            # ✅ FIXED

def add_patient(data):
    response = supabase.table("patients").insert(data).execute()
    return response.data                            # ✅ FIXED

def add_culture(data):
    response = supabase.table("cultures").insert(data).execute()
    return response.data                            # ✅ FIXED

# ── Streamlit UI ──────────────────────────────────────────────────
st.set_page_config(page_title="Huduma Poa AMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'hospital' not in st.session_state:
    st.session_state.hospital = None

# ── Login ─────────────────────────────────────────────────────────
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
                st.session_state.hospital = hospital   # ✅ FIXED (was state.hospital)
                st.rerun()
            else:
                st.error("Invalid credentials or hospital access")

# ── Main App ──────────────────────────────────────────────────────
else:
    st.sidebar.title(f"Welcome {st.session_state.user['full_name']}")
    st.sidebar.write(f"Hospital: {st.session_state.hospital}")  # ✅ FIXED

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.hospital = None
        st.rerun()                                     # ✅ FIXED (was cut off)

    # ── Navigation ────────────────────────────────────────────────
    page = st.sidebar.selectbox("Menu", ["Dashboard", "Patients", "Cultures", "Admin"])

    if page == "Dashboard":
        st.title("📊 Dashboard")
        col1, col2, col3 = st.columns(3)
        patients = get_patients()
        cultures = get_cultures()
        col1.metric("Total Patients", len(patients))
        col2.metric("Total Cultures", len(cultures))
        col3.metric("Hospital", st.session_state.hospital)

    elif page == "Patients":
        st.title("🧑‍⚕️ Patients")
        patients = get_patients()
        if patients:
            st.dataframe(pd.DataFrame(patients))
        else:
            st.info("No patients found.")

        st.subheader("Add Patient")
        with st.form("add_patient_form"):
            name = st.text_input("Full Name")
            dob = st.date_input("Date of Birth")
            ward = st.text_input("Ward")
            submitted = st.form_submit_button("Add Patient")
            if submitted:
                add_patient({
                    "full_name": name,
                    "dob": str(dob),
                    "ward": ward,
                    "hospital": st.session_state.hospital,
                    "created_at": datetime.now().isoformat()
                })
                st.success("Patient added!")
                st.rerun()

    elif page == "Cultures":
        st.title("🧫 Cultures")
        cultures = get_cultures()
        if cultures:
            st.dataframe(pd.DataFrame(cultures))
        else:
            st.info("No cultures found.")

        st.subheader("Add Culture")
        with st.form("add_culture_form"):
            patient_id = st.text_input("Patient ID")
            organism = st.text_input("Organism")
            antibiotic = st.text_input("Antibiotic")
            result = st.selectbox("Result", ["Sensitive", "Resistant", "Intermediate"])
            submitted = st.form_submit_button("Add Culture")
            if submitted:
                add_culture({
                    "patient_id": patient_id,
                    "organism": organism,
                    "antibiotic": antibiotic,
                    "result": result,
                    "hospital": st.session_state.hospital,
                    "created_at": datetime.now().isoformat()
                })
                st.success("Culture added!")
                st.rerun()

    elif page == "Admin":
        st.title("⚙️ Admin - User Management")
        if st.session_state.user.get('role') != 'admin':
            st.warning("Admin access only.")
        else:
            users = get_users()
            if users:
                st.dataframe(pd.DataFrame(users).drop(columns=["password_hash"], errors="ignore"))

            st.subheader("Add User")
            with st.form("add_user_form"):
                full_name = st.text_input("Full Name")
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["viewer", "editor", "admin"])
                hospitals = st.multiselect("Hospitals", ["Tanga RRH", "Bombo Hospital", "Muheza Hospital"])
                submitted = st.form_submit_button("Add User")
                if submitted:
                    add_user({
                        "full_name": full_name,
                        "username": new_username,
                        "password": new_password,
                        "role": role,
                        "hospitals": hospitals
                    })
                    st.success(f"User {new_username} added!")
                    st.rerun()
