import streamlit as st
import pandas as pd
import json
import hashlib
import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AMS Tool",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "ams_local.db"
HOSPITALS = ["Tanga RRH", "Bombo Hospital", "Muheza Hospital"]

# ─────────────────────────────────────────────────────────────────
# WHO REFERENCE DATA
# ─────────────────────────────────────────────────────────────────
ORGANISMS = [
    "Escherichia coli", "Klebsiella pneumoniae", "Staphylococcus aureus (MRSA)",
    "Staphylococcus aureus (MSSA)", "Streptococcus pneumoniae", "Pseudomonas aeruginosa",
    "Acinetobacter baumannii", "Enterococcus faecalis", "Enterococcus faecium",
    "Salmonella typhi", "Salmonella non-typhi", "Shigella spp.",
    "Neisseria gonorrhoeae", "Neisseria meningitidis", "Haemophilus influenzae",
    "Mycobacterium tuberculosis", "Candida albicans", "Candida auris",
    "Cryptococcus neoformans", "Plasmodium falciparum", "Other"
]

INFECTIONS = [
    "Community-acquired pneumonia (CAP)", "Hospital-acquired pneumonia (HAP)",
    "Ventilator-associated pneumonia (VAP)", "Urinary tract infection (UTI)",
    "Catheter-associated UTI (CAUTI)", "Bloodstream infection / Septicaemia",
    "Central line-associated BSI (CLABSI)", "Surgical site infection (SSI)",
    "Intra-abdominal infection", "Skin & soft tissue infection (SSTI)",
    "Meningitis / CNS infection", "Endocarditis", "Bone & joint infection",
    "Neonatal sepsis", "Typhoid fever", "Dysentery / Diarrhoeal disease",
    "Malaria", "Tuberculosis", "STI / Gonorrhoea", "Fungal infection", "Other"
]

ANTIBIOTICS = [
    "Amoxicillin", "Amoxicillin-Clavulanate", "Ampicillin", "Piperacillin-Tazobactam",
    "Cefazolin", "Cefuroxime", "Ceftriaxone", "Cefotaxime", "Ceftazidime",
    "Cefepime", "Meropenem", "Imipenem", "Ertapenem",
    "Ciprofloxacin", "Levofloxacin", "Moxifloxacin",
    "Gentamicin", "Amikacin", "Tobramycin",
    "Vancomycin", "Teicoplanin", "Linezolid",
    "Metronidazole", "Clindamycin", "Azithromycin", "Doxycycline",
    "Trimethoprim-Sulfamethoxazole", "Nitrofurantoin", "Colistin",
    "Fluconazole", "Amphotericin B", "Other"
]

WARDS = [
    "Medical Ward", "Surgical Ward", "Paediatric Ward", "Neonatal ICU (NICU)",
    "ICU / HDU", "Maternity Ward", "Orthopaedic Ward", "TB Ward",
    "Oncology Ward", "Emergency / Casualty", "Outpatient Department (OPD)", "Other"
]

SENSITIVITY = ["Sensitive (S)", "Intermediate (I)", "Resistant (R)", "Not tested"]

TREATMENT_GUIDELINES = {
    "Community-acquired pneumonia (CAP)": {
        "first_line": "Amoxicillin 500mg TDS x 5 days",
        "second_line": "Azithromycin 500mg OD x 5 days (atypical cover)",
        "severe": "Ceftriaxone 1g IV OD + Azithromycin 500mg IV OD",
        "who_note": "WHO AWaRe: Access antibiotics preferred. Reserve carbapenems for MDR organisms.",
        "duration": "5–7 days standard, 7–10 days severe"
    },
    "Urinary tract infection (UTI)": {
        "first_line": "Nitrofurantoin 100mg BD x 5 days (uncomplicated)",
        "second_line": "Trimethoprim-Sulfamethoxazole 960mg BD x 3 days",
        "severe": "Ceftriaxone 1g IV OD x 7–14 days (pyelonephritis)",
        "who_note": "Avoid fluoroquinolones as first-line to preserve Watch antibiotics.",
        "duration": "3–5 days uncomplicated, 7–14 days complicated"
    },
    "Bloodstream infection / Septicaemia": {
        "first_line": "Ceftriaxone 2g IV OD (pending cultures)",
        "second_line": "Piperacillin-Tazobactam 4.5g IV TDS (nosocomial)",
        "severe": "Meropenem 1g IV TDS (Reserve – MDR / critical)",
        "who_note": "De-escalate within 48–72h based on culture results. Source control essential.",
        "duration": "7–14 days depending on source and organism"
    },
    "Surgical site infection (SSI)": {
        "first_line": "Cefazolin 1g IV pre-op prophylaxis (within 60min)",
        "second_line": "Clindamycin 600mg IV (penicillin allergy)",
        "severe": "Piperacillin-Tazobactam + Metronidazole (deep/organ SSI)",
        "who_note": "Prophylaxis is single dose. Prolonged prophylaxis not recommended.",
        "duration": "Prophylaxis: single dose. Treatment: 5–14 days"
    },
    "Meningitis / CNS infection": {
        "first_line": "Ceftriaxone 2g IV BD x 10–14 days",
        "second_line": "Add Ampicillin 2g IV 4-hourly if Listeria suspected (age >50)",
        "severe": "Dexamethasone 0.15mg/kg QDS x 4 days (bacterial meningitis)",
        "who_note": "Steroids reduce mortality in bacterial meningitis. Do LP before antibiotics if safe.",
        "duration": "10–14 days bacterial, 14–21 days Listeria"
    },
    "Typhoid fever": {
        "first_line": "Azithromycin 1g OD x 5–7 days (uncomplicated)",
        "second_line": "Ceftriaxone 2g IV OD x 10–14 days (severe)",
        "severe": "Meropenem for XDR typhoid",
        "who_note": "Fluoroquinolone resistance common in East Africa. Avoid empirical fluoroquinolones.",
        "duration": "5–7 days uncomplicated, 10–14 days severe"
    },
}

