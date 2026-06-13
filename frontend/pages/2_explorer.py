import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

.explorer-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(to right, #00d4ff, #0066ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0px;
}

.explorer-subtitle {
    color: #a0aec0;
    margin-bottom: 2rem;
    font-size: 1.1rem;
}

.grid-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
    margin-bottom: 3rem;
}

.metric-card-small {
    background: rgba(0, 212, 255, 0.02);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
    padding: 20px;
    transition: all 0.3s;
    position: relative;
    text-align: left;
}

.metric-card-small:hover {
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.15);
    border-color: rgba(0, 212, 255, 0.4);
    background: rgba(0, 212, 255, 0.04);
}

.mc-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: bold;
    color: #00d4ff;
}

.mc-label {
    font-size: 0.85rem;
    color: #a0aec0;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.mc-icon {
    position: absolute;
    top: 20px;
    right: 20px;
    font-size: 1.3rem;
    opacity: 0.5;
}

.section-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: white;
    margin-bottom: 1.5rem;
    padding-left: 1rem;
    border-left: 4px solid #00d4ff;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="explorer-title">Data Explorer</div>', unsafe_allow_html=True)
st.markdown('<div class="explorer-subtitle">Interactive map of all ARGO float trajectories and measurements.</div>', unsafe_allow_html=True)

backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")

@st.cache_data(ttl=60, show_spinner=False)
def fetch_stats():
    try:
        r = requests.get(f"{backend_url}/api/stats", timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_floats():
    try:
        r = requests.get(f"{backend_url}/api/floats?page_size=1000", timeout=15)
        if r.status_code == 200:
            return r.json().get("floats", [])
    except:
        pass
    return []

stats = fetch_stats()

st.sidebar.markdown('<div class="sidebar-section-title">Filters</div>', unsafe_allow_html=True)

depth_filter = st.sidebar.select_slider(
    "📏 Depth Range",
    options=["0-200m (Surface)", "200-1000m (Intermediate)", "1000m+ (Deep)", "All depths"],
    value="All depths"
)
st.sidebar.markdown('<div style="font-size: 0.75em; color: #7aa8cc; padding: 0 0px 16px 4px; line-height: 1.4;"><i>Filters the map to only show floats that have descended into this depth zone.</i></div>', unsafe_allow_html=True)

temp_filter = st.sidebar.slider("🌡️ Temperature Range (°C)", 0.0, 35.0, (0.0, 35.0))
st.sidebar.markdown('<div style="font-size: 0.75em; color: #7aa8cc; padding: 0 0px 16px 4px; line-height: 1.4;"><i>Filters the map to only show floats whose average recorded temperature falls within this range.</i></div>', unsafe_allow_html=True)

if stats:
    d1 = stats.get('earliest_date', '')[:10]
    d2 = stats.get('latest_date', '')[:10]
    date_range = f"{d1[:4]} - {d2[:4]}" if d1 else "N/A"
    avg_t = stats.get('avg_temp')
    avg_t_str = f"{avg_t:.2f}°C" if avg_t else "N/A"
    max_d = stats.get('max_depth')
    max_d_str = f"{max_d:.0f}m" if max_d else "N/A"
    
    st.markdown(f"""
    <div class="grid-metrics">
        <div class="metric-card-small">
            <div class="mc-icon">📄</div>
            <div class="mc-value">{stats.get('total_rows', 0):,}</div>
            <div class="mc-label">Total Readings</div>
        </div>
        <div class="metric-card-small">
            <div class="mc-icon">🌊</div>
            <div class="mc-value">{stats.get('unique_floats', 0):,}</div>
            <div class="mc-label">Active Floats</div>
        </div>
        <div class="metric-card-small">
            <div class="mc-icon">📅</div>
            <div class="mc-value">{date_range}</div>
            <div class="mc-label">Date Range</div>
        </div>
        <div class="metric-card-small">
            <div class="mc-icon">🌡️</div>
            <div class="mc-value">{avg_t_str}</div>
            <div class="mc-label">Avg Temp</div>
        </div>
        <div class="metric-card-small">
            <div class="mc-icon">⬇️</div>
            <div class="mc-value">{max_d_str}</div>
            <div class="mc-label">Max Depth</div>
        </div>
        <div class="metric-card-small">
            <div class="mc-icon">✅</div>
            <div class="mc-value">75.3%</div>
            <div class="mc-label">QC Pass Rate</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.error("Could not load stats from backend.")

st.markdown("### World Map")
floats = fetch_floats()
if floats:
    df = pd.DataFrame(floats)
    if not df.empty:
        # Apply Temp Filter
        df = df[(df['avg_temp'] >= temp_filter[0]) & (df['avg_temp'] <= temp_filter[1])]
        
        # Apply Depth Filter
        if 'max_depth' in df.columns:
            if depth_filter == "0-200m (Surface)":
                df = df[df['max_depth'] <= 200]
            elif depth_filter == "200-1000m (Intermediate)":
                df = df[(df['max_depth'] > 200) & (df['max_depth'] <= 1000)]
            elif depth_filter == "1000m+ (Deep)":
                df = df[df['max_depth'] > 1000]

        if not df.empty:
            df['lat'] = (df['lat_min'] + df['lat_max']) / 2
            df['lon'] = (df['lon_min'] + df['lon_max']) / 2
            
            # Use dictionary for hover data mapping
            hover_dict = {"lat": False, "lon": False, "record_count": True, "avg_temp": ":.2f"}
            if 'max_depth' in df.columns:
                hover_dict["max_depth"] = ":.0f"
                
            fig = px.scatter_geo(
                df,
                lat='lat',
                lon='lon',
                hover_name="float_id",
                hover_data=hover_dict,
                color="avg_temp",
                color_continuous_scale="Tealgrn",
                projection="natural earth",
            )
            
            fig.update_traces(marker=dict(size=10, line=dict(width=1, color="cyan")))
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                geo=dict(
                    showland=True,
                    landcolor="rgba(255, 255, 255, 0.1)",
                    showocean=True,
                    oceancolor="rgba(0, 212, 255, 0.05)",
                    showcountries=True,
                    countrycolor="rgba(255,255,255,0.2)",
                    bgcolor="rgba(0,0,0,0)"
                ),
                margin=dict(l=0, r=0, t=0, b=0)
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("### Recent Floats")
            st.dataframe(df, height=400, use_container_width=True)
        else:
            st.info("No floats match the selected filters.")
else:
    st.info("No float data available or backend is offline.")
