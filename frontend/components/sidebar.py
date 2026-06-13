import streamlit as st
import datetime

def render_sidebar() -> dict:
    st.sidebar.header("🌊 SeaBorg")
    st.sidebar.subheader("Ocean Intelligence Platform")
    
    # Date range
    start_date = st.sidebar.date_input("Start Date", datetime.date(2000, 1, 1))
    end_date = st.sidebar.date_input("End Date", datetime.date.today())
    
    # Variable selector
    variable_label = st.sidebar.selectbox("Variable", ["Temperature", "Salinity"])
    variable_key = "temp_c" if variable_label == "Temperature" else "salinity"
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown(
        "SeaBorg is an AI-powered ocean data chatbot based on the **OceanGPT ACL 2024** paper. "
        "It queries real ARGO float oceanographic NetCDF data using natural language."
    )
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "variable": variable_key
    }
