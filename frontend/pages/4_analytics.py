import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

import os

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

.analytics-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(to right, #00d4ff, #0066ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0px;
}

.analytics-subtitle {
    color: #a0aec0;
    margin-bottom: 2rem;
    font-size: 1.1rem;
}

/* Style native st.metric cards to look like premium glass cards */
[data-testid="stMetric"] {
    background: rgba(0, 212, 255, 0.02) !important;
    border: 1px solid rgba(0, 212, 255, 0.15) !important;
    border-radius: 12px !important;
    padding: 20px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
}

[data-testid="stMetric"]:hover {
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.15) !important;
    border-color: rgba(0, 212, 255, 0.4) !important;
    background: rgba(0, 212, 255, 0.04) !important;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: bold !important;
    color: #00d4ff !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    color: #a0aec0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="analytics-title">Advanced Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="analytics-subtitle">In-depth statistical analysis and visualizations of ocean metrics.</div>', unsafe_allow_html=True)

@st.cache_resource
def load_parquet():
    path = os.getenv("PARQUET_PATH", "data/processed/argo.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()

df = load_parquet().copy()

if df.empty:
    st.error("Could not load argo.parquet data.")
else:
    st.sidebar.markdown('<div class="sidebar-section-title">Filters</div>', unsafe_allow_html=True)
    float_ids = ["All Floats"] + sorted(df["float_id"].unique().tolist())
    selected_float = st.sidebar.selectbox("🛟 Float ID", float_ids)
    st.sidebar.markdown('<div style="font-size: 0.75em; color: #7aa8cc; padding: 0 0px 16px 4px; line-height: 1.4;"><i>Isolates the analytics dashboard to show data from a specific ARGO float, rather than aggregating all available floats.</i></div>', unsafe_allow_html=True)
    
    if selected_float != "All Floats":
        df = df[df["float_id"] == selected_float]
    
    # Theme configuration
    layout_args = dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )

    # Sample dataframe for heavy charts
    hist_df = df.sample(n=min(20000, len(df))) if len(df) > 20000 else df
    
    col1, col2 = st.columns(2)
    
    with col1:
    # Removed empty html div
        st.subheader("Temperature Distribution")
        with st.spinner("Rendering..."):
            fig1 = px.histogram(hist_df, x="temp_c", nbins=50, color_discrete_sequence=["#00d4ff"])
            fig1.update_layout(**layout_args)
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>Shows the frequency of different temperature readings. Helps identify common temperature zones and anomalies in the ocean layers.</i></div>', unsafe_allow_html=True)
    # Removed closing html div

    with col2:
    # Removed empty html div
        st.subheader("Depth Distribution")
        with st.spinner("Rendering..."):
            fig4 = px.histogram(hist_df, x="depth_m", nbins=50, color_discrete_sequence=["#0066ff"])
            fig4.update_layout(**layout_args)
            st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})
        st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>Illustrates how many sensor readings were taken at various depths. Useful for understanding the vertical coverage of the ARGO floats.</i></div>', unsafe_allow_html=True)
    # Removed closing html div

    st.markdown("---")

    col3, col4 = st.columns(2)
    
    with col3:
    # Removed empty html div
        st.subheader("T-S Diagram (Temperature vs Salinity)")
        with st.spinner("Rendering..."):
            plot_df = df.sample(n=min(3000, len(df))) if len(df) > 3000 else df
            fig2 = px.scatter(
                plot_df, x="salinity", y="temp_c", color="depth_m",
                color_continuous_scale="Viridis_r", opacity=0.7
            )
            fig2.update_layout(**layout_args)
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>A standard oceanographic plot mapping Temperature against Salinity. Color indicates depth. This helps identify distinct ocean water masses and density gradients.</i></div>', unsafe_allow_html=True)
        
        # Correlation Stats below T-S diagram
        st.markdown("#### Correlation Stats")
        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)
        pearson_corr = df['temp_c'].corr(df['salinity'])
        mean_depth = df['depth_m'].mean()
        std_temp = df['temp_c'].std()
        min_sal, max_sal = df['salinity'].min(), df['salinity'].max()
        c1.metric("Pearson Correlation", f"{pearson_corr:.2f}")
        c2.metric("Mean Depth", f"{mean_depth:.0f} m")
        c3.metric("Temp Std Dev", f"{std_temp:.2f} °C")
        c4.metric("Salinity Range", f"{min_sal:.1f} - {max_sal:.1f}")
        
    # Removed closing html div

    with col4:
    # Removed empty html div
        st.subheader("Readings Over Time")
        with st.spinner("Rendering..."):
            df['week_start'] = df['date'].dt.to_period('W').dt.start_time
            time_df = df.groupby('week_start').size().reset_index(name='count')
            fig3 = px.line(time_df, x="week_start", y="count", color_discrete_sequence=["#00d4ff"])
            fig3.update_layout(**layout_args)
            st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>Tracks the volume of data collected by the floats over time, grouped by week. Highlights periods of active deployment and temporal data gaps.</i></div>', unsafe_allow_html=True)
    # Removed closing html div

    st.markdown("---")
    
    # 1. Float Activity Heatmap
    # Removed empty html div
    st.subheader("Float Activity Heatmap (Readings per Month/Year)")
    with st.spinner("Rendering..."):
        df['Month'] = df['date'].dt.month
        df['Year'] = df['date'].dt.year
        heatmap_df = df.groupby(['Month', 'Year']).size().reset_index(name='count')
        # Use pivot to make it a 2D matrix
        pivot_df = heatmap_df.pivot(index='Year', columns='Month', values='count').fillna(0)
        
        # Map month numbers to abbreviated names for readability
        import calendar
        pivot_df.columns = [calendar.month_abbr[int(m)] for m in pivot_df.columns]
        
        fig5 = px.imshow(
            pivot_df, 
            labels=dict(x="Month", y="Year", color="Readings"),
            x=pivot_df.columns,
            y=pivot_df.index,
            color_continuous_scale="Tealgrn",
            aspect="auto"
        )
        fig5.update_layout(**layout_args)
        st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})
    st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>Visualizes the density of sensor readings aggregated by month and year. Brighter green areas indicate periods with the highest data collection frequency.</i></div>', unsafe_allow_html=True)
    # Removed closing html div

    # Float Comparison Chart (Top 5 only to avoid spaghetti)
    unique_floats = df['float_id'].nunique()
    if unique_floats >= 2 and selected_float == "All Floats":
        st.markdown("---")
    # Removed empty html div
        st.subheader("Temperature Profile Comparison (Top 5 Most Active Floats)")
        with st.spinner("Rendering..."):
            # Line chart showing avg temp per depth per float. Since depth is continuous, bucket it.
            df['depth_bucket'] = (df['depth_m'] // 100) * 100
            top_floats = df['float_id'].value_counts().nlargest(5).index
            filtered_df = df[df['float_id'].isin(top_floats)]
            comp_df = filtered_df.groupby(['float_id', 'depth_bucket'])['temp_c'].mean().reset_index()
            comp_df['float_id_str'] = comp_df['float_id'].astype(str)
            
            fig6 = px.line(
                comp_df, x="temp_c", y="depth_bucket", color="float_id_str", 
                orientation='h',
                labels={"temp_c": "Temperature (°C)", "depth_bucket": "Depth (m)", "float_id_str": "Float ID"}
            )
            fig6.update_yaxes(autorange="reversed")
            fig6.update_layout(**layout_args)
            st.plotly_chart(fig6, use_container_width=True, config={'displayModeBar': False})
        st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>Plots depth against temperature for the 5 most active floats in the dataset. This allows for direct comparisons of water column temperature profiles across different float trajectories.</i></div>', unsafe_allow_html=True)
    # Removed closing html div

    # Depth Zone Analysis (Box plot instead of Bar chart for better distribution view)
    st.markdown("---")
    # Removed empty html div
    st.subheader("Temperature Distribution by Depth Zone")
    with st.spinner("Rendering..."):
        # Vectorized binning for performance
        df['Depth Zone'] = pd.cut(
            df['depth_m'], 
            bins=[-np.inf, 200, 1000, np.inf], 
            labels=['Surface (0-200m)', 'Intermediate (200-1000m)', 'Deep (1000m+)']
        )
        zone_order = ['Surface (0-200m)', 'Intermediate (200-1000m)', 'Deep (1000m+)']
        
        # Use a sample for the box plot to keep it fast but representative
        box_df = df.sample(n=min(10000, len(df))) if len(df) > 10000 else df
        
        fig7 = px.box(
            box_df, x="Depth Zone", y="temp_c", color="Depth Zone",
            category_orders={"Depth Zone": zone_order},
            labels={"temp_c": "Temperature (°C)"}
        )
        fig7.update_layout(**layout_args)
        fig7.update_layout(xaxis_title="")
        st.plotly_chart(fig7, use_container_width=True, config={'displayModeBar': False})
    st.markdown('<div style="font-size: 0.85em; color: #a0aec0; margin-top: -10px; margin-bottom: 20px;"><i>Shows the statistical spread (median, quartiles, and outliers) of temperatures recorded at the surface, intermediate layers, and the deep ocean.</i></div>', unsafe_allow_html=True)
    # Removed closing html div
