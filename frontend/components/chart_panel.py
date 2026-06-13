import streamlit as st
import pandas as pd
from visualisation.map_chart import plot_float_map
from visualisation.profile_chart import plot_depth_profile
from visualisation.timeseries_chart import plot_timeseries
from visualisation.exporter import export_csv
import os

@st.cache_data
def load_data():
    path = os.getenv("PARQUET_PATH", "data/processed/argo.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    return pd.DataFrame()

def render_chart(response: dict, variable: str):
    df = load_data()
    
    chart_type = response.get("chart_type", "none")
    float_ids = response.get("float_ids", [])
    
    if chart_type == "map":
        st.plotly_chart(plot_float_map(df), use_container_width=True)
    elif chart_type == "profile" and float_ids:
        st.plotly_chart(plot_depth_profile(df, float_ids[0], variable), use_container_width=True)
    elif chart_type == "timeseries" and float_ids:
        st.plotly_chart(plot_timeseries(df, float_ids[0], variable), use_container_width=True)
    else:
        st.info("Ask a question to see a visualization")
        
    sql_used = response.get("sql_used")
    if sql_used:
        with st.expander("🔍 Generated SQL"):
            st.code(sql_used, language="sql")
            
    if st.button("Download Data CSV"):
        try:
            path = export_csv(df)
            st.success(f"Exported to {path}")
        except Exception as e:
            st.error(f"Export failed: {e}")
