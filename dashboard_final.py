import streamlit as st
import pandas as pd
import sqlite3
import time
import plotly.express as px
import uuid

st.set_page_config(page_title="LocShield Monitor", layout="wide")
DB_FILE = "locshield.db"

# CSS Hacker Style
st.markdown("""<style>.stApp { background-color: #000000; color: #00FF00; } div[data-testid="stMetricValue"] { color: #00FF00; }</style>""", unsafe_allow_html=True)

st.title("📡 LocShield: Real-Time Forensics")
placeholder = st.empty()

while True:
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC LIMIT 50", conn)
        conn.close()
    except: df = pd.DataFrame()
    
    uid = str(uuid.uuid4())[:8] # Unik ID tiap detik

    with placeholder.container():
        if not df.empty:
            # Alerts
            if not df[df['source'].str.contains("fake|mock", case=False, na=False)].empty:
                st.error("🚨 KRITIS: FAKE GPS/MOCK LOCATION DETECTED!")
            
            # Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Logs", len(df))
            c2.metric("Critical Threats", len(df[df['risk'] >= 8]))
            c3.metric("Last Source", df.iloc[0]['source'])

            # Charts
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(df, names='source', hole=0.5, title="Access Distribution")
                fig.update_layout(paper_bgcolor="#111", font_color="#FFF")
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{uid}")
            with col2:
                fig2 = px.scatter(df, x="timestamp", y="risk", color="risk", color_continuous_scale=["lime", "red"])
                fig2.update_layout(paper_bgcolor="#111", font_color="#FFF")
                st.plotly_chart(fig2, use_container_width=True, key=f"scat_{uid}")

            st.dataframe(df[['timestamp', 'source', 'event', 'risk', 'msg']], use_container_width=True)
        else:
            st.info("Waiting for data...")
    time.sleep(1)