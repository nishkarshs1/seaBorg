import streamlit as st
import os
from components.sidebar import render_sidebar
from components.chat_panel import render_chat
from components.chart_panel import render_chart

st.set_page_config(page_title="SeaBorg", layout="wide", page_icon="🌊")

# Inject dark CSS
st.markdown("""
<style>
    .stApp {
        background-color: #0a0f1e;
        color: white;
    }
    .stChatMessage {
        background-color: #1a233a;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None

# Layout
col_chat, col_chart = st.columns([1, 1.2])

with col_chat:
    sidebar_state = render_sidebar()
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.last_response = None
        st.rerun()
    
    response = render_chat()
    if response:
        st.session_state.last_response = response
        st.rerun()

with col_chart:
    st.subheader("📊 Live Visualization")
    if st.session_state.last_response:
        render_chart(st.session_state.last_response, sidebar_state["variable"])
    else:
        st.info("Ask a question to see a visualization")