WARD_ROUND_QUESTIONS = [
    {"q": "Is the patient on antibiotics?", "options": ["Yes", "No"]},
    {"q": "Is there a documented indication for antibiotic use?", "options": ["Yes", "No", "Unclear"]},
    {"q": "Has a culture specimen been collected BEFORE antibiotics?", "options": ["Yes", "No", "Not applicable"]},
    {"q": "What is the route of administration?", "options": ["IV", "Oral", "IV → Oral step-down", "IM"]},
    {"q": "Is IV-to-oral switch appropriate?", "options": ["Yes – switch now", "No – IV still needed", "Not applicable"]},
    {"q": "Is the antibiotic on the WHO Access list?", "options": ["Yes (Access)", "No (Watch)", "No (Reserve)", "Unknown"]},
    {"q": "Is the dose correct for patient weight/renal function?", "options": ["Yes", "No – needs adjustment", "Not checked"]},
    {"q": "Has the duration been documented?", "options": ["Yes – stop date set", "No stop date", "Unclear"]},
    {"q": "Has the treatment been reviewed in last 48–72h?", "options": ["Yes – reviewed", "No – not reviewed", "Day 1–2 (review due)"]},
    {"q": "Is de-escalation possible based on culture results?", "options": ["Yes – de-escalate", "No – escalate needed", "Awaiting cultures", "Not applicable"]},
    {"q": "Are there signs of clinical improvement?", "options": ["Yes – improving", "No – not improving", "Deteriorating"]},
    {"q": "Is there any antibiotic allergy documented?", "options": ["No known allergy", "Allergy documented", "Not checked"]},
]

IPC_CHECKLIST = [
    "Hand hygiene compliance observed in ward",
    "PPE available and used correctly",
    "Isolation precautions in place for known MDR organisms",
    "IV line / catheter insertion site reviewed",
    "Wound care and dressing adequacy assessed",
    "Environmental cleaning adequate",
    "Sharps disposal appropriate",
    "Visitors briefed on infection control measures",
]

