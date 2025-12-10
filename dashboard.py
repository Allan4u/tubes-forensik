import streamlit as st
import pandas as pd
import sqlite3
import time
import plotly.express as px
import uuid

st.set_page_config(page_title="LocShield Turbo", layout="wide")
DB_FILE = "locshield.db"

# CSS TEGAS
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #00FF00; font-family: monospace; }
    div[data-testid="stMetricValue"] { color: #00FF00 !important; font-size: 30px; }
    .status-box { padding: 20px; border: 3px solid; text-align: center; font-weight: bold; font-size: 24px; margin-bottom: 20px; }
    .danger { border-color: red; color: red; background-color: #330000; animation: blink 0.5s infinite alternate; }
    .safe { border-color: green; color: green; background-color: #002200; }
    .warning { border-color: yellow; color: yellow; background-color: #333300; }
    @keyframes blink { from {opacity: 1;} to {opacity: 0.5;} }
</style>
""", unsafe_allow_html=True)

st.title("⚡ LOCSHIELD TURBO MONITOR")
placeholder = st.empty()

while True:
    uid = str(uuid.uuid4())[:8]
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC LIMIT 50", conn)
        conn.close()
    except: df = pd.DataFrame()

    with placeholder.container():
        if not df.empty:
            last_event = df.iloc[0]['event']
            
            # LOGIKA STATUS BAR
            if "USER USED FAKE" in last_event or "ATTACKED" in last_event:
                st.markdown(f'<div class="status-box danger">🚨 {last_event}</div>', unsafe_allow_html=True)
            elif "FAKE" in last_event:
                st.markdown(f'<div class="status-box warning">⚠️ WARNING: FAKE GPS ACTIVE</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="status-box safe">✅ SYSTEM SECURE (REAL GPS)</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Events", len(df))
            c2.metric("Threats", len(df[df['risk'] >= 8]))
            c3.metric("Last Details", df.iloc[0]['msg'][:30])

            # TABEL (Paling penting untuk lihat real time)
            def color_row(row):
                if "AMAN" in row['event']: return ['color: #00FF00']*len(row)
                if "FAKE" in row['event']: return ['color: #FFFF00']*len(row)
                if "ATTACK" in row['event'] or "USED" in row['event']: return ['color: #FF0000; font-weight: bold']*len(row)
                return ['']*len(row)

            # Fix warning styler
            try:
                st.dataframe(df[['timestamp', 'event', 'source', 'msg']].style.apply(color_row, axis=1), height=400)
            except:
                st.dataframe(df[['timestamp', 'event', 'source', 'msg']], height=400)
        else:
            st.info("System Ready...")

    time.sleep(0.5) # Refresh rate cepat