import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import hashlib

# ── STEP 1: Paste your values directly here to test ──────────────
# Once working, move these to Streamlit secrets and use st.secrets
SUPABASE_URL = "https://labpsrmioeelgukybsqo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhYnBzcm1pb2VlbGd1a3lic3FvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2NTkzOTAsImV4cCI6MjA5MzIzNTM5MH0.zdZZGJQ0_ivn1MWHVMIaqcCqj56DE7J9eZdn36yDmek"

# ── STEP 2: Create client ─────────────────────────────────────────
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ Failed to create Supabase client: {e}")
    st.stop()

# ── STEP 3: Fix RLS — run this ONCE in Supabase SQL Editor ────────
# ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
# ALTER TABLE public.patients DISABLE ROW LEVEL SECURITY;
# ALTER TABLE public.cultures DISABLE ROW LEVEL SECURITY;

# ── Helpers ───────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password, hospital):
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("username", username)
            .execute()
        )
        result = response.data
        if not result:
            return None
        user = result[0]
        if (user.get("password_hash") == hash_password(password) and
                hospital in user.get("hospitals", [])):
            return user
        return None
    except Exception as e:
        st.error(f"❌ Auth error: {e}")
        return None

def get_users():
    try:
        return supabase.table("users").select("*").execute().data or []
    except Exception as e:
        st.error(f"❌ get_users error: {e}")
        return []

def get_patients():
    try:
        return supabase.table("patients").select("*").execute().data or []
    except Exception as e:
        st.error(f"❌ get_patients error: {e}")
        return []

def get_cultures():
    try:
        return supabase.table("cultures").select("*").execute().data or []
    except Exception as e:
        st.error(f"❌ get_cultures error: {e}")
        return []

def add_user(data):
    try:
        data["password_hash"] = hash_password(data.pop("password"))
        return supabase.table("users").insert(data).execute().data
    except Exception as e:
        st.error(f"❌ add_user error: {e}")

def add_patient(data):
    try:
        return supabase.table("patients").insert(data).execute().data
    except Exception as e:
        st.error(f"❌ add_patient error: {e}")

def add_culture(data):
    try:
        return supabase.table("cultures").insert(data).execute().data
    except Exception as e:
        st.error(f"❌ add_culture error: {e}")

# ── App config ────────────────────────────────────────────────────
st.set_page_config(page_title="Huduma Poa AMS", layout="wide")

# ── Session state init ────────────────────────────────────────────
for key, val in [("logged_in", False), ("user", None), ("hospital", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Login page ────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.title("🏥 Huduma Poa AMS - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        hospital = st.selectbox("Hospital", [
            "Tanga RRH", "Bombo Hospital", "Muheza Hospital"
        ])
        submit = st.form_submit_button("Login")

        if submit:
            user = authenticate_user(username, password, hospital)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.hospital = hospital
                st.rerun()
            else:
                st.error("❌ Invalid credentials or hospital access")

# ── Main app ──────────────────────────────────────────────────────
else:
    st.sidebar.title(f"👤 {st.session_state.user.get('full_name', 'User')}")
    st.sidebar.write(f"🏥 {st.session_state.hospital}")

    if st.sidebar.button("Logout"):
        for key in ["logged_in", "user", "hospital"]:
            st.session_state[key] = None
        st.session_state.logged_in = False
        st.rerun()

    page = st.sidebar.selectbox("Menu", [
        "Dashboard", "Patients", "Cultures", "Admin"
    ])

    # ── Dashboard ─────────────────────────────────────────────────
    if page == "Dashboard":
        st.title("📊 Dashboard")
        patients = get_patients()
        cultures = get_cultures()
        c1, c2, c3 = st.columns(3)
        c1.metric("Patients", len(patients))
        c2.metric("Cultures", len(cultures))
        c3.metric("Hospital", st.session_state.hospital)

    # ── Patients ──────────────────────────────────────────────────
    elif page == "Patients":
        st.title("🧑‍⚕️ Patients")
        patients = get_patients()
        if patients:
            st.dataframe(pd.DataFrame(patients), use_container_width=True)
        else:
            st.info("No patients found.")

        st.subheader("Add Patient")
        with st.form("add_patient_form"):
            name    = st.text_input("Full Name")
            dob     = st.date_input("Date of Birth")
            ward    = st.text_input("Ward")
            if st.form_submit_button("Add Patient"):
                add_patient({
                    "full_name":   name,
                    "dob":         str(dob),
                    "ward":        ward,
                    "hospital":    st.session_state.hospital,
                    "created_at":  datetime.now().isoformat()
                })
                st.success("✅ Patient added!")
                st.rerun()

    # ── Cultures ──────────────────────────────────────────────────
    elif page == "Cultures":
        st.title("🧫 Cultures")
        cultures = get_cultures()
        if cultures:
            st.dataframe(pd.DataFrame(cultures), use_container_width=True)
        else:
            st.info("No cultures found.")

        st.subheader("Add Culture")
        with st.form("add_culture_form"):
            patient_id = st.text_input("Patient ID")
            organism   = st.text_input("Organism")
            antibiotic = st.text_input("Antibiotic")
            result     = st.selectbox("Result", ["Sensitive", "Resistant", "Intermediate"])
            if st.form_submit_button("Add Culture"):
                add_culture({
                    "patient_id":  patient_id,
                    "organism":    organism,
                    "antibiotic":  antibiotic,
                    "result":      result,
                    "hospital":    st.session_state.hospital,
                    "created_at":  datetime.now().isoformat()
                })
                st.success("✅ Culture added!")
                st.rerun()

    # ── Admin ─────────────────────────────────────────────────────
    elif page == "Admin":
        st.title("⚙️ Admin")
        if st.session_state.user.get("role") != "admin":
            st.warning("⛔ Admin access only.")
        else:
            users = get_users()
            if users:
                st.dataframe(
                    pd.DataFrame(users).drop(columns=["password_hash"], errors="ignore"),
                    use_container_width=True
                )
            st.subheader("Add User")
            with st.form("add_user_form"):
                full_name    = st.text_input("Full Name")
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                role         = st.selectbox("Role", ["viewer", "editor", "admin"])
                hospitals    = st.multiselect("Hospitals", [
                    "Tanga RRH", "Bombo Hospital", "Muheza Hospital"
                ])
                if st.form_submit_button("Add User"):
                    add_user({
                        "full_name": full_name,
                        "username":  new_username,
                        "password":  new_password,
                        "role":      role,
                        "hospitals": hospitals
                    })
                    st.success(f"✅ User {new_username} added!")
                    st.rerun()