# ─────────────────────────────────────────────────────────────────
# LOCAL DATABASE (SQLite — offline first)
# ─────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'viewer',
        hospitals TEXT DEFAULT '[]',
        designation TEXT,
        phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        patient_id TEXT,
        age INTEGER,
        sex TEXT,
        ward TEXT,
        hospital TEXT,
        admission_date TEXT,
        diagnosis TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS cultures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT,
        patient_name TEXT,
        specimen_type TEXT,
        organism TEXT,
        antibiotic TEXT,
        sensitivity TEXT,
        ward TEXT,
        hospital TEXT,
        collected_by TEXT,
        collection_date TEXT,
        report_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ward_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ward TEXT,
        hospital TEXT,
        conducted_by TEXT,
        round_date TEXT,
        answers TEXT,
        insights TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        meeting_date TEXT,
        hospital TEXT,
        attendees TEXT,
        agenda TEXT,
        minutes TEXT,
        action_points TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS pharmacy_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hospital TEXT,
        upload_date TEXT,
        uploaded_by TEXT,
        data TEXT,
        summary TEXT
    )""")

    # Default admin
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("""INSERT OR IGNORE INTO users 
        (full_name, username, password_hash, role, hospitals, designation)
        VALUES (?, ?, ?, ?, ?, ?)""",
        ("System Admin", "admin", admin_hash, "admin",
         json.dumps(HOSPITALS), "AMS Coordinator"))

    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

# ─────────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────────
def authenticate_user(username, password, hospital):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        if not row: return None
        cols = ["id","full_name","username","password_hash","role","hospitals","designation","phone","created_at"]
        user = dict(zip(cols, row))
        hospitals = json.loads(user["hospitals"])
        if user["password_hash"] == hash_password(password) and hospital in hospitals:
            return user
        return None
    except Exception as e:
        st.error(f"Auth error: {e}")
        return None

def db_fetch(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def db_execute(query, params=()):
    conn = get_conn()
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def get_users():
    return db_fetch("SELECT id,full_name,username,role,hospitals,designation,phone,created_at FROM users")

def get_patients(hospital):
    return db_fetch("SELECT * FROM patients WHERE hospital=? ORDER BY created_at DESC", (hospital,))

def get_cultures(hospital):
    return db_fetch("SELECT * FROM cultures WHERE hospital=? ORDER BY created_at DESC", (hospital,))

def get_ward_rounds(hospital):
    return db_fetch("SELECT * FROM ward_rounds WHERE hospital=? ORDER BY round_date DESC", (hospital,))

def get_meetings(hospital):
    return db_fetch("SELECT * FROM meetings WHERE hospital=? ORDER BY meeting_date DESC", (hospital,))

# ─────────────────────────────────────────────────────────────────
# SUPABASE SYNC (when online)
# ─────────────────────────────────────────────────────────────────
def try_supabase_sync():
    try:
        from supabase import create_client
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if url and key and url.startswith("https://"):
            return create_client(url, key)
    except:
        pass
    return None

# ─────────────────────────────────────────────────────────────────
# INSIGHTS ENGINE
# ─────────────────────────────────────────────────────────────────
def generate_insights(answers):
    insights = []
    a = answers

    if a.get("Is the patient on antibiotics?") == "Yes":
        if a.get("Has a culture specimen been collected BEFORE antibiotics?") == "No":
            insights.append("⚠️ CRITICAL: Culture not collected before antibiotics — compromises diagnostic accuracy.")
        if a.get("Is there a documented indication for antibiotic use?") != "Yes":
            insights.append("🔴 No documented indication — consider stopping or justifying antibiotic use.")
        if a.get("Is IV-to-oral switch appropriate?") == "Yes – switch now":
            insights.append("✅ IV-to-oral switch recommended — reduces cost, complications and hospital stay.")
        if a.get("Is the antibiotic on the WHO Access list?") in ["No (Watch)", "No (Reserve)"]:
            insights.append("⚠️ Watch/Reserve antibiotic in use — ensure justified indication and review at 48–72h.")
        if a.get("Has the duration been documented?") == "No stop date":
            insights.append("🔴 No stop date set — antibiotic overuse risk. Document duration today.")
        if a.get("Has the treatment been reviewed in last 48–72h?") == "No – not reviewed":
            insights.append("⚠️ No 48–72h review — mandatory for all antibiotic courses. Review now.")
        if a.get("Is de-escalation possible based on culture results?") == "Yes – de-escalate":
            insights.append("✅ De-escalation possible — narrow spectrum based on sensitivity report.")
        if a.get("Are there signs of clinical improvement?") == "No – not improving":
            insights.append("🔴 Not improving — reassess diagnosis, check cultures, consider escalation or ID consult.")
        if a.get("Is the dose correct for patient weight/renal function?") == "No – needs adjustment":
            insights.append("⚠️ Dose adjustment needed — consult renal dosing guidelines or pharmacist.")

    if not insights:
        insights.append("✅ No immediate AMS concerns identified in this round.")

    return insights

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --accent: #2ea043;
    --accent2: #388bfd;
    --warn: #d29922;
    --danger: #f85149;
    --text: #e6edf3;
    --muted: #8b949e;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background-color: var(--bg); }

.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}
.metric-card .val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2.2rem;
    font-weight: 500;
    color: var(--accent);
}
.metric-card .label {
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 4px;
}

.insight-box {
    background: var(--surface);
    border-left: 3px solid var(--accent2);
    border-radius: 0 6px 6px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.9rem;
}

.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
}

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 500;
}
.badge-green { background: rgba(46,160,67,0.15); color: #2ea043; border: 1px solid rgba(46,160,67,0.3); }
.badge-blue  { background: rgba(56,139,253,0.15); color: #388bfd; border: 1px solid rgba(56,139,253,0.3); }
.badge-warn  { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
.badge-red   { background: rgba(248,81,73,0.15);  color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────
init_db()

for k, v in [("logged_in", False), ("user", None), ("hospital", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Logo / Branding ──────────────────────────────────────
        st.markdown("""
        <div style='text-align:center; margin-bottom:8px;'>
            <div style='font-size:3rem;'>🏥</div>
            <div style='font-family:"IBM Plex Mono",monospace; font-size:1.6rem;
                        font-weight:600; color:#e6edf3; letter-spacing:0.04em;'>
                AMS Tool
            </div>
            <div style='color:#8b949e; font-size:0.85rem; margin-top:4px;'>
                Antimicrobial Stewardship Intelligence Platform
            </div>
            <div style='color:#388bfd; font-size:0.75rem; margin-top:2px;
                        font-family:"IBM Plex Mono",monospace; letter-spacing:0.08em;'>
                Tanga · Bombo · Muheza
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Disclaimer ───────────────────────────────────────────
        st.markdown("""
        <div style='background:#161b22; border:1px solid #d29922; border-radius:8px;
                    padding:12px 16px; margin:12px 0; font-size:0.78rem; color:#d29922;'>
            <b>⚠️ Clinical Disclaimer</b><br>
            This tool provides decision support based on WHO AMS guidelines and local
            treatment protocols. It does <b>not</b> replace clinical judgement. All
            prescribing decisions must be made by a qualified, licensed healthcare
            professional. Data entered is confidential and intended for authorised
            AMS team members only.
        </div>
        """, unsafe_allow_html=True)

        # ── Login Form ───────────────────────────────────────────
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            hospital = st.selectbox("Hospital", HOSPITALS)
            submit   = st.form_submit_button("Login →", use_container_width=True)
            if submit:
                user = authenticate_user(username, password, hospital)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.hospital = hospital
                    st.rerun()
                else:
                    st.error("Invalid credentials or no access to this hospital.")

        # ── Footer ───────────────────────────────────────────────
        st.markdown("""
        <div style='text-align:center; margin-top:20px; padding-top:16px;
                    border-top:1px solid #30363d;'>
            <div style='color:#8b949e; font-size:0.72rem; letter-spacing:0.05em;'>
                Developed by <b style='color:#e6edf3;'>Odieman</b> &nbsp;|&nbsp;
                <a href='mailto:emmanuelodie94@gmail.com'
                   style='color:#388bfd; text-decoration:none;'>
                   emmanuelodie94@gmail.com
                </a>
            </div>
            <div style='color:#30363d; font-size:0.65rem; margin-top:4px;'>
                © 2025 AMS Tool · All rights reserved
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.stop()

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
user = st.session_state.user
hospital = st.session_state.hospital

with st.sidebar:
    st.markdown(f"**{user['full_name']}**")
    st.markdown(f"<span style='color:#8b949e;font-size:0.85rem'>{user.get('designation','')}</span>", unsafe_allow_html=True)
    st.markdown(f"<span class='badge badge-blue'>{hospital}</span>", unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio("Navigation", [
        "📊 Dashboard",
        "🧫 Laboratory",
        "💊 Pharmacy",
        "🏃 Ward Rounds",
        "🛡️ IPC",
        "📋 Meetings",
        "👥 Team",
        "📚 Guidelines",
        "⚙️ Admin"
    ])

    st.markdown("---")
    sync = try_supabase_sync()
    if sync:
        st.markdown("<span class='badge badge-green'>🟢 Online — Synced</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge badge-warn'>🟡 Offline — Local DB</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Logout", use_container_width=True):
        for k in ["logged_in","user","hospital"]:
            st.session_state[k] = None
        st.session_state.logged_in = False
        st.rerun()

    st.markdown("""
    <div style="margin-top:32px; padding-top:12px; border-top:1px solid #21262d; text-align:center;">
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.6rem; color:#21262d;
                    letter-spacing:0.15em; text-transform:uppercase; margin-bottom:2px;">
            Developed by
        </div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.85rem; font-weight:700;
                    color:#30363d; letter-spacing:0.2em; text-transform:uppercase;">
            ODIEMAN
        </div>
        <div style="margin-top:4px;">
            <a href="mailto:emmanuelodie94@gmail.com"
               style="color:#388bfd; font-size:0.65rem; text-decoration:none; opacity:0.7;">
               emmanuelodie94@gmail.com
            </a>
        </div>
        <div style="color:#21262d; font-size:0.58rem; margin-top:4px;">
            &copy; 2025 AMS Tool
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.title("📊 AMS Dashboard")
    st.markdown(f"<p style='color:#8b949e'>{hospital} · {datetime.now().strftime('%d %B %Y')}</p>", unsafe_allow_html=True)

    patients  = get_patients(hospital)
    cultures  = get_cultures(hospital)
    rounds    = get_ward_rounds(hospital)
    meetings  = get_meetings(hospital)

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in [
        (c1, len(patients),  "Patients Registered"),
        (c2, len(cultures),  "Culture Records"),
        (c3, len(rounds),    "Ward Rounds"),
        (c4, len(meetings),  "AMS Meetings"),
    ]:
        col.markdown(f"""<div class='metric-card'>
            <div class='val'>{val}</div>
            <div class='label'>{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not cultures.empty and "organism" in cultures.columns:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='section-header'>Top Organisms Isolated</div>", unsafe_allow_html=True)
            org_counts = cultures["organism"].value_counts().head(8).reset_index()
            org_counts.columns = ["Organism", "Count"]
            fig = px.bar(org_counts, x="Count", y="Organism", orientation="h",
                         color_discrete_sequence=["#2ea043"])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#e6edf3", margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("<div class='section-header'>Sensitivity Distribution</div>", unsafe_allow_html=True)
            if "sensitivity" in cultures.columns:
                sens = cultures["sensitivity"].value_counts().reset_index()
                sens.columns = ["Result", "Count"]
                fig2 = px.pie(sens, values="Count", names="Result",
                              color_discrete_sequence=["#2ea043","#d29922","#f85149","#8b949e"])
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e6edf3",
                                   margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig2, use_container_width=True)

    if not cultures.empty and "antibiotic" in cultures.columns and "sensitivity" in cultures.columns:
        st.markdown("<div class='section-header'>Mini Antibiogram</div>", unsafe_allow_html=True)
        try:
            pivot = cultures.groupby(["organism","antibiotic","sensitivity"]).size().reset_index(name="n")
            total = pivot.groupby(["organism","antibiotic"])["n"].sum().reset_index(name="total")
            sens_only = pivot[pivot["sensitivity"].str.startswith("S")].groupby(["organism","antibiotic"])["n"].sum().reset_index(name="sensitive")
            merged = total.merge(sens_only, on=["organism","antibiotic"], how="left").fillna(0)
            merged["%S"] = (merged["sensitive"] / merged["total"] * 100).round(0)
            heat = merged.pivot(index="organism", columns="antibiotic", values="%S")
            fig3 = px.imshow(heat, color_continuous_scale="RdYlGn", aspect="auto",
                             title="% Susceptibility by Organism × Antibiotic")
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e6edf3",
                               margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig3, use_container_width=True)
        except:
            st.info("Add more culture records to generate the antibiogram.")

# ─────────────────────────────────────────────────────────────────
# LABORATORY
# ─────────────────────────────────────────────────────────────────
elif page == "🧫 Laboratory":
    st.title("🧫 Laboratory — Culture & Sensitivity")
    tab1, tab2, tab3 = st.tabs(["Add Result", "All Records", "Antibiogram"])

    with tab1:
        st.markdown("<div class='section-header'>New Culture & Sensitivity Result</div>", unsafe_allow_html=True)
        with st.form("culture_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_id   = st.text_input("Patient ID / IP Number")
                p_name = st.text_input("Patient Name")
                ward   = st.selectbox("Ward", WARDS)
                spec   = st.selectbox("Specimen Type", [
                    "Blood", "Urine", "Sputum", "Wound Swab", "CSF",
                    "Stool", "Pus", "Tracheal Aspirate", "Other"])
                org    = st.selectbox("Organism Isolated", ORGANISMS)
            with c2:
                ab     = st.selectbox("Antibiotic Tested", ANTIBIOTICS)
                sens   = st.selectbox("Sensitivity Result", SENSITIVITY)
                cdate  = st.date_input("Collection Date", date.today())
                rdate  = st.date_input("Report Date", date.today())
                notes  = st.text_area("Notes / Additional Sensitivities")

            if st.form_submit_button("Save Culture Result", use_container_width=True):
                db_execute("""INSERT INTO cultures
                    (patient_id,patient_name,specimen_type,organism,antibiotic,
                     sensitivity,ward,hospital,collected_by,collection_date,report_date,notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (p_id, p_name, spec, org, ab, sens, ward, hospital,
                     user["full_name"], str(cdate), str(rdate), notes))
                st.success("✅ Culture result saved.")
                st.rerun()

    with tab2:
        df = get_cultures(hospital)
        if not df.empty:
            st.dataframe(df.drop(columns=["id"], errors="ignore"), use_container_width=True)
            csv = df.to_csv(index=False).encode()
            st.download_button("⬇️ Export CSV", csv, "cultures.csv", "text/csv")
        else:
            st.info("No culture records yet.")

    with tab3:
        df = get_cultures(hospital)
        if not df.empty and "organism" in df.columns:
            st.markdown("#### Antibiogram — % Susceptibility")
            try:
                pivot = df.groupby(["organism","antibiotic","sensitivity"]).size().reset_index(name="n")
                total = pivot.groupby(["organism","antibiotic"])["n"].sum().reset_index(name="total")
                sens_only = pivot[pivot["sensitivity"].str.startswith("S")].groupby(["organism","antibiotic"])["n"].sum().reset_index(name="sensitive")
                merged = total.merge(sens_only, on=["organism","antibiotic"], how="left").fillna(0)
                merged["%S"] = (merged["sensitive"] / merged["total"] * 100).round(0)
                heat = merged.pivot(index="organism", columns="antibiotic", values="%S")
                fig = px.imshow(heat, color_continuous_scale="RdYlGn", aspect="auto",
                                text_auto=True, title="Antibiogram — % Susceptibility")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e6edf3")
                st.plotly_chart(fig, use_container_width=True)
                csv = merged.to_csv(index=False).encode()
                st.download_button("⬇️ Export Antibiogram", csv, "antibiogram.csv", "text/csv")
            except Exception as e:
                st.error(f"Could not render antibiogram: {e}")
        else:
            st.info("Add culture records to generate the antibiogram.")

# ─────────────────────────────────────────────────────────────────
# PHARMACY
# ─────────────────────────────────────────────────────────────────
elif page == "💊 Pharmacy":
    st.title("💊 Pharmacy — Antibiotic Consumption Analysis")
    tab1, tab2 = st.tabs(["Upload & Analyse", "WHO AWaRe Classification"])

    with tab1:
        st.markdown("<div class='section-header'>Upload Pharmacy Dispensing Data (Excel)</div>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx","xls","csv"])

        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)

                st.markdown("**Preview:**")
                st.dataframe(df.head(20), use_container_width=True)
                st.markdown(f"**Rows:** {len(df)} | **Columns:** {', '.join(df.columns.tolist())}")

                # Auto-detect antibiotic column
                ab_col = next((c for c in df.columns if any(
                    k in c.lower() for k in ["antibiotic","drug","medicine","item"])), None)
                qty_col = next((c for c in df.columns if any(
                    k in c.lower() for k in ["qty","quantity","dispensed","count","units"])), None)

                if ab_col:
                    st.markdown("<div class='section-header'>Consumption Analysis</div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        top = df[ab_col].value_counts().head(10).reset_index()
                        top.columns = ["Antibiotic","Count"]
                        fig = px.bar(top, x="Count", y="Antibiotic", orientation="h",
                                     color_discrete_sequence=["#388bfd"],
                                     title="Top 10 Antibiotics Dispensed")
                        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e6edf3")
                        st.plotly_chart(fig, use_container_width=True)

                    with c2:
                        # WHO AWaRe classification
                        access = ["Amoxicillin","Ampicillin","Cefazolin","Ceftriaxone","Metronidazole",
                                  "Trimethoprim-Sulfamethoxazole","Nitrofurantoin","Doxycycline","Clindamycin"]
                        watch  = ["Ciprofloxacin","Levofloxacin","Vancomycin","Cefepime","Piperacillin-Tazobactam",
                                  "Azithromycin","Ceftazidime","Meropenem"]
                        reserve= ["Colistin","Linezolid","Ceftazidime-Avibactam","Fosfomycin"]

                        def classify(name):
                            n = str(name).lower()
                            for a in access:
                                if a.lower() in n: return "Access"
                            for w in watch:
                                if w.lower() in n: return "Watch"
                            for r in reserve:
                                if r.lower() in n: return "Reserve"
                            return "Unclassified"

                        df["AWaRe"] = df[ab_col].apply(classify)
                        aware_counts = df["AWaRe"].value_counts().reset_index()
                        aware_counts.columns = ["Category","Count"]
                        fig2 = px.pie(aware_counts, values="Count", names="Category",
                                      color_discrete_map={"Access":"#2ea043","Watch":"#d29922",
                                                          "Reserve":"#f85149","Unclassified":"#8b949e"},
                                      title="WHO AWaRe Distribution")
                        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e6edf3")
                        st.plotly_chart(fig2, use_container_width=True)

                    access_pct = (df["AWaRe"]=="Access").sum() / len(df) * 100
                    if access_pct >= 60:
                        st.success(f"✅ Access antibiotic use: {access_pct:.1f}% — meets WHO target (≥60%)")
                    else:
                        st.warning(f"⚠️ Access antibiotic use: {access_pct:.1f}% — below WHO target of 60%. Review Watch/Reserve prescribing.")

            except Exception as e:
                st.error(f"Could not read file: {e}")

    with tab2:
        st.markdown("### WHO AWaRe Classification Guide")
        data = {
            "Category": ["Access","Access","Access","Watch","Watch","Watch","Reserve","Reserve"],
            "Antibiotic": ["Amoxicillin","Ceftriaxone","Metronidazole",
                           "Ciprofloxacin","Vancomycin","Meropenem",
                           "Colistin","Linezolid"],
            "Notes": [
                "First-line for common infections",
                "Broad spectrum — use with indication",
                "Anaerobic cover",
                "Restrict — fluoroquinolone resistance rising",
                "MRSA / serious Gram-positive infections",
                "Reserve for MDR Gram-negatives only",
                "Last resort — nephrotoxic",
                "MDR Gram-positive only"
            ]
        }
        st.dataframe(pd.DataFrame(data), use_container_width=True)

# ─────────────────────────────────────────────────────────────────
# WARD ROUNDS
# ─────────────────────────────────────────────────────────────────
elif page == "🏃 Ward Rounds":
    st.title("🏃 Smart Ward Rounds")
    tab1, tab2 = st.tabs(["Conduct Round", "Previous Rounds"])

    with tab1:
        st.markdown("<div class='section-header'>New Ward Round</div>", unsafe_allow_html=True)
        ward  = st.selectbox("Ward", WARDS)
        rdate = st.date_input("Date", date.today())

        st.markdown("**Per-ward AMS Questionnaire**")
        answers = {}
        for item in WARD_ROUND_QUESTIONS:
            answers[item["q"]] = st.selectbox(item["q"], item["options"])

        if st.button("Generate Insights & Save Round", use_container_width=True):
            insights = generate_insights(answers)
            st.markdown("### 💡 AMS Insights")
            for ins in insights:
                st.markdown(f"<div class='insight-box'>{ins}</div>", unsafe_allow_html=True)

            db_execute("""INSERT INTO ward_rounds
                (ward,hospital,conducted_by,round_date,answers,insights)
                VALUES (?,?,?,?,?,?)""",
                (ward, hospital, user["full_name"], str(rdate),
                 json.dumps(answers), json.dumps(insights)))
            st.success("✅ Ward round saved.")

    with tab2:
        df = get_ward_rounds(hospital)
        if not df.empty:
            for _, row in df.iterrows():
                with st.expander(f"📋 {row['ward']} — {row['round_date']} (by {row['conducted_by']})"):
                    ins = json.loads(row["insights"]) if row["insights"] else []
                    for i in ins:
                        st.markdown(f"<div class='insight-box'>{i}</div>", unsafe_allow_html=True)
        else:
            st.info("No ward rounds recorded yet.")

# ─────────────────────────────────────────────────────────────────
# IPC
# ─────────────────────────────────────────────────────────────────
elif page == "🛡️ IPC":
    st.title("🛡️ Infection Prevention & Control")
    tab1, tab2 = st.tabs(["IPC Checklist", "MDR Alert"])

    with tab1:
        st.markdown("<div class='section-header'>IPC Ward Assessment Checklist</div>", unsafe_allow_html=True)
        ward  = st.selectbox("Ward", WARDS)
        rdate = st.date_input("Assessment Date", date.today())
        results = {}
        for item in IPC_CHECKLIST:
            results[item] = st.selectbox(item, ["Yes ✅", "No ❌", "Partial ⚠️", "N/A"])

        if st.button("Save IPC Assessment"):
            score = sum(1 for v in results.values() if v.startswith("Yes"))
            total = sum(1 for v in results.values() if not v.endswith("N/A"))
            pct = score/total*100 if total else 0
            if pct >= 80:
                st.success(f"✅ IPC compliance: {pct:.0f}% — Good")
            elif pct >= 60:
                st.warning(f"⚠️ IPC compliance: {pct:.0f}% — Needs improvement")
            else:
                st.error(f"🔴 IPC compliance: {pct:.0f}% — Urgent action required")
            st.json(results)

    with tab2:
        st.markdown("<div class='section-header'>MDR Organism Alert</div>", unsafe_allow_html=True)
        cultures = get_cultures(hospital)
        if not cultures.empty:
            mdr_orgs = ["MRSA", "Acinetobacter", "Pseudomonas", "Klebsiella", "Candida auris"]
            mdr = cultures[cultures["organism"].str.contains("|".join(mdr_orgs), case=False, na=False)]
            if not mdr.empty:
                st.error(f"🔴 {len(mdr)} MDR organism(s) detected in recent cultures!")
                st.dataframe(mdr[["patient_name","organism","ward","collection_date"]], use_container_width=True)
            else:
                st.success("✅ No MDR organisms detected in current records.")

# ─────────────────────────────────────────────────────────────────
# MEETINGS
# ─────────────────────────────────────────────────────────────────
elif page == "📋 Meetings":
    st.title("📋 Smart AMS Meetings")
    tab1, tab2 = st.tabs(["New Meeting", "Meeting Records"])

    with tab1:
        with st.form("meeting_form"):
            title     = st.text_input("Meeting Title", f"AMS Meeting — {hospital}")
            mdate     = st.date_input("Date", date.today())
            attendees = st.text_area("Attendees (one per line)")
            agenda    = st.text_area("Agenda")
            minutes   = st.text_area("Minutes / Discussion")
            actions   = st.text_area("Action Points")

            if st.form_submit_button("Save Meeting Record", use_container_width=True):
                db_execute("""INSERT INTO meetings
                    (title,meeting_date,hospital,attendees,agenda,minutes,action_points,created_by)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (title, str(mdate), hospital, attendees, agenda, minutes, actions, user["full_name"]))
                st.success("✅ Meeting record saved.")
                st.rerun()

    with tab2:
        df = get_meetings(hospital)
        if not df.empty:
            for _, row in df.iterrows():
                with st.expander(f"📋 {row['title']} — {row['meeting_date']}"):
                    st.markdown(f"**Attendees:**\n{row['attendees']}")
                    st.markdown(f"**Agenda:**\n{row['agenda']}")
                    st.markdown(f"**Minutes:**\n{row['minutes']}")
                    st.markdown(f"**Action Points:**\n{row['action_points']}")
        else:
            st.info("No meetings recorded yet.")

# ─────────────────────────────────────────────────────────────────
# TEAM
# ─────────────────────────────────────────────────────────────────
elif page == "👥 Team":
    st.title("👥 AMS Team Members")
    tab1, tab2 = st.tabs(["Team List", "Add / Remove Member"])

    with tab1:
        users_df = get_users()
        if not users_df.empty:
            st.dataframe(users_df.drop(columns=["password_hash"], errors="ignore"), use_container_width=True)

    with tab2:
        if user["role"] != "admin":
            st.warning("Admin access required.")
        else:
            st.markdown("<div class='section-header'>Add Team Member</div>", unsafe_allow_html=True)
            with st.form("add_user_form"):
                c1, c2 = st.columns(2)
                with c1:
                    full_name   = st.text_input("Full Name")
                    username    = st.text_input("Username")
                    password    = st.text_input("Password", type="password")
                    designation = st.selectbox("Designation", [
                        "AMS Coordinator","Infectious Disease Physician","Microbiologist",
                        "Clinical Pharmacist","Infection Control Nurse","Ward Doctor",
                        "Nursing Officer","Lab Technician","Other"])
                with c2:
                    role      = st.selectbox("Role", ["viewer","editor","admin"])
                    hospitals = st.multiselect("Hospital Access", HOSPITALS)
                    phone     = st.text_input("Phone")

                if st.form_submit_button("Add Member", use_container_width=True):
                    try:
                        db_execute("""INSERT INTO users
                            (full_name,username,password_hash,role,hospitals,designation,phone)
                            VALUES (?,?,?,?,?,?,?)""",
                            (full_name, username, hash_password(password),
                             role, json.dumps(hospitals), designation, phone))
                        st.success(f"✅ {full_name} added.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.markdown("<div class='section-header'>Remove Member</div>", unsafe_allow_html=True)
            users_df = get_users()
            if not users_df.empty:
                to_del = st.selectbox("Select user to remove",
                    users_df[users_df["username"] != "admin"]["username"].tolist())
                if st.button("🗑️ Remove Member"):
                    db_execute("DELETE FROM users WHERE username=?", (to_del,))
                    st.success(f"Removed {to_del}.")
                    st.rerun()

# ─────────────────────────────────────────────────────────────────
# GUIDELINES
# ─────────────────────────────────────────────────────────────────
elif page == "📚 Guidelines":
    st.title("📚 Treatment Guidelines & WHO References")
    tab1, tab2, tab3 = st.tabs(["Treatment Guidelines", "Organism Reference", "SOPs"])

    with tab1:
        infection = st.selectbox("Select Infection / Syndrome", list(TREATMENT_GUIDELINES.keys()))
        g = TREATMENT_GUIDELINES[infection]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**🟢 First-line:** {g['first_line']}")
            st.markdown(f"**🟡 Second-line:** {g['second_line']}")
            st.markdown(f"**🔴 Severe / IV:** {g['severe']}")
        with c2:
            st.markdown(f"**⏱️ Duration:** {g['duration']}")
            st.markdown(f"<div class='insight-box'>🌍 <b>WHO AWaRe Note:</b> {g['who_note']}</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("### Organism → Common Infections")
        data = {
            "Organism": ["E. coli","Klebsiella pneumoniae","S. aureus (MRSA)","S. pneumoniae",
                         "Pseudomonas aeruginosa","Acinetobacter baumannii","Candida auris"],
            "Common Infections": [
                "UTI, BSI, intra-abdominal",
                "Pneumonia, BSI, UTI, liver abscess",
                "Skin/soft tissue, BSI, endocarditis, pneumonia",
                "CAP, meningitis, otitis media",
                "HAP/VAP, BSI, UTI (ICU)",
                "HAP/VAP, BSI (MDR in ICU)",
                "Fungaemia, wound infection (MDR)"
            ],
            "WHO Priority": ["Critical","Critical","High","High","Critical","Critical","Critical"]
        }
        st.dataframe(pd.DataFrame(data), use_container_width=True)

    with tab3:
        st.markdown("### Standard Operating Procedures")
        sops = {
            "Blood Culture Collection": "Collect 2 sets (aerobic + anaerobic) from 2 different sites. Clean skin with 70% alcohol + 2% chlorhexidine. Inoculate bottles before starting antibiotics.",
            "Urine Culture": "Midstream clean-catch. Process within 2h or refrigerate. Catheter specimens from sampling port, not bag.",
            "IV-to-Oral Switch Criteria": "Patient afebrile >24h, tolerating oral intake, no bacteraemia, improving clinically, equivalent oral bioavailability available.",
            "Antibiotic Time-out (48–72h)": "Review: Is there still an indication? Is the spectrum appropriate? Can we de-escalate? Is the duration defined? Document review in notes.",
            "MDR Organism Management": "Notify IPC team immediately. Implement contact precautions. Dedicate equipment. Notify ward staff and admissions. Report to national surveillance.",
            "Carbapenem Stewardship": "Carbapenems are Reserve antibiotics. Require ID physician or AMS team authorisation. Review daily. De-escalate when possible.",
        }
        for title, content in sops.items():
            with st.expander(f"📄 {title}"):
                st.markdown(content)

# ─────────────────────────────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────────────────────────────
elif page == "⚙️ Admin":
    st.title("⚙️ System Administration")
    if user["role"] != "admin":
        st.warning("⛔ Admin access only.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Add Patient", "Database Stats", "Supabase Sync"])

    with tab1:
        st.markdown("<div class='section-header'>Register Patient</div>", unsafe_allow_html=True)
        with st.form("add_patient_form"):
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("Full Name")
                p_id   = st.text_input("IP / OP Number")
                age    = st.number_input("Age", 0, 120, 30)
                sex    = st.selectbox("Sex", ["Male","Female","Other"])
            with c2:
                ward   = st.selectbox("Ward", WARDS)
                adm    = st.date_input("Admission Date", date.today())
                diag   = st.selectbox("Primary Diagnosis / Infection", INFECTIONS)

            if st.form_submit_button("Register Patient", use_container_width=True):
                db_execute("""INSERT INTO patients
                    (full_name,patient_id,age,sex,ward,hospital,admission_date,diagnosis)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (p_name, p_id, age, sex, ward, hospital, str(adm), diag))
                st.success("✅ Patient registered.")
                st.rerun()

    with tab2:
        st.markdown("<div class='section-header'>Database Statistics</div>", unsafe_allow_html=True)
        tables = ["users","patients","cultures","ward_rounds","meetings"]
        for t in tables:
            df = db_fetch(f"SELECT COUNT(*) as n FROM {t}")
            st.markdown(f"**{t}:** {df['n'][0]} records")
        db_size = os.path.getsize(DB_PATH) / 1024
        st.markdown(f"**DB size:** {db_size:.1f} KB")

    with tab3:
        st.markdown("<div class='section-header'>Supabase Cloud Sync</div>", unsafe_allow_html=True)
        st.markdown("Add credentials to `.streamlit/secrets.toml` to enable cloud sync:")
        st.code("""SUPABASE_URL = "https://your-project.supabase.co"\nSUPABASE_KEY = "your-anon-key" """, language="toml")
        sync = try_supabase_sync()
        if sync:
            st.success("✅ Supabase connected — sync available.")
        else:
            st.warning("🟡 No Supabase connection — running in offline mode. All data saved locally.")
