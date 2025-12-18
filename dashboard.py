import streamlit as st
import pandas as pd
import sqlite3
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid

st.set_page_config(page_title="LocShield Turbo Dashboard", layout="wide", initial_sidebar_state="collapsed")
DB_FILE = "locshield.db"

# CSS ENHANCED
st.markdown("""
<style>
    .stApp { 
        background: linear-gradient(135deg, #000000 0%, #0a0a0a 100%);
        color: #00FF00; 
        font-family: 'Courier New', monospace; 
    }
    div[data-testid="stMetricValue"] { 
        color: #00FF00 !important; 
        font-size: 32px !important;
        font-weight: bold !important;
        text-shadow: 0 0 10px #00FF00;
    }
    div[data-testid="stMetricLabel"] {
        color: #888888 !important;
        font-size: 14px !important;
    }
    .status-box { 
        padding: 25px; 
        border: 4px solid; 
        text-align: center; 
        font-weight: bold; 
        font-size: 28px; 
        margin-bottom: 25px;
        border-radius: 10px;
        box-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    .danger { 
        border-color: #FF0000; 
        color: #FF0000; 
        background: linear-gradient(135deg, #330000 0%, #1a0000 100%);
        animation: blink 0.5s infinite alternate; 
    }
    .safe { 
        border-color: #00FF00; 
        color: #00FF00; 
        background: linear-gradient(135deg, #002200 0%, #001100 100%);
    }
    .warning { 
        border-color: #FFFF00; 
        color: #FFFF00; 
        background: linear-gradient(135deg, #333300 0%, #1a1a00 100%);
        animation: pulse 1s infinite;
    }
    @keyframes blink { 
        from {opacity: 1; transform: scale(1);} 
        to {opacity: 0.6; transform: scale(1.02);} 
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    .metric-card {
        background: #0a0a0a;
        border: 2px solid #333;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    h1, h2, h3 {
        text-shadow: 0 0 10px #00FF00;
    }
    .stDataFrame {
        background: #0a0a0a;
    }
</style>
""", unsafe_allow_html=True)

# Header with timestamp
col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.title("⚡ LOCSHIELD TURBO MONITOR")
with col_header2:
    st.markdown(f"**Live Update:** {datetime.now().strftime('%H:%M:%S')}")

placeholder = st.empty()

# Initialize session state for metrics tracking
if 'previous_threats' not in st.session_state:
    st.session_state.previous_threats = 0
if 'previous_total' not in st.session_state:
    st.session_state.previous_total = 0

