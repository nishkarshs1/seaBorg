import sys
import os
# Add the project root to sys.path so Streamlit Cloud can find modules like 'visualisation'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import time
import requests
import os
import streamlit.components.v1 as components

st.set_page_config(page_title="SeaBorg", layout="wide", page_icon="🌊")

# Global CSS Injection for the Sidebar
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #020818;
        color: white;
    }

    /* Style the Streamlit top bar to match the theme */
    [data-testid="stDecoration"] {
        background: linear-gradient(90deg, #00d4ff, #0066ff) !important;
    }
    header[data-testid="stHeader"] {
        background: #020818 !important;
    }

    /* Fix main content top padding to shift items up */
    .main .block-container {
        padding-top: 0rem !important;
    }
    
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020818 0%, #0a1628 100%);
        border-right: 1px solid rgba(0, 212, 255, 0.1);
    }
    
    /* Remove default Streamlit sidebar padding */
    [data-testid="stSidebar"] > div:first-child {
        padding: 0;
    }
    
    /* Custom scrollbar in sidebar */
    [data-testid="stSidebar"]::-webkit-scrollbar {
        width: 4px;
    }
    [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
        background: rgba(0, 212, 255, 0.3);
        border-radius: 2px;
    }
    
    /* Section titles */
    .sidebar-section-title {
        color: #7aa8cc;
        font-size: 0.7em;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        padding: 16px 20px 8px 20px;
        border-bottom: 1px solid rgba(0, 212, 255, 0.1);
        margin-bottom: 12px;
        margin-top: 8px;
    }
    
    /* Pulse animation for online indicator */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 255, 100, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(0, 255, 100, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 255, 100, 0); }
    }
    
    /* Pulse animation for offline indicator */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(255, 50, 50, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); }
    }

    /* Style page links as pill buttons */
    [data-testid="stSidebarNav"] {
        display: none !important; /* Hide default navigation fallback */
    }
    
    [data-testid="stPageLink-NavLink"] {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px 16px;
        margin: 4px 16px 8px 16px;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        text-decoration: none !important;
        width: auto !important;
    }
    
    [data-testid="stPageLink-NavLink"]:hover {
        background: rgba(0, 212, 255, 0.05);
        border-color: rgba(0, 212, 255, 0.3);
        transform: translateY(-2px);
    }
    
    /* Active Nav Link Styling */
    [data-testid="stPageLink-NavLink"][aria-current="page"] {
        background: rgba(0, 212, 255, 0.1) !important;
        border: 1px solid #00d4ff !important;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.15) !important;
    }
    
    [data-testid="stPageLink-NavLink"][aria-current="page"] p {
        color: #00d4ff !important;
        font-weight: 600 !important;
    }
    
    /* Add descriptions to nav items using CSS content on specific links */
    a[href*="1_chat"] p::after { content: "\\A Query ocean data with AI"; white-space: pre; font-size: 0.75em; color: #7aa8cc; font-weight: 400; line-height: 1.4; display: block; }
    a[href*="2_explorer"] p::after { content: "\\A Browse ARGO float data"; white-space: pre; font-size: 0.75em; color: #7aa8cc; font-weight: 400; line-height: 1.4; display: block; }
    a[href*="3_about"] p::after { content: "\\A ML pipeline explained"; white-space: pre; font-size: 0.75em; color: #7aa8cc; font-weight: 400; line-height: 1.4; display: block; }
    a[href*="4_analytics"] p::after { content: "\\A Statistical insights"; white-space: pre; font-size: 0.75em; color: #7aa8cc; font-weight: 400; line-height: 1.4; display: block; }

    /* Selectbox styling */
    div[data-baseweb="select"] > div {
        background-color: #0a1628;
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 8px;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: #00d4ff;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "suggested_clicked" not in st.session_state:
    st.session_state.suggested_clicked = False

@st.cache_data(ttl=60, show_spinner=False)
def fetch_backend_stats():
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
    try:
        r = requests.get(f"{backend_url}/api/stats", timeout=15)
        if r.status_code == 200:
            return True, r.json()
    except Exception:
        pass
    return False, {}

def fetch_latency():
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
    try:
        start_t = time.time()
        requests.get(f"{backend_url}/openapi.json", timeout=15)
        return int((time.time() - start_t) * 1000)
    except Exception:
        return 0

is_online, backend_stats = fetch_backend_stats()

@st.fragment(run_every="15s")
def render_backend_status():
    _online, _ = fetch_backend_stats()
    latency = fetch_latency() if _online else 0
    if _online:
        st.markdown(f"""
        <div style="margin: 0 16px 16px 16px; background: rgba(0, 255, 100, 0.05); border: 1px solid rgba(0, 255, 100, 0.2); border-radius: 10px; padding: 10px 14px; display: flex; align-items: center; gap: 8px;">
          <div style="width: 8px; height: 8px; background: #00ff64; border-radius: 50%; box-shadow: 0 0 8px #00ff64; animation: pulse 2s infinite;"></div>
          <span style="color: #00ff64; font-size: 0.85em; font-weight: 600;">Backend Online</span>
          <span style="color: #7aa8cc; font-size: 0.75em; margin-left: auto;">{latency} ms</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="margin: 0 16px 16px 16px; background: rgba(255, 50, 50, 0.05); border: 1px solid rgba(255, 50, 50, 0.2); border-radius: 10px; padding: 10px 14px; display: flex; align-items: center; gap: 8px;">
          <div style="width: 8px; height: 8px; background: #ff3232; border-radius: 50%; box-shadow: 0 0 8px #ff3232; animation: pulse-red 2s infinite;"></div>
          <span style="color: #ff3232; font-size: 0.85em; font-weight: 600;">Backend Offline</span>
          <span style="color: #7aa8cc; font-size: 0.75em; margin-left: auto;">--- ms</span>
        </div>
        """, unsafe_allow_html=True)

# Setup pages (Must be defined before st.page_link is used)
page_chat = st.Page("pages/1_chat.py", title="Ocean Chat", icon="💬")
page_explorer = st.Page("pages/2_explorer.py", title="Data Explorer", icon="🗺️")
page_about = st.Page("pages/3_about.py", title="How It Works", icon="⚙️")
page_analytics = st.Page("pages/4_analytics.py", title="Analytics", icon="📈")
pg = st.navigation([page_chat, page_explorer, page_about, page_analytics], position="hidden")

# Global Sidebar
with st.sidebar:
    # PART 1 - LOGO SECTION
    st.markdown("""
    <div style="text-align: center; padding: 20px 0 10px 0;">
      <div style="
        width: 60px; height: 60px;
        margin: 0 auto 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 40px;
      ">🌊</div>
      <h2 style="
        color: #00d4ff;
        font-size: 1.6em;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(90deg, #00d4ff, #0066ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      ">SeaBorg</h2>
      <p style="color: #7aa8cc; font-size: 0.75em; margin: 4px 0 0 0;">
        Ocean Intelligence Platform
      </p>
    </div>
    """, unsafe_allow_html=True)

    # PART 2 - BACKEND STATUS
    render_backend_status()

    # PART 3 - LIVE STATS MINI CARDS
    if is_online and backend_stats:
        recs = f"{backend_stats.get('total_rows', 0):,}"
        floats = f"{backend_stats.get('unique_floats', 0):,}"
        d1 = backend_stats.get('earliest_date', '')[:4]
        d2 = backend_stats.get('latest_date', '')[:4]
        date_cov = f"{d1} ──────────── {d2}" if d1 and d2 else "N/A"
        
        st.markdown(f"""
        <div style="margin: 0 16px 16px 16px;">
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                <div style="flex: 1; background: rgba(0, 212, 255, 0.03); border: 1px solid rgba(0, 212, 255, 0.1); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="color: #00d4ff; font-family: 'JetBrains Mono', monospace; font-weight: bold; font-size: 1.1em;">{recs}</div>
                    <div style="color: #7aa8cc; font-size: 0.65em; text-transform: uppercase;">Records</div>
                </div>
                <div style="flex: 1; background: rgba(0, 212, 255, 0.03); border: 1px solid rgba(0, 212, 255, 0.1); border-radius: 8px; padding: 10px; text-align: center;">
                    <div style="color: #00d4ff; font-family: 'JetBrains Mono', monospace; font-weight: bold; font-size: 1.1em;">{floats}</div>
                    <div style="color: #7aa8cc; font-size: 0.65em; text-transform: uppercase;">Floats</div>
                </div>
            </div>
            <div style="background: rgba(0, 212, 255, 0.03); border: 1px solid rgba(0, 212, 255, 0.1); border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #00d4ff; font-family: 'JetBrains Mono', monospace; font-weight: bold; font-size: 0.95em;">{date_cov}</div>
                <div style="color: #7aa8cc; font-size: 0.65em; text-transform: uppercase;">Date Coverage</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # PART 4 - NAVIGATION
    st.markdown('<div class="sidebar-section-title">Navigation</div>', unsafe_allow_html=True)
    st.page_link(page_chat, label="Ocean Chat", icon="💬")
    st.page_link(page_explorer, label="Data Explorer", icon="🗺️")
    st.page_link(page_about, label="How It Works", icon="⚙️")
    st.page_link(page_analytics, label="Analytics", icon="📈")

    # Dynamically highlight active page robustly via JS
    active_title = pg.title
    components.html(f"""
    <script>
        const parentDoc = window.parent.document;
        const links = parentDoc.querySelectorAll('[data-testid="stPageLink-NavLink"]');
        links.forEach(link => {{
            const text = link.innerText || link.textContent;
            if(text.includes('{active_title}')) {{
                link.style.setProperty('background', 'rgba(0, 212, 255, 0.1)', 'important');
                link.style.setProperty('border', '1px solid #00d4ff', 'important');
                link.style.setProperty('box-shadow', '0 0 15px rgba(0, 212, 255, 0.15)', 'important');
                const p = link.querySelector('p');
                if (p) {{
                    p.style.setProperty('color', '#00d4ff', 'important');
                    p.style.setProperty('font-weight', '600', 'important');
                }}
            }} else {{
                link.style.background = '';
                link.style.border = '';
                link.style.boxShadow = '';
                const p = link.querySelector('p');
                if(p) {{ p.style.color = ''; p.style.fontWeight = ''; }}
            }}
        }});
    </script>
    """, height=0, width=0)

pg.run()
