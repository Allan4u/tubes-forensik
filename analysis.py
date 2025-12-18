import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
from datetime import datetime
import numpy as np

# Set style
plt.style.use('dark_background')
sns.set_palette("husl")

DB_FILE = "locshield.db"

def load_data():
    """Load data from SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("""
            SELECT id, timestamp, event, source, risk, msg, dread_score 
            FROM logs 
            ORDER BY id ASC
        """, conn)
        conn.close()
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], format='%H:%M:%S', errors='coerce')
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def calculate_metrics(df, label="Overall"):
    """Calculate key metrics for comparison"""
    metrics = {
        'label': label,
        'total_events': len(df),
        'critical_threats': len(df[df['risk'] >= 8]),
        'medium_threats': len(df[(df['risk'] >= 5) & (df['risk'] < 8)]),
        'low_threats': len(df[df['risk'] < 5]),
        'avg_risk': df['risk'].mean() if len(df) > 0 else 0,
        'max_risk': df['risk'].max() if len(df) > 0 else 0,
        'avg_dread': df['dread_score'].mean() if len(df) > 0 else 0,
        'fake_gps_count': len(df[df['event'].str.contains('FAKE', na=False)]),
        'attack_count': len(df[df['event'].str.contains('ATTACK', na=False)]),
        'safe_events': len(df[df['event'] == 'AMAN']),
    }
    return metrics

def plot_comparison(before_df, after_df, output_file='comparison_before_after.png'):
    """Create before vs after comparison charts"""
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('LocShield Turbo - Before vs After Mitigation Analysis', 
                 fontsize=20, fontweight='bold', color='#00FF00')
    
    # Calculate metrics
    before_metrics = calculate_metrics(before_df, "Before Mitigation")
    after_metrics = calculate_metrics(after_df, "After Mitigation")
    
    # 1. Total Events Comparison
    ax1 = axes[0, 0]
    categories = ['Total Events', 'Critical', 'Medium', 'Low']
    before_vals = [before_metrics['total_events'], before_metrics['critical_threats'], 
                   before_metrics['medium_threats'], before_metrics['low_threats']]
    after_vals = [after_metrics['total_events'], after_metrics['critical_threats'], 
                  after_metrics['medium_threats'], after_metrics['low_threats']]
    
    x = np.arange(len(categories))
    width = 0.35
    ax1.bar(x - width/2, before_vals, width, label='Before', color='#FF4444')
    ax1.bar(x + width/2, after_vals, width, label='After', color='#44FF44')
    ax1.set_xlabel('Category', fontsize=12)
    ax1.set_ylabel('Count', fontsize=12)
    ax1.set_title('Event Count Comparison', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=45)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Risk Score Distribution
    ax2 = axes[0, 1]
    risk_bins = [0, 3, 5, 8, 10]
    risk_labels = ['Low (0-3)', 'Medium (3-5)', 'High (5-8)', 'Critical (8-10)']
    
    before_risk_dist = pd.cut(before_df['risk'], bins=risk_bins, labels=risk_labels).value_counts()
    after_risk_dist = pd.cut(after_df['risk'], bins=risk_bins, labels=risk_labels).value_counts()
    
    before_risk_dist.plot(kind='bar', ax=ax2, alpha=0.7, color='#FF4444', width=0.4, position=0, label='Before')
    after_risk_dist.plot(kind='bar', ax=ax2, alpha=0.7, color='#44FF44', width=0.4, position=1, label='After')
    ax2.set_xlabel('Risk Category', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('Risk Distribution', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Average Risk & DREAD
    ax3 = axes[0, 2]
    metrics_comp = ['Avg Risk', 'Avg DREAD']
    before_avg = [before_metrics['avg_risk'], before_metrics['avg_dread']/5]  # Normalize DREAD to 0-10
    after_avg = [after_metrics['avg_risk'], after_metrics['avg_dread']/5]
    
    x = np.arange(len(metrics_comp))
    ax3.bar(x - width/2, before_avg, width, label='Before', color='#FF4444')
    ax3.bar(x + width/2, after_avg, width, label='After', color='#44FF44')
    ax3.set_xlabel('Metric', fontsize=12)
    ax3.set_ylabel('Score (0-10)', fontsize=12)
    ax3.set_title('Average Scores Comparison', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(metrics_comp)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=5, color='yellow', linestyle='--', alpha=0.5, label='Threshold')
    
    # 4. Threat Timeline - Before
    ax4 = axes[1, 0]
    if len(before_df) > 0:
        ax4.plot(before_df.index, before_df['risk'], color='#FF4444', linewidth=2, alpha=0.7)
        ax4.fill_between(before_df.index, before_df['risk'], alpha=0.3, color='#FF4444')
        ax4.axhline(y=8, color='red', linestyle='--', alpha=0.5, label='Critical')
        ax4.axhline(y=5, color='yellow', linestyle='--', alpha=0.5, label='Medium')
    ax4.set_xlabel('Event Sequence', fontsize=12)
    ax4.set_ylabel('Risk Level', fontsize=12)
    ax4.set_title('Risk Timeline - Before Mitigation', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. Threat Timeline - After
    ax5 = axes[1, 1]
    if len(after_df) > 0:
        ax5.plot(after_df.index, after_df['risk'], color='#44FF44', linewidth=2, alpha=0.7)
        ax5.fill_between(after_df.index, after_df['risk'], alpha=0.3, color='#44FF44')
        ax5.axhline(y=8, color='red', linestyle='--', alpha=0.5, label='Critical')
        ax5.axhline(y=5, color='yellow', linestyle='--', alpha=0.5, label='Medium')
    ax5.set_xlabel('Event Sequence', fontsize=12)
    ax5.set_ylabel('Risk Level', fontsize=12)
    ax5.set_title('Risk Timeline - After Mitigation', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 6. Event Type Distribution
    ax6 = axes[1, 2]
    
    # Get top 5 event types for each
    before_events = before_df['event'].value_counts().head(5)
    after_events = after_df['event'].value_counts().head(5)
    
    # Combine for comparison
    all_events = set(before_events.index) | set(after_events.index)
    event_comparison = pd.DataFrame({
        'Before': [before_events.get(e, 0) for e in all_events],
        'After': [after_events.get(e, 0) for e in all_events]
    }, index=list(all_events))
    
    event_comparison.plot(kind='barh', ax=ax6, color=['#FF4444', '#44FF44'], alpha=0.7)
    ax6.set_xlabel('Count', fontsize=12)
    ax6.set_ylabel('Event Type', fontsize=12)
    ax6.set_title('Event Type Distribution', fontsize=14, fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"✓ Chart saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("METRICS SUMMARY")
    print("="*70)
    print(f"\n{'Metric':<30} {'Before':>15} {'After':>15} {'Change':>15}")
    print("-"*70)
    
    for key in ['total_events', 'critical_threats', 'medium_threats', 'avg_risk', 'avg_dread']:
        before_val = before_metrics[key]
        after_val = after_metrics[key]
        change = after_val - before_val
        change_pct = (change / before_val * 100) if before_val != 0 else 0
        
        if 'avg' in key:
            print(f"{key:<30} {before_val:>15.2f} {after_val:>15.2f} {change:>+10.2f} ({change_pct:+.1f}%)")
        else:
            print(f"{key:<30} {before_val:>15.0f} {after_val:>15.0f} {change:>+10.0f} ({change_pct:+.1f}%)")
    
    print("="*70 + "\n")
    
    return fig

def plot_dread_analysis(df, output_file='dread_analysis.png'):
    """Analyze DREAD scores"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('DREAD Score Analysis', fontsize=18, fontweight='bold', color='#00FF00')
    
    # 1. DREAD Score Distribution
    ax1 = axes[0]
    dread_bins = [0, 10, 20, 30, 40, 50]
    dread_labels = ['Low (0-10)', 'Medium (10-20)', 'High (20-30)', 'Very High (30-40)', 'Critical (40-50)']
    dread_dist = pd.cut(df['dread_score'], bins=dread_bins, labels=dread_labels).value_counts()
    
    colors = ['#44FF44', '#FFFF44', '#FF8844', '#FF4444', '#AA0000']
    dread_dist.plot(kind='bar', ax=ax1, color=colors, alpha=0.8)
    ax1.set_xlabel('DREAD Category', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('DREAD Score Distribution', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Risk vs DREAD Correlation
    ax2 = axes[1]
    scatter = ax2.scatter(df['risk'], df['dread_score'], 
                         c=df['dread_score'], cmap='RdYlGn_r', 
                         s=100, alpha=0.6, edgecolors='white', linewidth=0.5)
    ax2.set_xlabel('Risk Score (0-10)', fontsize=12)
    ax2.set_ylabel('DREAD Score (0-50)', fontsize=12)
    ax2.set_title('Risk vs DREAD Correlation', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add trendline
    if len(df) > 1:
        z = np.polyfit(df['risk'], df['dread_score'], 1)
        p = np.poly1d(z)
        ax2.plot(df['risk'], p(df['risk']), "r--", alpha=0.8, linewidth=2, label='Trend')
        ax2.legend()
    
    plt.colorbar(scatter, ax=ax2, label='DREAD Score')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"✓ DREAD analysis saved to: {output_file}")
    
    return fig

def plot_access_rate(df, output_file='access_rate.png'):
    """Plot GPS access rate over time"""
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle('GPS Access Rate Analysis', fontsize=18, fontweight='bold', color='#00FF00')
    
    # Calculate rolling access rate (events per minute)
    window_size = 60  # 60 events window
    if len(df) > window_size:
        df['rolling_rate'] = df['id'].rolling(window=window_size).count()
        
        ax.plot(df.index, df['rolling_rate'], color='#00FFFF', linewidth=2, alpha=0.8)
        ax.fill_between(df.index, df['rolling_rate'], alpha=0.3, color='#00FFFF')
        
        # Add threshold line
        ax.axhline(y=50, color='red', linestyle='--', linewidth=2, alpha=0.7, label='DoS Threshold (50/min)')
        
        ax.set_xlabel('Event Sequence', fontsize=12)
        ax.set_ylabel('Access Rate (events per window)', fontsize=12)
        ax.set_title('GPS Access Frequency Over Time', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'Insufficient data for rate analysis', 
               ha='center', va='center', fontsize=16, color='#888888')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"✓ Access rate chart saved to: {output_file}")
    
    return fig

def main():
    """Main analysis function"""
    print("\n" + "="*70)
    print("🔍 LOCSHIELD TURBO - METRICS ANALYSIS")
    print("="*70 + "\n")
    
    # Load all data
    df = load_data()
    
    if df.empty:
        print("❌ No data found in database!")
        return
    
    print(f"✓ Loaded {len(df)} events from database")
    
    # Split into before/after based on attack events
    attack_start = df[df['event'].str.contains('ATTACK', na=False)].index.min() if len(df[df['event'].str.contains('ATTACK', na=False)]) > 0 else len(df)
    attack_end = df[df['event'].str.contains('ATTACK', na=False)].index.max() if len(df[df['event'].str.contains('ATTACK', na=False)]) > 0 else len(df)
    
    before_df = df[:attack_start] if attack_start > 0 else df[:len(df)//2]
    during_df = df[attack_start:attack_end+1] if attack_start < len(df) else pd.DataFrame()
    after_df = df[attack_end+1:] if attack_end < len(df)-1 else df[len(df)//2:]
    
    print(f"✓ Before attack: {len(before_df)} events")
    print(f"✓ During attack: {len(during_df)} events")
    print(f"✓ After mitigation: {len(after_df)} events\n")
    
    # Generate charts
    print("Generating comparison charts...")
    plot_comparison(before_df, after_df)
    
    print("Generating DREAD analysis...")
    plot_dread_analysis(df)
    
    print("Generating access rate analysis...")
    plot_access_rate(df)
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print("  • comparison_before_after.png")
    print("  • dread_analysis.png")
    print("  • access_rate.png")
    print("\nUse these charts in your report/video demo!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()