while True:
    uid = str(uuid.uuid4())[:8]
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("""
            SELECT id, timestamp, event, source, risk, msg, dread_score 
            FROM logs 
            ORDER BY id DESC 
            LIMIT 100
        """, conn)
        
        # Get statistics
        stats_query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN risk >= 8 THEN 1 ELSE 0 END) as high_threats,
                SUM(CASE WHEN risk >= 5 AND risk < 8 THEN 1 ELSE 0 END) as medium_threats,
                AVG(risk) as avg_risk,
                AVG(dread_score) as avg_dread
            FROM logs
        """
        stats = pd.read_sql_query(stats_query, conn)
        
        # Time-based analysis (last 10 minutes)
        time_query = """
            SELECT timestamp, event, risk 
            FROM logs 
            WHERE id >= (SELECT MAX(id) - 100 FROM logs)
            ORDER BY id DESC
        """
        time_df = pd.read_sql_query(time_query, conn)
        
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")
        df = pd.DataFrame()
        stats = pd.DataFrame({'total': [0], 'high_threats': [0], 'medium_threats': [0], 
                            'avg_risk': [0], 'avg_dread': [0]})
        time_df = pd.DataFrame()

    with placeholder.container():
        if not df.empty:
            last_event = df.iloc[0]['event']
            last_risk = df.iloc[0]['risk']
            last_msg = df.iloc[0]['msg']
            
            # DYNAMIC STATUS BAR
            if "USER USED FAKE" in last_event or "ATTACKED" in last_event:
                st.markdown(f'<div class="status-box danger">🚨 CRITICAL THREAT: {last_event}</div>', 
                          unsafe_allow_html=True)
            elif "FAKE GPS DETECTED" in last_event or "HIGH_FREQ" in last_msg:
                st.markdown(f'<div class="status-box warning">⚠️ WARNING: {last_event}</div>', 
                          unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="status-box safe">✅ SYSTEM SECURE - {last_event}</div>', 
                          unsafe_allow_html=True)

            # METRICS ROW 1
            c1, c2, c3, c4 = st.columns(4)
            
            total_events = int(stats['total'].iloc[0])
            high_threats = int(stats['high_threats'].iloc[0])
            medium_threats = int(stats['medium_threats'].iloc[0])
            avg_risk = float(stats['avg_risk'].iloc[0])
            
            # Calculate deltas
            delta_total = total_events - st.session_state.previous_total
            delta_threats = high_threats - st.session_state.previous_threats
            
            c1.metric("📊 Total Events", f"{total_events}", 
                     delta=f"+{delta_total}" if delta_total > 0 else None)
            c2.metric("🔴 Critical Threats", f"{high_threats}", 
                     delta=f"+{delta_threats}" if delta_threats > 0 else None,
                     delta_color="inverse")
            c3.metric("🟡 Medium Alerts", f"{medium_threats}")
            c4.metric("📈 Avg Risk Score", f"{avg_risk:.1f}/10")
            
            # Update session state
            st.session_state.previous_total = total_events
            st.session_state.previous_threats = high_threats

            # METRICS ROW 2
            st.markdown("---")
            c5, c6, c7, c8 = st.columns(4)
            
            last_dread = df.iloc[0].get('dread_score', 0)
            avg_dread = float(stats['avg_dread'].iloc[0])
            safe_events = len(df[df['event'] == 'AMAN'])
            fake_gps_count = len(df[df['event'].str.contains('FAKE', na=False)])
            
            c5.metric("🎯 Last DREAD Score", f"{last_dread}/50")
            c6.metric("📊 Avg DREAD", f"{avg_dread:.1f}/50")
            c7.metric("✅ Safe Events", f"{safe_events}")
            c8.metric("🎭 Fake GPS Detections", f"{fake_gps_count}")

            st.markdown("---")

            # CHARTS
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.subheader("📊 Risk Distribution")
                risk_dist = df['risk'].value_counts().sort_index()
                fig_risk = px.bar(
                    x=risk_dist.index, 
                    y=risk_dist.values,
                    labels={'x': 'Risk Level', 'y': 'Count'},
                    color=risk_dist.values,
                    color_continuous_scale=['green', 'yellow', 'orange', 'red']
                )
                fig_risk.update_layout(
                    plot_bgcolor='#0a0a0a',
                    paper_bgcolor='#0a0a0a',
                    font_color='#00FF00',
                    showlegend=False,
                    height=300
                )
                st.plotly_chart(fig_risk, use_container_width=True)
            
            with chart_col2:
                st.subheader("📈 Event Types")
                event_counts = df['event'].value_counts().head(5)
                fig_events = px.pie(
                    values=event_counts.values,
                    names=event_counts.index,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_events.update_layout(
                    plot_bgcolor='#0a0a0a',
                    paper_bgcolor='#0a0a0a',
                    font_color='#00FF00',
                    height=300
                )
                st.plotly_chart(fig_events, use_container_width=True)

            st.markdown("---")
            
            # REAL-TIME EVENT LOG
            st.subheader("📡 Real-Time Event Stream")
            
            # Color-coded dataframe
            def style_row(row):
                if row['risk'] >= 8:
                    return ['background-color: #330000; color: #FF0000; font-weight: bold'] * len(row)
                elif row['risk'] >= 5:
                    return ['background-color: #333300; color: #FFFF00'] * len(row)
                elif 'AMAN' in str(row['event']):
                    return ['background-color: #002200; color: #00FF00'] * len(row)
                return ['background-color: #0a0a0a; color: #888888'] * len(row)

            # Display styled dataframe
            display_df = df[['timestamp', 'event', 'source', 'risk', 'dread_score', 'msg']].head(50)
            
            try:
                styled_df = display_df.style.apply(style_row, axis=1)
                st.dataframe(styled_df, height=400, use_container_width=True)
            except:
                st.dataframe(display_df, height=400, use_container_width=True)
            
            # THREAT TIMELINE
            if not time_df.empty and len(time_df) > 1:
                st.markdown("---")
                st.subheader("⏱️ Threat Timeline (Last 100 Events)")
                
                # Prepare timeline data
                time_df['id'] = range(len(time_df), 0, -1)
                fig_timeline = px.line(
                    time_df, 
                    x='id', 
                    y='risk',
                    title='Risk Level Over Time',
                    labels={'id': 'Event Sequence', 'risk': 'Risk Level'}
                )
                fig_timeline.add_hline(y=8, line_dash="dash", line_color="red", 
                                      annotation_text="Critical Threshold")
                fig_timeline.add_hline(y=5, line_dash="dash", line_color="yellow", 
                                      annotation_text="Medium Threshold")
                fig_timeline.update_layout(
                    plot_bgcolor='#0a0a0a',
                    paper_bgcolor='#0a0a0a',
                    font_color='#00FF00',
                    height=300
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

        else:
            st.info("🟢 System Ready - Waiting for events...")
            st.markdown("""
            ### Quick Start Guide:
            1. ✅ Make sure `engine.py` is running
            2. ✅ Android device/emulator connected via ADB
            3. ✅ Start monitoring for location access events
            4. ✅ This dashboard will auto-update every 0.5s
            """)

    time.sleep(0.5)  # Fast refresh rate for real-time monitoring