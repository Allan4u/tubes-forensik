import streamlit as st
import pandas as pd
import sqlite3
import time
import plotly.express as px
import uuid  # Library untuk membuat ID unik acak

# Konfigurasi Halaman
st.set_page_config(page_title="LocShield Real-Monitor", page_icon="📡", layout="wide")

DB_FILE = "locshield.db"

# CSS Hacker Style
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #00FF00; }
    .stDataFrame { border: 1px solid #00FF00; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
</style>
""", unsafe_allow_html=True)

st.title("📡 LocShield: Real-Time Forensics")
st.markdown("### Status Monitoring: ACTIVE")

# Container utama untuk refresh area
placeholder = st.empty()

while True:
    # 1. BACA DATABASE
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC LIMIT 50", conn)
        conn.close()
    except Exception as e:
        df = pd.DataFrame()

    # 2. GENERATE ID UNIK (PENTING AGAR TIDAK ERROR DUPLICATE)
    # Kita buat ID baru setiap detik agar Streamlit tahu ini update baru
    uid = str(uuid.uuid4())[:8]

    # 3. RENDER TAMPILAN
    with placeholder.container():
        if not df.empty:
            # --- ALERTS ---
            # Cek Fake GPS
            if not df[df['source'].str.contains("fake|mock", case=False, na=False)].empty:
                st.error("🚨 KRITIS: FAKE GPS / MOCK LOCATION DETECTED!")
            
            # Cek Google Maps
            if not df[df['source'].str.contains("maps", case=False, na=False)].empty:
                st.warning("⚠️ Google Maps Tracking Detected")

            # --- METRICS ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Logs", len(df))
            c2.metric("Critical Threats", len(df[df['risk'] >= 8]))
            
            try:
                last_src = df.iloc[0]['source']
            except:
                last_src = "-"
            c3.metric("Last Source", last_src)

            # --- CHARTS ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Source Distribution")
                fig = px.pie(df, names='source', hole=0.5, title="Access Distribution")
                fig.update_layout(paper_bgcolor="#111", font_color="#FFF")
                # PERBAIKAN: Hapus use_container_width, Tambah Key Unik
                st.plotly_chart(fig, key=f"pie_{uid}")
            
            with col2:
                st.subheader("Risk Timeline")
                fig2 = px.scatter(df, x="timestamp", y="risk", color="risk", 
                                  size="risk", hover_data=['source'],
                                  color_continuous_scale=["lime", "yellow", "red"])
                fig2.update_layout(paper_bgcolor="#111", font_color="#FFF")
                # PERBAIKAN: Hapus use_container_width, Tambah Key Unik
                st.plotly_chart(fig2, key=f"scatter_{uid}")

            # --- TABLE ---
            st.subheader("Live Log Stream")
            # PERBAIKAN: Hapus use_container_width (Default sudah lebar)
            st.dataframe(df[['timestamp', 'source', 'event', 'risk', 'msg']], height=300)
            
        else:
            st.info("Menunggu data masuk dari Python Backend...")

    # Refresh Rate 2 Detik
    time.sleep(2)