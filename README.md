[README.md](https://github.com/user-attachments/files/27294975/README.md)
# 🏥 Huduma Poa AMS — Antimicrobial Stewardship Intelligence Platform

## Features
- 📊 Dashboard with live antibiogram and organism analytics
- 🧫 Laboratory: culture & sensitivity entry, full antibiogram heatmap
- 💊 Pharmacy: Excel upload, WHO AWaRe classification, consumption analysis
- 🏃 Smart Ward Rounds: per-ward questionnaire with automated AMS insights
- 🛡️ IPC: checklist + MDR organism alerts
- 📋 Smart Meetings: record agenda, minutes, action points
- 👥 Team management: register/remove AMS members
- 📚 WHO treatment guidelines, organism reference, SOPs
- ✅ Offline-first (SQLite) with optional Supabase cloud sync

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run locally
```bash
streamlit run odieman-ams-intelligence.py
```

### 3. Default login
- **Username:** admin  
- **Password:** admin123  
- **Hospital:** Tanga RRH

## Deploying to Streamlit Cloud

### Secrets (.streamlit/secrets.toml)
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

Without secrets, the app runs fully offline using local SQLite.

## Supabase Setup (optional — for cloud sync)
Run `supabase_schema.sql` once in your Supabase SQL Editor.

## Hospitals
- Tanga RRH
- Bombo Hospital  
- Muheza Hospital
