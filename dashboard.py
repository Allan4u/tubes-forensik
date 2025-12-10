import streamlit as st
import pandas as pd
import sqlite3
import time
import plotly.express as px
import uuid

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="LocShield Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_FILE = "locshield.db"

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp {
        background-color: #050505;
        color: #00FF41;
        font-family: 'Courier New', Courier, monospace;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        text-shadow: 0 0 10px rgba(0, 255, 65, 0.7);
        color: #00FF41 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #aaaaaa;
        font-weight: bold;
    }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        font-weight: bold;
        font-size: 24px;
        border: 2px solid;
    }
    .safe {
        background-color: rgba(0, 255, 65, 0.1);
        border-color: #00FF41;
        color: #00FF41;
        box-shadow: 0 0 15px #00FF41;
    }
    .warning {
        background-color: rgba(255, 215, 0, 0.1);
        border-color: #FFD700;
        color: #FFD700;
        box-shadow: 0 0 15px #FFD700;
    }
    .danger {
        background-color: rgba(255, 0, 0, 0.2);
        border-color: #FF0000;
        color: #FF0000;
        box-shadow: 0 0 25px #FF0000;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI BACA DATA ---
def get_data():
    try:
        conn = sqlite3.connect(DB_FILE)
        # Ambil 100 log terakhir
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC LIMIT 100", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

# --- MAIN LOOP ---
st.title("🛡️ LOCSHIELD: INTELLIGENCE DASHBOARD")
st.markdown("---")

placeholder = st.empty()

while True:
    # 1. Generate ID Unik (Mencegah error duplicate key)
    uid = str(uuid.uuid4())[:8]
    
    # 2. Baca Data
    df = get_data()

    with placeholder.container():
        if not df.empty:
            # --- STATUS MONITOR ---
            try:
                last_event = df.iloc[0]['event']
            except:
                last_event = "UNKNOWN"
            
            status_html = ""
            if "USER USED FAKE" in last_event or "ATTACKED" in last_event:
                status_html = f"""<div class="status-box danger">🚨 SYSTEM COMPROMISED 🚨<br>{last_event} DETECTED</div>"""
            elif "FAKE GPS" in last_event:
                status_html = f"""<div class="status-box warning">⚠️ INTEGRITY RISK ⚠️<br>FAKE GPS TOOLS ACTIVE</div>"""
            else:
                status_html = f"""<div class="status-box safe">✅ SYSTEM SECURE ✅<br>MONITORING ACTIVE</div>"""
            
            st.markdown(status_html, unsafe_allow_html=True)

            # --- METRICS ---
            c1, c2, c3, c4 = st.columns(4)
            
            total_logs = len(df)
            spoof_count = len(df[df['event'].str.contains("FAKE", na=False)])
            compromised_count = len(df[df['event'].str.contains("USER USED FAKE", na=False)])
            try:
                risk_val = df.iloc[0]['risk']
            except:
                risk_val = 0
            
            c1.metric("Total Logs", total_logs)
            c2.metric("Spoofing Attempts", spoof_count)
            c3.metric("Maps Compromised", compromised_count)
            c4.metric("Risk Level", risk_val)

            # --- GRAFIK ---
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Target Distribution")
                color_map = {
                    "AMAN": "#00FF41",
                    "FAKE GPS DETECTED": "#FFD700", 
                    "ATTACKED": "#FF0000",
                    "USER USED FAKE GPS TO MAPS": "#8800FF"
                }
                fig = px.pie(df, names='event', hole=0.6, title="Event Types", color='event', color_discrete_map=color_map)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", showlegend=False)
                
                # PERBAIKAN: Hapus parameter use_container_width
                st.plotly_chart(fig, theme="streamlit", key=f"pie_{uid}")

            with col2:
                st.subheader("Real-Time Threat Timeline")
                fig2 = px.scatter(df, x="timestamp", y="risk", color="event", size="risk", hover_data=['source', 'msg'], title="Risk Intensity")
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#333'))
                
                # PERBAIKAN: Hapus parameter use_container_width
                st.plotly_chart(fig2, theme="streamlit", key=f"scatter_{uid}")

            # --- TABEL ---
            st.subheader("Intercepted Log Data")
            
            def highlight_risk(val):
                color = 'white'
                if val >= 8: color = '#FF0000'
                elif val >= 5: color = '#FFD700'
                return f'color: {color}'

            # PERBAIKAN: Ganti applymap ke map (Pandas baru)
            try:
                styled_df = df[['timestamp', 'event', 'source', 'risk', 'msg']].style.map(highlight_risk, subset=['risk'])
                st.dataframe(styled_df, height=300)
            except:
                st.dataframe(df[['timestamp', 'event', 'source', 'risk', 'msg']], height=300)

        else:
            st.info("Waiting for Backend Engine to send data...")

    # Jeda 1 detik
    time.sleep(1)