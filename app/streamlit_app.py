"""
Gaming LiveOps Analytics Dashboard
"""
import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from pathlib import Path
import yaml
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Gaming LiveOps Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Connect to DuckDB
@st.cache_resource
def get_connection():
    db_path = Path(config['paths']['warehouse']) / 'gaming_analytics.duckdb'
    return duckdb.connect(str(db_path), read_only=True)

con = get_connection()

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🎮 Gaming Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📊 Executive Dashboard", "💰 Monetization", "📱 Platform Analysis", "🔄 Retention & Engagement"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")

# Date filter
min_date = con.execute("SELECT MIN(session_date) FROM fact_sessions").fetchone()[0]
max_date = con.execute("SELECT MAX(session_date) FROM fact_sessions").fetchone()[0]

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Platform filter
platforms = con.execute("SELECT DISTINCT platform FROM dim_players ORDER BY platform").fetchdf()
selected_platforms = st.sidebar.multiselect(
    "Platform",
    options=platforms['platform'].tolist(),
    default=platforms['platform'].tolist()
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Use filters to drill down into specific segments!")

# ==================== PAGE 1: EXECUTIVE DASHBOARD ====================
if page == "📊 Executive Dashboard":
    st.title("🎮 Gaming LiveOps - Executive Dashboard")
    st.markdown("### Real-time KPIs and Performance Metrics")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    # DAU
    dau = con.execute(f"""
        SELECT COUNT(DISTINCT s.player_id) as dau
        FROM fact_sessions s
        JOIN dim_players p ON s.player_id = p.player_id
        WHERE s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0]
    
    col1.metric("👥 Daily Active Users", f"{dau:,}")
    
    # Total Sessions
    total_sessions = con.execute(f"""
        SELECT COUNT(*) 
        FROM fact_sessions s
        JOIN dim_players p ON s.player_id = p.player_id
        WHERE s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0]
    
    col2.metric("🎮 Total Sessions", f"{total_sessions:,}")
    
    # Revenue
    revenue = con.execute(f"""
        SELECT COALESCE(SUM(pur.price_usd), 0)
        FROM fact_purchases pur
        JOIN dim_players p ON pur.player_id = p.player_id
        WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0] or 0
    
    col3.metric("💰 Total Revenue", f"${revenue:,.2f}")
    
    # ARPPU
    paying_users = con.execute(f"""
        SELECT COUNT(DISTINCT pur.player_id)
        FROM fact_purchases pur
        JOIN dim_players p ON pur.player_id = p.player_id
        WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0] or 0
    
    arppu = revenue / paying_users if paying_users > 0 else 0
    col4.metric("📊 ARPPU", f"${arppu:.2f}")
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Daily Active Users Trend")
        dau_trend = con.execute(f"""
            SELECT 
                session_date,
                COUNT(DISTINCT s.player_id) as dau
            FROM fact_sessions s
            JOIN dim_players p ON s.player_id = p.player_id
            WHERE s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
            GROUP BY session_date
            ORDER BY session_date
        """).fetchdf()
        
        fig = px.line(dau_trend, x='session_date', y='dau', 
                     title='Daily Active Users',
                     labels={'session_date': 'Date', 'dau': 'DAU'})
        fig.update_traces(line_color='#667eea', line_width=3)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💵 Daily Revenue")
        revenue_trend = con.execute(f"""
            SELECT 
                purchase_date,
                SUM(pur.price_usd) as revenue
            FROM fact_purchases pur
            JOIN dim_players p ON pur.player_id = p.player_id
            WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
            GROUP BY purchase_date
            ORDER BY purchase_date
        """).fetchdf()
        
        fig = px.bar(revenue_trend, x='purchase_date', y='revenue',
                    title='Daily Revenue',
                    labels={'purchase_date': 'Date', 'revenue': 'Revenue ($)'})
        fig.update_traces(marker_color='#52c41a')
        st.plotly_chart(fig, use_container_width=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏱️ Session Duration Distribution")
        duration_dist = con.execute(f"""
            SELECT 
                CASE 
                    WHEN duration_minutes < 5 THEN '0-5 min'
                    WHEN duration_minutes < 15 THEN '5-15 min'
                    WHEN duration_minutes < 30 THEN '15-30 min'
                    WHEN duration_minutes < 60 THEN '30-60 min'
                    ELSE '60+ min'
                END as duration_bucket,
                COUNT(*) as sessions
            FROM fact_sessions s
            JOIN dim_players p ON s.player_id = p.player_id
            WHERE s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
            GROUP BY duration_bucket
        """).fetchdf()
        
        fig = px.pie(duration_dist, values='sessions', names='duration_bucket',
                    title='Session Duration Distribution')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🌍 Top Countries by Players")
        country_stats = con.execute(f"""
            SELECT 
                country,
                COUNT(DISTINCT s.player_id) as players
            FROM fact_sessions s
            JOIN dim_players p ON s.player_id = p.player_id
            WHERE s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
            GROUP BY country
            ORDER BY players DESC
            LIMIT 10
        """).fetchdf()
        
        fig = px.bar(country_stats, x='players', y='country', orientation='h',
                    title='Top 10 Countries',
                    labels={'country': 'Country', 'players': 'Active Players'})
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

# ==================== PAGE 2: MONETIZATION ====================
elif page == "💰 Monetization":
    st.title("💰 Monetization Analytics")
    st.markdown("### Revenue, Conversions & Whale Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Total Purchases
    total_purchases = con.execute(f"""
        SELECT COUNT(*)
        FROM fact_purchases pur
        JOIN dim_players p ON pur.player_id = p.player_id
        WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0]
    
    col1.metric("💳 Total Purchases", f"{total_purchases:,}")
    
    # Conversion Rate
    total_players = con.execute(f"""
        SELECT COUNT(DISTINCT s.player_id)
        FROM fact_sessions s
        JOIN dim_players p ON s.player_id = p.player_id
        WHERE s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0]
    
    paying_users = con.execute(f"""
        SELECT COUNT(DISTINCT pur.player_id)
        FROM fact_purchases pur
        JOIN dim_players p ON pur.player_id = p.player_id
        WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0] or 0
    
    conversion_rate = (paying_users / total_players * 100) if total_players > 0 else 0
    col2.metric("🎯 Conversion Rate", f"{conversion_rate:.2f}%")
    
    # Average Transaction
    avg_transaction = con.execute(f"""
        SELECT AVG(price_usd)
        FROM fact_purchases pur
        JOIN dim_players p ON pur.player_id = p.player_id
        WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0] or 0
    
    col3.metric("💵 Avg Transaction", f"${avg_transaction:.2f}")
    
    # Total Revenue
    revenue = con.execute(f"""
        SELECT COALESCE(SUM(price_usd), 0)
        FROM fact_purchases pur
        JOIN dim_players p ON pur.player_id = p.player_id
        WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
    """).fetchone()[0] or 0
    
    col4.metric("💰 Total Revenue", f"${revenue:,.2f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛒 Revenue by Item Type")
        item_revenue = con.execute(f"""
            SELECT 
                item_type,
                COUNT(*) as purchases,
                SUM(price_usd) as revenue
            FROM fact_purchases pur
            JOIN dim_players p ON pur.player_id = p.player_id
            WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
            GROUP BY item_type
            ORDER BY revenue DESC
        """).fetchdf()
        
        fig = px.bar(item_revenue, x='item_type', y='revenue',
                    title='Revenue by Item Type',
                    labels={'item_type': 'Item Type', 'revenue': 'Revenue ($)'},
                    color='revenue',
                    color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🐋 Top 10 Spenders (Whales)")
        whales = con.execute(f"""
            SELECT 
                pur.player_id,
                p.platform,
                COUNT(pur.purchase_id) as purchases,
                SUM(pur.price_usd) as total_spent
            FROM fact_purchases pur
            JOIN dim_players p ON pur.player_id = p.player_id
            WHERE pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            AND p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
            GROUP BY pur.player_id, p.platform
            ORDER BY total_spent DESC
            LIMIT 10
        """).fetchdf()
        
        st.dataframe(whales, use_container_width=True, hide_index=True)

# ==================== PAGE 3: PLATFORM ANALYSIS ====================
elif page == "📱 Platform Analysis":
    st.title("📱 Platform Performance")
    st.markdown("### iOS vs Android vs Web")
    
    platform_metrics = con.execute(f"""
        SELECT 
            p.platform,
            COUNT(DISTINCT p.player_id) as players,
            COUNT(DISTINCT s.session_id) as sessions,
            AVG(s.duration_minutes) as avg_duration,
            COALESCE(SUM(pur.price_usd), 0) as revenue
        FROM dim_players p
        LEFT JOIN fact_sessions s ON p.player_id = s.player_id 
            AND s.session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        LEFT JOIN fact_purchases pur ON p.player_id = pur.player_id
            AND pur.purchase_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
        WHERE p.platform IN ({','.join([f"'{p}'" for p in selected_platforms])})
        GROUP BY p.platform
        ORDER BY revenue DESC
    """).fetchdf()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig = px.pie(platform_metrics, values='players', names='platform',
                    title='Players by Platform')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.pie(platform_metrics, values='sessions', names='platform',
                    title='Sessions by Platform')
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        fig = px.pie(platform_metrics, values='revenue', names='platform',
                    title='Revenue by Platform')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📊 Platform Comparison")
    st.dataframe(platform_metrics, use_container_width=True, hide_index=True)

# ==================== PAGE 4: RETENTION ====================
elif page == "🔄 Retention & Engagement":
    st.title("🔄 Retention & Engagement")
    st.markdown("### Player Lifecycle and Cohort Analysis")
    
    st.subheader("📅 D1, D3, D7 Retention")
    
    retention = con.execute(f"""
        WITH player_first_day AS (
            SELECT 
                player_id,
                MIN(session_date) as first_session_date
            FROM fact_sessions
            GROUP BY player_id
        ),
        daily_retention AS (
            SELECT 
                pfd.first_session_date,
                COUNT(DISTINCT pfd.player_id) as cohort_size,
                COUNT(DISTINCT CASE WHEN s.session_date = pfd.first_session_date + 1 THEN s.player_id END) as d1_retained,
                COUNT(DISTINCT CASE WHEN s.session_date = pfd.first_session_date + 3 THEN s.player_id END) as d3_retained,
                COUNT(DISTINCT CASE WHEN s.session_date = pfd.first_session_date + 7 THEN s.player_id END) as d7_retained
            FROM player_first_day pfd
            LEFT JOIN fact_sessions s ON pfd.player_id = s.player_id
            WHERE pfd.first_session_date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
            GROUP BY pfd.first_session_date
            ORDER BY pfd.first_session_date
        )
        SELECT 
            first_session_date,
            cohort_size,
            ROUND(d1_retained * 100.0 / cohort_size, 2) as d1_retention_pct,
            ROUND(d3_retained * 100.0 / cohort_size, 2) as d3_retention_pct,
            ROUND(d7_retained * 100.0 / cohort_size, 2) as d7_retention_pct
        FROM daily_retention
    """).fetchdf()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=retention['first_session_date'], y=retention['d1_retention_pct'],
                            mode='lines+markers', name='D1 Retention', line=dict(color='#52c41a')))
    fig.add_trace(go.Scatter(x=retention['first_session_date'], y=retention['d3_retention_pct'],
                            mode='lines+markers', name='D3 Retention', line=dict(color='#1890ff')))
    fig.add_trace(go.Scatter(x=retention['first_session_date'], y=retention['d7_retention_pct'],
                            mode='lines+markers', name='D7 Retention', line=dict(color='#722ed1')))
    
    fig.update_layout(title='Retention Rate Over Time', xaxis_title='Cohort Date', yaxis_title='Retention %')
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(retention, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit | Gaming LiveOps Analytics Dashboard")
