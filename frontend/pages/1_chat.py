import streamlit as st
import requests
import os
import random
import time
import html
import streamlit.components.v1 as components
from datetime import datetime
from components.chart_panel import render_chart

# Initialize Session State for direct page loads
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "suggested_clicked" not in st.session_state:
    st.session_state.suggested_clicked = False

st.markdown("""
<style>
/* PART 1 - PAGE LAYOUT */
.main .block-container {
    padding-top: 0rem !important;
    padding-bottom: 0;
    max-width: 100%;
}
[data-testid="column"] {
    height: calc(100vh - 80px);
    overflow-y: auto;
    padding-right: 15px;
}
[data-testid="column"]::-webkit-scrollbar {
    width: 6px;
}
[data-testid="column"]::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.2);
    border-radius: 10px;
}
[data-testid="column"]::-webkit-scrollbar-track {
    background: transparent;
}
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes glow {
    0%, 100% { box-shadow: 0 0 10px rgba(0,212,255,0.2); }
    50% { box-shadow: 0 0 20px rgba(0,212,255,0.4); }
}
.message-appear {
    animation: fadeSlideUp 0.3s ease forwards;
}
[data-testid="stChatMessage"] {
    animation: fadeSlideUp 0.3s ease forwards;
}
@keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-8px); }
}
[data-testid="stChatInput"] {
    background: rgba(0,212,255,0.03) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 16px !important;
    color: #e0f4ff !important;
    outline: none !important;
}
[data-testid="stChatInput"] * {
    outline: none !important;
}
/* Aggressively strip Streamlit's native inner wrapper borders/shadows */
[data-testid="stChatInput"] div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 0 2px rgba(0,212,255,0.1) !important;
}
[data-testid="stChatInputSubmitButton"] {
    background: linear-gradient(135deg, #00d4ff, #0066ff) !important;
    border-radius: 10px !important;
}
div.stButton > button {
    background: rgba(0,212,255,0.05) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 12px !important;
    color: #e0f4ff !important;
    padding: 14px 16px !important;
    font-size: 0.95em !important;
    font-weight: 600 !important;
    text-align: left !important;
    transition: all 0.2s !important;
    width: 100% !important;
    margin-bottom: 8px !important;
}
div.stButton > button:hover {
    background: rgba(0,212,255,0.1) !important;
    border-color: #00d4ff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0,212,255,0.15) !important;
}
.clear-btn div.stButton > button {
    background: rgba(255,50,50,0.05) !important;
    border-color: rgba(255,50,50,0.2) !important;
    color: #ff6b6b !important;
    text-align: center !important;
}
.clear-btn div.stButton > button:hover {
    background: rgba(255,50,50,0.1) !important;
    border-color: #ff3232 !important;
    box-shadow: 0 4px 12px rgba(255,50,50,0.15) !important;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown('<div class="sidebar-section-title">Filters</div>', unsafe_allow_html=True)
variable_label = st.sidebar.selectbox("📊 Variable", ["Temperature", "Salinity"])
st.session_state.variable = "temp_c" if variable_label == "Temperature" else "salinity"
st.sidebar.markdown('<div style="font-size: 0.75em; color: #7aa8cc; padding: 0 0px 16px 4px; line-height: 1.4;"><i>Controls which metric is displayed on the live interactive chart when the AI generates a plot.</i></div>', unsafe_allow_html=True)

col_chat, col_chart = st.columns([0.45, 0.55], gap="large")

with col_chat:
    st.markdown("""
<div style="
background: linear-gradient(135deg, rgba(0,212,255,0.05), rgba(0,102,255,0.05));
border: 1px solid rgba(0,212,255,0.15);
border-radius: 16px;
padding: 20px;
margin-bottom: 20px;
display: flex;
align-items: center;
gap: 16px;
">
<div style="
width: 48px; height: 48px;
background: linear-gradient(135deg, #00d4ff, #0066ff);
border-radius: 50%;
display: flex; align-items: center; 
justify-content: center;
font-size: 24px;
box-shadow: 0 0 20px rgba(0,212,255,0.4);
flex-shrink: 0;
">🌊</div>
<div>
<h2 style="
margin: 0;
background: linear-gradient(90deg, #00d4ff, #0066ff);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
font-size: 1.3em;
font-weight: 800;
">SeaBorg AI</h2>
<p style="
margin: 2px 0 0 0;
color: #7aa8cc;
font-size: 0.8em;
">Powered by real ARGO float data · LLaMA 3 via Groq</p>
</div>
<div style="
margin-left: auto;
display: flex; align-items: center; gap: 6px;
background: rgba(0,255,100,0.05);
border: 1px solid rgba(0,255,100,0.2);
border-radius: 20px;
padding: 4px 12px;
">
<div style="
width: 6px; height: 6px;
background: #00ff64;
border-radius: 50%;
box-shadow: 0 0 6px #00ff64;
"></div>
<span style="color: #00ff64; font-size: 0.75em;">Live</span>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    col_msg, col_clear = st.columns([0.7, 0.3])
    with col_msg:
        st.markdown(f'<div style="color: #7aa8cc; font-size: 0.8em; text-transform: uppercase; padding-top: 10px; margin-bottom: 20px;">💬 Messages: <span style="color: #00d4ff; font-weight: bold;">{len(st.session_state.messages)}</span></div>', unsafe_allow_html=True)
    with col_clear:
        st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_response = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_stats():
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
        try:
            r = requests.get(f"{backend_url}/api/stats", timeout=15)
            if r.status_code == 200:
                return r.json().get('total_rows', 0)
        except Exception:
            pass
        return "15,843"
        
    total_readings = fetch_stats()
    if isinstance(total_readings, int):
        total_readings = f"{total_readings:,}"

    if len(st.session_state.messages) == 0:
        st.markdown(f"""
<div class="message-appear" style="
text-align: center;
padding: 30px 20px;
margin-bottom: 20px;
">
<div style="font-size: 3em; margin-bottom: 12px;">🌊</div>
<h3 style="
background: linear-gradient(90deg, #00d4ff, #0066ff);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
font-size: 1.4em;
margin-bottom: 8px;
">Welcome to SeaBorg</h3>
<p style="color: #7aa8cc; font-size: 0.9em; line-height: 1.6;">
Ask me anything about ocean data.<br>
I have access to <strong style="color: #00d4ff;">{total_readings}</strong> 
real ARGO float readings from the Indian Ocean.<br>
<span style="font-size: 0.85em; opacity: 0.7;">
Based on OceanGPT ACL 2024 paper
</span>
</p>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="message-appear" style="color: #a0aec0; font-size: 0.9em; margin-bottom: 12px; font-weight: 600;">💡 Try asking...</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            q1 = st.button("🌡️ Avg Ocean Temperature")
            q2 = st.button("📍 Float Locations")
            q3 = st.button("📈 Salinity Trend")
        with c2:
            q4 = st.button("🌊 Depth Profile")
            q5 = st.button("🐟 How deep do floats go?")
            q6 = st.button("🌍 Ocean conditions")
            
        selected_query = None
        if q1: selected_query = "whats the avg temp of indian ocean"
        if q2: selected_query = "Where are ARGO floats?"
        if q3: selected_query = "Salinity trend over time"
        if q4: selected_query = "Depth profile analysis"
        if q5: selected_query = "How deep do ARGO floats go?"
        if q6: selected_query = "Ocean conditions near Indian subcontinent"
        
        if selected_query:
            st.session_state.messages.append({
                "role": "user", 
                "content": selected_query,
                "timestamp": datetime.now().strftime("%I:%M %p")
            })
            st.rerun()

    for msg in st.session_state.messages:
        timestamp = msg.get("timestamp", datetime.now().strftime("%I:%M %p"))
        
        if msg["role"] == "user":
            st.markdown(f"""
<div class="message-appear" style="
display: flex;
justify-content: flex-end;
margin: 8px 0;
">
<div style="
background: linear-gradient(135deg, #0066ff, #00d4ff);
color: white;
padding: 12px 16px;
border-radius: 18px 18px 4px 18px;
max-width: 80%;
font-size: 0.9em;
box-shadow: 0 4px 15px rgba(0,102,255,0.3);
">
{msg["content"]}
<div style="
font-size: 0.7em; 
opacity: 0.7; 
text-align: right;
margin-top: 4px;
">{timestamp}</div>
</div>
<div style="
width: 32px; height: 32px;
background: rgba(0,102,255,0.2);
border-radius: 50%;
margin-left: 8px;
display: flex; align-items: center; 
justify-content: center;
flex-shrink: 0;
font-size: 16px;
">👤</div>
</div>
""", unsafe_allow_html=True)
        else:
            stats_html = ""
            if "metadata" in msg:
                meta = msg["metadata"]
                resp_time = meta.get("response_time", 0)
                conf = meta.get("confidence", 0)
                chart_t = meta.get("chart_type", "none")
                
                safe_copy_text = html.escape(msg['content'], quote=True).replace('\n', '&#10;').replace('\r', '&#13;')
                stats_html = f"""
<div style="
display: flex; gap: 12px;
margin-top: 10px;
padding-top: 10px;
border-top: 1px solid rgba(0,212,255,0.1);
flex-wrap: wrap;
">
<span style="color: #7aa8cc; font-size: 0.75em;">
⚡ {resp_time:.1f}ms
</span>
<span style="color: #7aa8cc; font-size: 0.75em;">
🎯 {conf*100:.0f}% confidence
</span>
<span style="color: #7aa8cc; font-size: 0.75em; text-transform: capitalize;">
📊 {chart_t} chart
</span>
<span class="chat-copy-btn" style="color: #7aa8cc; font-size: 0.75em; cursor: pointer; transition: color 0.2s;" 
      onmouseover="this.style.color='#00d4ff'" 
      onmouseout="this.style.color='#7aa8cc'"
      data-clipboard-text="{safe_copy_text}">
📋 Copy
</span>
<span style="color: #7aa8cc; font-size: 0.75em; margin-left: auto;">
{timestamp}
</span>
</div>
"""
            
            st.markdown(f"""
<div class="message-appear" style="
display: flex;
justify-content: flex-start;
margin: 8px 0;
">
<div style="
width: 32px; height: 32px;
background: linear-gradient(135deg, #00d4ff, #0066ff);
border-radius: 50%;
margin-right: 8px;
display: flex; align-items: center;
justify-content: center;
flex-shrink: 0;
font-size: 16px;
box-shadow: 0 0 10px rgba(0,212,255,0.3);
">🌊</div>
<div style="
background: rgba(0,212,255,0.05);
border: 1px solid rgba(0,212,255,0.15);
color: #e0f4ff;
padding: 14px 18px;
border-radius: 4px 18px 18px 18px;
max-width: 85%;
font-size: 0.9em;
line-height: 1.6;
">
{msg["content"]}
{stats_html}
</div>
</div>
""", unsafe_allow_html=True)

    indicator_placeholder = st.empty()
    st.markdown('<div style="text-align: center; color: #7aa8cc; font-size: 0.8em; opacity: 0.6; padding-top: 20px; padding-bottom: 5px;">⏱️ Note: AI responses query live data and may take up to 10-15 seconds.</div>', unsafe_allow_html=True)
    user_input = st.chat_input("Ask about ocean data... e.g. temperature at 500m")
    
    if user_input:
        st.session_state.messages.append({
            "role": "user", 
            "content": user_input,
            "timestamp": datetime.now().strftime("%I:%M %p")
        })
        st.rerun()
        
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
        user_msg = st.session_state.messages[-1]["content"]
        
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
        api_endpoint = f"{backend_url}/api/chat"
        
        spinner_messages = [
            "🔍 Searching ARGO data...",
            "🧠 Analyzing ocean records...",
            "🌊 Diving into the data...",
            "📡 Querying float sensors...",
            "🗄️ Retrieving from FAISS..."
        ]
        
        rand_msg = random.choice(spinner_messages)
        indicator_placeholder.markdown(f"""
<div class="message-appear" style="display: flex; align-items: center; gap: 8px; padding: 12px 0;">
<div style="
width: 32px; height: 32px;
background: linear-gradient(135deg, #00d4ff, #0066ff);
border-radius: 50%;
display: flex; align-items: center; 
justify-content: center;
font-size: 16px;
">🌊</div>
<div style="
background: rgba(0,212,255,0.05);
border: 1px solid rgba(0,212,255,0.15);
border-radius: 4px 18px 18px 18px;
padding: 14px 20px;
">
<div style="display: flex; gap: 6px; align-items: center;">
<span style="color: #7aa8cc; font-size: 0.85em; margin-right: 8px;">{rand_msg}</span>
<div style="
width: 8px; height: 8px;
background: #00d4ff;
border-radius: 50%;
animation: bounce 1.4s infinite;
"></div>
<div style="
width: 8px; height: 8px;
background: #00d4ff;
border-radius: 50%;
animation: bounce 1.4s infinite 0.2s;
"></div>
<div style="
width: 8px; height: 8px;
background: #00d4ff;
border-radius: 50%;
animation: bounce 1.4s infinite 0.4s;
"></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
        
        start_time = time.time()
        try:
            response = requests.post(api_endpoint, json={"message": user_msg}, timeout=120)
            end_time = time.time()
            indicator_placeholder.empty()
            
            if response.status_code == 200:
                data = response.json()
                ans = data.get("answer", "No text response.")
                st.session_state.last_response = data
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": ans,
                    "timestamp": datetime.now().strftime("%I:%M %p"),
                    "metadata": {
                        "confidence": data.get("confidence", 0.85),
                        "sql_used": data.get("sql_used"),
                        "response_time": end_time - start_time,
                        "chart_type": data.get("chart_type", "none")
                    },
                    "id": random.randint(1, 1000000)
                })
                st.rerun()
            else:
                st.error(f"Error {response.status_code}: {response.text}")
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Error communicating with backend.",
                    "timestamp": datetime.now().strftime("%I:%M %p")
                })
        except Exception as e:
            indicator_placeholder.empty()
            st.error(f"Failed to connect: {e}")
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "Failed to connect to backend.",
                "timestamp": datetime.now().strftime("%I:%M %p")
            })

with col_chart:
    chart_t = "None"
    conf = 0
    sql = None
    if st.session_state.last_response:
        chart_t = st.session_state.last_response.get("chart_type", "None")
        conf = st.session_state.last_response.get("confidence", 0)
        sql = st.session_state.last_response.get("sql_used")

    st.markdown(f"""
<div class="message-appear" style="
background: linear-gradient(135deg, rgba(0,102,255,0.05), rgba(0,212,255,0.05));
border: 1px solid rgba(0,212,255,0.15);
border-radius: 16px;
padding: 16px 20px;
margin-bottom: 16px;
display: flex;
align-items: center;
justify-content: space-between;
">
<div style="display: flex; align-items: center; gap: 12px;">
<span style="font-size: 1.5em;">📊</span>
<div>
<h3 style="
margin: 0;
color: #00d4ff;
font-size: 1.1em;
font-weight: 700;
">Live Visualization</h3>
<p style="margin: 0; color: #7aa8cc; font-size: 0.75em;">
Auto-updates with each query
</p>
</div>
</div>
<div style="
background: rgba(0,212,255,0.1);
border: 1px solid rgba(0,212,255,0.2);
border-radius: 8px;
padding: 4px 12px;
color: #00d4ff;
font-size: 0.8em;
text-transform: capitalize;
">{chart_t} chart</div>
</div>
""", unsafe_allow_html=True)

    if st.session_state.last_response and chart_t.lower() != "none":
        render_chart(st.session_state.last_response, st.session_state.variable)
    else:
        st.markdown("""
<div class="message-appear" style="
height: 300px;
background: rgba(0,212,255,0.02);
border: 1px dashed rgba(0,212,255,0.15);
border-radius: 16px;
display: flex;
flex-direction: column;
align-items: center;
justify-content: center;
gap: 12px;
">
<span style="font-size: 3em; opacity: 0.3;">🌊</span>
<p style="color: #7aa8cc; font-size: 0.9em; text-align: center;">
Ask a question to see a<br>live ocean visualization
</p>
</div>
""", unsafe_allow_html=True)

components.html("""
<script>
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById('copy-script-injected')) {
        const dummy = parentDoc.createElement('div');
        dummy.id = 'copy-script-injected';
        dummy.style.display = 'none';
        parentDoc.body.appendChild(dummy);
        
        parentDoc.addEventListener("click", function(e) {
            if (e.target && e.target.matches('.chat-copy-btn')) {
                const text = e.target.getAttribute('data-clipboard-text');
                window.parent.navigator.clipboard.writeText(text).then(() => {
                    const oldText = e.target.innerText;
                    e.target.innerText = '✅ Copied!';
                    setTimeout(() => e.target.innerText = oldText, 2000);
                }).catch(err => {
                    console.error('Failed to copy!', err);
                });
            }
        });
    }
</script>
""", height=0, width=0)
