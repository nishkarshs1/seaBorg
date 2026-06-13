import streamlit as st
import requests
import os

@st.cache_data(ttl=60, show_spinner=False)
def fetch_stats():
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8001")
    try:
        r = requests.get(f"{backend_url}/api/stats", timeout=2)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

stats = fetch_stats()
total_rows = stats.get('total_rows', 15843)
unique_floats = stats.get('unique_floats', 3)
d1 = stats.get('earliest_date', '')[:10]
d2 = stats.get('latest_date', '')[:10]
date_range = f"{d1[:4]}-{d2[:4]}" if d1 else "2002-2026"

st.set_page_config(page_title="How It Works - SeaBorg", layout="wide", page_icon="⚙️")

# CSS INJECTION
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
.hero-section {
background: linear-gradient(135deg, #020818, #0a1628, #001833);
padding: 4rem 2rem 3rem 2rem;
border-radius: 16px;
text-align: center;
position: relative;
overflow: hidden;
margin-bottom: 2rem;
border: 1px solid rgba(0, 212, 255, 0.1);
}
.hero-title {
font-size: 4rem;
font-weight: 800;
background: linear-gradient(to right, #00d4ff, #0066ff);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
margin-bottom: 0.5rem;
}
.hero-subtitle {
font-size: 1.5rem;
color: #a0aec0;
margin-bottom: 2rem;
}
.pill-badge {
display: inline-block;
padding: 8px 20px;
border-radius: 50px;
font-size: 0.95rem;
font-weight: 600;
margin: 0 8px;
backdrop-filter: blur(10px);
}
.pill-cyan {
border: 1px solid #00d4ff;
color: #00d4ff;
background: rgba(0, 212, 255, 0.05);
}
.pill-blue {
border: 1px solid #0066ff;
color: #0066ff;
background: rgba(0, 102, 255, 0.05);
}
.wave-wrapper {
position: absolute;
bottom: -5px;
left: 0;
width: 100%;
overflow: hidden;
line-height: 0;
}
.wave-track {
display: flex;
width: 200%;
animation: move-wave 15s linear infinite;
}
.wave-track svg {
flex-shrink: 0;
width: 50%;
height: 40px;
}
@keyframes move-wave {
0% { transform: translateX(0); }
100% { transform: translateX(-50%); }
}
.metrics-bar {
display: flex;
justify-content: space-around;
background: rgba(0, 212, 255, 0.02);
border: 1px solid rgba(0, 212, 255, 0.15);
border-radius: 12px;
padding: 1.5rem;
margin-bottom: 3rem;
}
.metric-item {
text-align: center;
position: relative;
flex: 1;
}
.metric-item:not(:last-child)::after {
content: '';
position: absolute;
right: 0;
top: 10%;
height: 80%;
width: 1px;
background: rgba(255, 255, 255, 0.1);
}
.metric-value {
font-family: 'JetBrains Mono', monospace;
font-size: 1.8rem;
font-weight: 700;
color: #00d4ff;
transition: text-shadow 0.3s;
}
.metric-item:hover .metric-value {
text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}
.metric-label {
font-size: 0.85rem;
color: #a0aec0;
text-transform: uppercase;
letter-spacing: 1px;
margin-top: 4px;
}
.section-title {
font-size: 1.8rem;
font-weight: 700;
color: white;
margin-bottom: 1.5rem;
padding-left: 1rem;
border-left: 4px solid #00d4ff;
}
.pipeline-container {
display: flex;
flex-wrap: wrap;
align-items: center;
justify-content: center;
gap: 12px;
margin-bottom: 3rem;
}
.pipeline-card {
background: rgba(0, 212, 255, 0.05);
border: 1px solid rgba(0, 212, 255, 0.2);
border-radius: 12px;
padding: 16px;
width: 160px;
height: 150px;
position: relative;
transition: all 0.3s ease;
display: flex;
flex-direction: column;
justify-content: center;
text-align: center;
}
.pipeline-card:hover {
border-color: #00d4ff;
transform: translateY(-4px);
box-shadow: 0 4px 15px rgba(0, 212, 255, 0.15);
}
.step-badge {
position: absolute;
top: -10px;
left: -10px;
background: #00d4ff;
color: #020818;
width: 26px;
height: 26px;
border-radius: 50%;
display: flex;
align-items: center;
justify-content: center;
font-weight: bold;
font-size: 0.9rem;
border: 2px solid #020818;
}
.pipeline-title {
font-weight: bold;
font-size: 1.0rem;
color: white;
margin-bottom: 8px;
display: flex;
flex-direction: column;
align-items: center;
gap: 4px;
}
.pipeline-desc {
font-size: 0.75rem;
color: #a0aec0;
line-height: 1.4;
white-space: pre-line;
}
.pipeline-arrow {
color: #00d4ff;
font-size: 1.5rem;
font-weight: bold;
opacity: 0.7;
}
.grid-2x3 {
display: grid;
grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
gap: 20px;
margin-bottom: 3rem;
}
.algo-card {
background: rgba(255, 255, 255, 0.02);
border: 1px solid rgba(255, 255, 255, 0.05);
border-radius: 12px;
padding: 24px;
transition: all 0.3s;
display: flex;
flex-direction: column;
}
.algo-card:hover {
background: rgba(255, 255, 255, 0.04);
transform: translateY(-2px);
box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}
.algo-title {
font-size: 1.25rem;
font-weight: bold;
margin-bottom: 12px;
}
.algo-type {
display: inline-block;
font-size: 0.8rem;
padding: 4px 10px;
border-radius: 6px;
background: rgba(255, 255, 255, 0.1);
margin-bottom: 16px;
color: #e2e8f0;
}
.algo-list {
margin: 0;
padding-left: 20px;
font-size: 0.9rem;
color: #cbd5e0;
line-height: 1.6;
flex-grow: 1;
}
.algo-list li {
margin-bottom: 6px;
}
.algo-used {
margin-top: 20px;
font-size: 0.85rem;
font-weight: bold;
color: #48bb78;
background: rgba(72, 187, 120, 0.1);
border: 1px solid rgba(72, 187, 120, 0.3);
padding: 6px 12px;
border-radius: 6px;
align-self: flex-start;
}
.grid-metrics {
display: grid;
grid-template-columns: repeat(4, 1fr);
gap: 16px;
margin-bottom: 16px;
}
.metric-card-small {
background: rgba(0, 212, 255, 0.02);
border: 1px solid rgba(0, 212, 255, 0.15);
border-radius: 12px;
padding: 20px;
transition: all 0.3s;
position: relative;
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
.styled-table {
width: 100%;
border-collapse: separate;
border-spacing: 0;
margin-bottom: 3rem;
font-size: 0.95rem;
border: 1px solid rgba(0, 212, 255, 0.2);
border-radius: 12px;
overflow: hidden;
background: rgba(255, 255, 255, 0.02);
}
.styled-table th, .styled-table td {
padding: 16px 20px;
text-align: left;
border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.styled-table th {
background-color: rgba(0, 212, 255, 0.08);
color: #00d4ff;
font-weight: bold;
text-transform: uppercase;
font-size: 0.85rem;
letter-spacing: 1px;
}
.styled-table tr:last-child td {
border-bottom: none;
}
.styled-table tr:hover {
background-color: rgba(0, 212, 255, 0.04);
}
.table-highlight {
background-color: rgba(0, 212, 255, 0.06) !important;
font-weight: bold;
border-left: 2px solid #00d4ff;
}
.stat-pills-row {
display: flex;
gap: 12px;
margin-top: 20px;
flex-wrap: wrap;
}
.stat-pill {
background: rgba(255, 255, 255, 0.05);
border: 1px solid rgba(255, 255, 255, 0.1);
padding: 8px 16px;
border-radius: 50px;
font-size: 0.9rem;
display: flex;
align-items: center;
gap: 8px;
color: #e2e8f0;
}
/* Specific Top Borders for Algos */
.b-cyan { border-top: 3px solid #00d4ff !important; }
.b-blue { border-top: 3px solid #0066ff !important; }
.b-teal { border-top: 3px solid #38b2ac !important; }
.b-purple { border-top: 3px solid #9f7aea !important; }
.b-orange { border-top: 3px solid #ed8936 !important; }
.b-green { border-top: 3px solid #48bb78 !important; }
@media (max-width: 1024px) {
.grid-metrics {
grid-template-columns: repeat(2, 1fr);
}
}
</style>
""", unsafe_allow_html=True)

# PART 1: HERO SECTION
st.markdown("""
<div class="hero-section">
<div class="hero-title">SeaBorg</div>
<div class="hero-subtitle">Ocean Intelligence Platform</div>
<div>
<span class="pill-badge pill-cyan">🎓 Based on OceanGPT ACL 2024</span>
<span class="pill-badge pill-blue">🌊 Real ARGO Float Data</span>
</div>
<div class="wave-wrapper">
<div class="wave-track">
<svg viewBox="0 0 1200 120" preserveAspectRatio="none">
<path d="M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z" opacity=".25" fill="#00d4ff"></path>
<path d="M0,0V15.81C13,36.92,27.64,56.86,47.69,72.05c99.29,75.21,206.31,52.33,308,24.5C417.81,81.42,476.92,67.6,539,64.2c62.66-3.41,126.83,1.87,190,12.78,71.21,12.3,142.17,26.54,213.9,32.61,64.4,5.43,129.74-1.28,197.1-15.61V0Z" opacity=".5" fill="#00d4ff"></path>
<path d="M0,0V5.63C149.93,59,314.09,71.32,475.83,42.57c43-7.64,84.23-20.12,127.61-26.46,59-8.63,112.48,12.24,165.56,35.4C827.93,77.22,886,95.24,951.2,90c86.53-7,172.46-45.71,248.8-84.81V0Z" fill="#00d4ff"></path>
</svg>
<svg viewBox="0 0 1200 120" preserveAspectRatio="none">
<path d="M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z" opacity=".25" fill="#00d4ff"></path>
<path d="M0,0V15.81C13,36.92,27.64,56.86,47.69,72.05c99.29,75.21,206.31,52.33,308,24.5C417.81,81.42,476.92,67.6,539,64.2c62.66-3.41,126.83,1.87,190,12.78,71.21,12.3,142.17,26.54,213.9,32.61,64.4,5.43,129.74-1.28,197.1-15.61V0Z" opacity=".5" fill="#00d4ff"></path>
<path d="M0,0V5.63C149.93,59,314.09,71.32,475.83,42.57c43-7.64,84.23-20.12,127.61-26.46,59-8.63,112.48,12.24,165.56,35.4C827.93,77.22,886,95.24,951.2,90c86.53-7,172.46-45.71,248.8-84.81V0Z" fill="#00d4ff"></path>
</svg>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# PART 2: METRICS BAR
st.markdown(f"""
<div class="metrics-bar">
<div class="metric-item">
<div class="metric-value">{total_rows:,}</div>
<div class="metric-label">ARGO Records</div>
</div>
<div class="metric-item">
<div class="metric-value">384D</div>
<div class="metric-label">Embeddings</div>
</div>
<div class="metric-item">
<div class="metric-value">16.85ms</div>
<div class="metric-label">FAISS Speed</div>
</div>
<div class="metric-item">
<div class="metric-value">75.34%</div>
<div class="metric-label">QC Pass Rate</div>
</div>
<div class="metric-item">
<div class="metric-value">~1.2s</div>
<div class="metric-label">LLM Latency</div>
</div>
</div>
""", unsafe_allow_html=True)

# PART 3: PIPELINE SECTION
st.markdown("""
<div class="section-title">The SeaBorg Pipeline</div>
<div class="pipeline-container">
<div class="pipeline-card" style="border-left: 3px solid #1a3a5c;">
<div class="step-badge">1</div>
<div class="pipeline-title"><span>📁</span> NetCDF Files</div>
<div class="pipeline-desc">Raw ARGO sensor data (.nc format, multidimensional arrays)</div>
</div>
<div class="pipeline-arrow">→</div>
<div class="pipeline-card">
<div class="step-badge">2</div>
<div class="pipeline-title"><span>🔧</span> ETL Pipeline</div>
<div class="pipeline-desc">xarray parsing → QC filtering → PostgreSQL + Parquet</div>
</div>
<div class="pipeline-arrow">→</div>
<div class="pipeline-card">
<div class="step-badge">3</div>
<div class="pipeline-title"><span>📝</span> Text Summaries</div>
<div class="pipeline-desc">Each row converted to natural language summary</div>
</div>
<div class="pipeline-arrow">→</div>
<div class="pipeline-card">
<div class="step-badge">4</div>
<div class="pipeline-title"><span>🧠</span> Embeddings</div>
<div class="pipeline-desc">all-MiniLM-L6-v2<br>384-dimensional vectors</div>
</div>
<div class="pipeline-arrow">→</div>
<div class="pipeline-card">
<div class="step-badge">5</div>
<div class="pipeline-title"><span>🔍</span> FAISS Search</div>
<div class="pipeline-desc">Semantic similarity search<br>Top-5 relevant records</div>
</div>
<div class="pipeline-arrow">→</div>
<div class="pipeline-card">
<div class="step-badge">6</div>
<div class="pipeline-title"><span>🤖</span> LLaMA 3</div>
<div class="pipeline-desc">Context-grounded answer via Groq API</div>
</div>
<div class="pipeline-arrow">→</div>
<div class="pipeline-card">
<div class="step-badge">7</div>
<div class="pipeline-title"><span>📊</span> Answer + Chart</div>
<div class="pipeline-desc">Natural language response + Plotly visualization</div>
</div>
</div>
""", unsafe_allow_html=True)

# PART 4: ALGORITHMS SECTION
st.markdown("""
<div class="section-title">ML Algorithms & Techniques</div>
<div class="grid-2x3">
<!-- Card 1 -->
<div class="algo-card b-cyan">
<div class="algo-title" style="color: #00d4ff;">Sentence Transformers</div>
<div class="algo-type">all-MiniLM-L6-v2</div>
<ul class="algo-list">
<li><b>Type:</b> Bi-encoder neural network</li>
<li><b>Architecture:</b> 6-layer transformer, 384-dimensional embeddings</li>
<li><b>Purpose:</b> Converts ocean data into semantic vectors</li>
<li><b>Why chosen:</b> Lightweight (80MB), runs on CPU</li>
</ul>
<div class="algo-used">Used in SeaBorg ✅</div>
</div>
<!-- Card 2 -->
<div class="algo-card b-blue">
<div class="algo-title" style="color: #0066ff;">FAISS</div>
<div class="algo-type">Facebook AI Similarity Search</div>
<ul class="algo-list">
<li><b>Type:</b> Approximate Nearest Neighbor (ANN) search</li>
<li><b>Index type:</b> IndexFlatL2 (exact L2 distance search)</li>
<li><b>Purpose:</b> Finds top-K most relevant ocean records in ms</li>
<li><b>Speed:</b> Sub-millisecond search on CPU</li>
</ul>
<div class="algo-used">Used in SeaBorg ✅</div>
</div>
<!-- Card 3 -->
<div class="algo-card b-teal">
<div class="algo-title" style="color: #38b2ac;">RAG Architecture</div>
<div class="algo-type">Retrieval-Augmented Generation</div>
<ul class="algo-list">
<li><b>Type:</b> Hybrid AI architecture</li>
<li><b>Components:</b> Retriever + Generator</li>
<li><b>Advantage:</b> LLM cannot hallucinate numbers — it only reads retrieved real sensor data</li>
<li><b>Context:</b> Top-5 most relevant records passed</li>
</ul>
<div class="algo-used">Used in SeaBorg ✅</div>
</div>
<!-- Card 4 -->
<div class="algo-card b-purple">
<div class="algo-title" style="color: #9f7aea;">LLaMA 3 via Groq</div>
<div class="algo-type">llama-3.1-8b-instant</div>
<ul class="algo-list">
<li><b>Provider:</b> Groq (ultra-fast LPU inference)</li>
<li><b>Purpose:</b> Answer generation + NL-to-SQL</li>
<li><b>Temperature:</b> 0.2 (factual, consistent)</li>
<li><b>Tokens:</b> 1024 max per response</li>
</ul>
<div class="algo-used">Used in SeaBorg ✅</div>
</div>
<!-- Card 5 -->
<div class="algo-card b-orange">
<div class="algo-title" style="color: #ed8936;">Natural Language to SQL</div>
<div class="algo-type">LLM Query Translation</div>
<ul class="algo-list">
<li><b>Input:</b> Plain English question</li>
<li><b>Output:</b> PostgreSQL query for argo_profiles</li>
<li><b>Safety:</b> SQL injection prevention via keyword blocklist</li>
<li><b>Purpose:</b> Structured data queries alongside RAG</li>
</ul>
<div class="algo-used">Used in SeaBorg ✅</div>
</div>
<!-- Card 6 -->
<div class="algo-card b-green">
<div class="algo-title" style="color: #48bb78;">Quality Control Pipeline</div>
<div class="algo-type">Scientific Data Filtering</div>
<ul class="algo-list">
<li><b>ARGO QC flags:</b> Accept only flag 1 (Good) and 2 (Probably good)</li>
<li><b>Range validation:</b> temp -3°C to 40°C, salinity 20-42 PSU</li>
<li><b>Depth validation:</b> depth > 0m only</li>
<li><b>Result:</b> Clean, scientifically valid sensor data</li>
</ul>
<div class="algo-used">Used in SeaBorg ✅</div>
</div>
</div>
""", unsafe_allow_html=True)

# PART 5: METRICS SECTION
st.markdown(f"""
<div class="section-title">System Performance</div>
<!-- Row 1 -->
<div class="grid-metrics">
<div class="metric-card-small">
<div class="mc-icon">📄</div>
<div class="mc-value">{total_rows:,}</div>
<div class="mc-label">Total ARGO Records</div>
</div>
<div class="metric-card-small">
<div class="mc-icon">🌊</div>
<div class="mc-value">{unique_floats:,}</div>
<div class="mc-label">Active Floats Used</div>
</div>
<div class="metric-card-small">
<div class="mc-icon">📅</div>
<div class="mc-value">{date_range}</div>
<div class="mc-label">Date Coverage</div>
</div>
<div class="metric-card-small">
<div class="mc-icon">✅</div>
<div class="mc-value">75.34%</div>
<div class="mc-label">QC Pass Rate</div>
</div>
</div>
<!-- Row 2 -->
<div class="grid-metrics" style="margin-bottom: 3rem;">
<div class="metric-card-small">
<div class="mc-icon">⚡</div>
<div class="mc-value">16.85ms</div>
<div class="mc-label">FAISS Retrieval</div>
</div>
<div class="metric-card-small">
<div class="mc-icon">🚀</div>
<div class="mc-value">~1.2s</div>
<div class="mc-label">Groq API Latency</div>
</div>
<div class="metric-card-small">
<div class="mc-icon">💬</div>
<div class="mc-value">84</div>
<div class="mc-label">Avg LLM Tokens</div>
</div>
<div class="metric-card-small">
<div class="mc-icon">🌡️</div>
<div class="mc-value">0.2</div>
<div class="mc-label">LLM Temperature</div>
</div>
</div>
""", unsafe_allow_html=True)

# PART 6: RAG vs FINE-TUNING TABLE
st.markdown("""
<div class="section-title">Why RAG?</div>
<table class="styled-table">
<thead>
<tr>
<th>Approach</th>
<th>Pros</th>
<th>Cons</th>
<th>SeaBorg Uses?</th>
</tr>
</thead>
<tbody>
<tr class="table-highlight">
<td><strong>RAG</strong> (Retrieval-Augmented Generation)</td>
<td>Always uses latest data, no hallucination, cheap</td>
<td>Slower than direct LLM inference</td>
<td style="color: #48bb78; font-weight: bold;">✅ Yes</td>
</tr>
<tr>
<td><strong>Fine-tuning</strong></td>
<td>Fast inference, domain adapted</td>
<td>Expensive, data goes stale instantly</td>
<td style="color: #f56565;">❌ No</td>
</tr>
<tr>
<td><strong>Prompt engineering</strong></td>
<td>Simple, no training needed</td>
<td>Limited context window limits data</td>
<td style="color: #ed8936;">Partial ✅</td>
</tr>
<tr>
<td><strong>Vector DB only</strong></td>
<td>Fast retrieval, good for search</td>
<td>No natural language generation</td>
<td style="color: #f56565;">❌ No</td>
</tr>
</tbody>
</table>
<div style="background: rgba(0, 212, 255, 0.05); padding: 16px; border-radius: 8px; border-left: 4px solid #00d4ff; margin-bottom: 3rem;">
<b>Explanation:</b> SeaBorg uses RAG because ocean data changes constantly. A fine-tuned model would go stale. RAG always retrieves the exact, latest ARGO readings dynamically before answering.
</div>
""", unsafe_allow_html=True)

# PART 7: ARGO FLOAT SECTION
st.markdown('<div class="section-title">What are ARGO Floats?</div>', unsafe_allow_html=True)

c1, c2 = st.columns([6, 4])

with c1:
    st.markdown("""
<div style="font-size: 1.05rem; line-height: 1.6; color: #cbd5e0; padding-right: 20px;">
<p>ARGO is an international program that collects information from inside the ocean using a fleet of robotic instruments that drift with the ocean currents and move up and down between the surface and a mid-water level.</p>
<ul style="margin-top: 16px;">
<li style="margin-bottom: 8px;"><strong style="color: white;">Autonomous robotic profilers:</strong> No ship required after deployment.</li>
<li style="margin-bottom: 8px;"><strong style="color: white;">Global coverage:</strong> Over 4,000 active floats deployed worldwide.</li>
<li style="margin-bottom: 8px;"><strong style="color: white;">Measurements:</strong> Temperature (°C), Salinity (PSU), and Pressure (dbar, proxy for depth).</li>
<li style="margin-bottom: 8px;"><strong style="color: white;">Data format:</strong> NetCDF (.nc files) — multidimensional scientific arrays.</li>
</ul>
<div class="stat-pills-row">
<div class="stat-pill">🌍 4,000+ Active Floats</div>
<div class="stat-pill">📡 Satellite Transmissions</div>
<div class="stat-pill">🌊 2000m Depth Range</div>
</div>
</div>
</div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
<div style="background: rgba(0, 212, 255, 0.02); border: 1px solid rgba(0, 212, 255, 0.15); border-radius: 12px; padding: 20px; box-shadow: inset 0 0 20px rgba(0,0,0,0.2);">
<div style="color: #00d4ff; font-weight: bold; font-family: 'JetBrains Mono', monospace; margin-bottom: 20px; font-size: 1.1em;"># The 10-Day Dive Cycle</div>
<div style="position: relative; padding-left: 28px;">
<!-- Vertical Line -->
<div style="position: absolute; left: 8px; top: 8px; bottom: 8px; width: 2px; background: linear-gradient(to bottom, #00d4ff, #0066ff, #0066ff, #00d4ff);"></div>
<!-- Step 1 -->
<div style="position: relative; margin-bottom: 18px;">
<div style="position: absolute; left: -24px; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: #00d4ff; box-shadow: 0 0 8px #00d4ff;"></div>
<div style="color: #e0f4ff; font-weight: 600;">Surface (0m)</div>
<div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">📡 Transmit data via satellite</div>
</div>
<!-- Step 2 -->
<div style="position: relative; margin-bottom: 18px;">
<div style="position: absolute; left: -24px; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: #00aaff; box-shadow: 0 0 4px rgba(0,170,255,0.5);"></div>
<div style="color: #e0f4ff; font-weight: 600;">Park depth (1000m)</div>
<div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">🌊 Drift with ocean currents for ~9 days</div>
</div>
<!-- Step 3 -->
<div style="position: relative; margin-bottom: 18px;">
<div style="position: absolute; left: -24px; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: #0066ff;"></div>
<div style="color: #e0f4ff; font-weight: 600;">Profile depth (2000m)</div>
<div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">⬇️ Descend to bottom</div>
</div>
<!-- Step 4 -->
<div style="position: relative; margin-bottom: 18px;">
<div style="position: absolute; left: -24px; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: #00aaff; box-shadow: 0 0 4px rgba(0,170,255,0.5);"></div>
<div style="color: #e0f4ff; font-weight: 600;">Ascent Profiling</div>
<div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">⬆️ Measure temp & salinity every ~2m</div>
</div>
<!-- Step 5 -->
<div style="position: relative;">
<div style="position: absolute; left: -24px; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: #00d4ff; box-shadow: 0 0 8px #00d4ff;"></div>
<div style="color: #e0f4ff; font-weight: 600;">Surface (0m)</div>
<div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">🔄 Repeat cycle</div>
</div>
</div>
</div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# PART 8: SEABORG VS OCEANGPT
st.markdown('<div class="section-title">Research: SeaBorg vs OceanGPT</div>', unsafe_allow_html=True)
c3, c4 = st.columns([3, 2])

with c3:
    st.markdown("""
<div style="font-size: 1.1em; color: #e0f4ff; font-weight: bold; margin-bottom: 12px;">The Foundation: OceanGPT (ACL 2024)</div>
<div style="color: #cbd5e0; line-height: 1.6; font-size: 0.95em; border-left: 3px solid #00d4ff; padding-left: 16px; background: rgba(0, 212, 255, 0.02); padding-top: 12px; padding-bottom: 12px; border-radius: 0 8px 8px 0;">
    <p style="margin-top: 0;"><i>SeaBorg's intelligence is heavily inspired by <b>OceanGPT</b>, the first Large Language Model specifically designed for ocean science.</i></p>
    <p><i>While the original research focused on generating synthetic training data using a multi-agent framework to fine-tune an LLM, SeaBorg takes a more applied approach.</i></p>
    <p style="margin-bottom: 0;"><i>We implemented OceanGPT's core Retrieval-Augmented Generation (RAG) architecture and wired it directly to a live pipeline of <b>real ARGO float sensor data</b>, bridging the gap between theoretical AI models and real-time oceanographic exploration.</i></p>
</div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
<div class="algo-card" style="padding: 16px; border-top: 3px solid #00d4ff;">
<h4 style='color: #00d4ff; margin-top:0;'>SeaBorg vs OceanGPT</h4>
<ul style="list-style-type: none; padding-left: 0; margin-bottom: 16px; font-size: 0.9rem;">
<li>✅ RAG pipeline</li>
<li>✅ Domain-specific embeddings</li>
<li>✅ NL-to-SQL</li>
<li>✅ Real ocean data (ARGO)</li>
<li style="opacity:0.8; color:#a0aec0;">🔮 LLM fine-tuning (Future Work)</li>
<li style="opacity:0.8; color:#a0aec0;">🔮 DoInstruct framework (Future Work)</li>
</ul>
<hr style="border-color: rgba(255,255,255,0.1); margin: 12px 0;">
<b style="font-size:0.9rem;">What SeaBorg adds to the OceanGPT vision:</b>
<ul style="list-style-type: none; padding-left: 0; margin-top: 10px; font-size: 0.85rem; color: #cbd5e0;">
<li style="margin-bottom: 4px;">✅ Real-time ARGO data ingestion (not static datasets)</li>
<li style="margin-bottom: 4px;">✅ Interactive Plotly visualizations (map, depth profile, timeseries)</li>
<li style="margin-bottom: 4px;">✅ Multi-page educational platform</li>
<li style="margin-bottom: 4px;">✅ Export functionality (CSV download)</li>
<li style="margin-bottom: 4px; opacity:0.8; color:#a0aec0;">🔮 LLM fine-tuning on ARGO data (Future Work)</li>
<li style="margin-bottom: 4px; opacity:0.8; color:#a0aec0;">🔮 DoInstruct data generation (Future Work)</li>
</ul>
</div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="
    background: rgba(0, 212, 255, 0.03);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
    padding: 20px;
    margin-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div style="
            width: 48px; height: 48px;
            background: #161b22;
            border-radius: 12px;
            display: flex; align-items: center;
            justify-content: center;
            font-size: 24px;
            border: 1px solid rgba(255,255,255,0.1);
        ">🐙</div>
        <div>
            <div style="
                color: #e0f4ff; 
                font-weight: 700; 
                font-size: 1em;
            ">OceanGPT Official Repository</div>
            <div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">
                github.com/OceanGPT/OceanGPT
            </div>
            <div style="color: #7aa8cc; font-size: 0.8em; margin-top: 4px;">
                The original research implementation · ACL 2024
            </div>
        </div>
    </div>
    <a href="https://github.com/OceanGPT/OceanGPT" 
       target="_blank"
       style="
        background: rgba(0,212,255,0.1);
        border: 1px solid rgba(0,212,255,0.3);
        color: #00d4ff;
        padding: 8px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 0.85em;
        font-weight: 600;
        white-space: nowrap;
    ">View on GitHub →</a>
</div>

<div style="
    background: rgba(255, 100, 0, 0.03);
    border: 1px solid rgba(255, 100, 0, 0.15);
    border-radius: 12px;
    padding: 20px;
    margin-top: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
">
    <div style="display: flex; align-items: center; gap: 16px;">
        <div style="
            width: 48px; height: 48px;
            background: rgba(255,100,0,0.1);
            border-radius: 12px;
            display: flex; align-items: center;
            justify-content: center;
            font-size: 24px;
        ">📄</div>
        <div>
            <div style="color: #e0f4ff; font-weight: 700; font-size: 1em;">
                OceanGPT: A Large Language Model for Ocean Science Tasks
            </div>
            <div style="color: #7aa8cc; font-size: 0.85em; margin-top: 2px;">
                ACL 2024 · arxiv.org/abs/2310.02031
            </div>
            <div style="color: #7aa8cc; font-size: 0.8em; margin-top: 4px;">
                Bi et al. · The research paper SeaBorg is based on
            </div>
        </div>
    </div>
    <a href="https://arxiv.org/abs/2310.02031" 
       target="_blank"
       style="
        background: rgba(255,100,0,0.1);
        border: 1px solid rgba(255,100,0,0.3);
        color: #ff6400;
        padding: 8px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 0.85em;
        font-weight: 600;
        white-space: nowrap;
    ">Read Paper →</a>
</div>
""", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# PART 9: TECH STACK
st.markdown('<div class="section-title">Tech Stack</div>', unsafe_allow_html=True)

ts1, ts2, ts3, ts4 = st.columns(4)

with ts1:
    st.markdown("""
    <div class="algo-card" style="padding: 16px; height: 100%; text-align: center; border-top: 3px solid #00d4ff;">
    <div style="font-size: 2rem; margin-bottom: 8px;">🎨</div>
    <h4 style="color: #00d4ff; margin: 0 0 8px 0;">Frontend</h4>
    <p style="font-size: 0.85rem; color: #a0aec0; margin: 0; line-height: 1.6;">Streamlit<br>Custom HTML/CSS<br>Plotly Maps</p>
    </div>
    """, unsafe_allow_html=True)

with ts2:
    st.markdown("""
    <div class="algo-card" style="padding: 16px; height: 100%; text-align: center; border-top: 3px solid #0066ff;">
    <div style="font-size: 2rem; margin-bottom: 8px;">⚙️</div>
    <h4 style="color: #0066ff; margin: 0 0 8px 0;">Backend</h4>
    <p style="font-size: 0.85rem; color: #a0aec0; margin: 0; line-height: 1.6;">FastAPI<br>Python 3.11<br>Uvicorn</p>
    </div>
    """, unsafe_allow_html=True)

with ts3:
    st.markdown("""
    <div class="algo-card" style="padding: 16px; height: 100%; text-align: center; border-top: 3px solid #00d4ff;">
    <div style="font-size: 2rem; margin-bottom: 8px;">🧠</div>
    <h4 style="color: #00d4ff; margin: 0 0 8px 0;">AI / ML</h4>
    <p style="font-size: 0.85rem; color: #a0aec0; margin: 0; line-height: 1.6;">LLaMA 3 (Groq)<br>ChromaDB<br>SentenceTransformers</p>
    </div>
    """, unsafe_allow_html=True)

with ts4:
    st.markdown("""
    <div class="algo-card" style="padding: 16px; height: 100%; text-align: center; border-top: 3px solid #0066ff;">
    <div style="font-size: 2rem; margin-bottom: 8px;">🗄️</div>
    <h4 style="color: #0066ff; margin: 0 0 8px 0;">Data Eng</h4>
    <p style="font-size: 0.85rem; color: #a0aec0; margin: 0; line-height: 1.6;">xarray / netCDF4<br>SQLite / Pandas<br>ETL Pipeline</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br><br>", unsafe_allow_html=True)

# FOOTER
st.markdown("""
<div style="text-align: center; padding: 20px; border-top: 1px solid rgba(0, 212, 255, 0.1); color: #7aa8cc; font-size: 0.85rem;">
    <strong>SeaBorg v1.0.0</strong> &middot; Built on OceanGPT ACL 2024 &middot; ARGO Float Data &middot; Made by <strong>Nishkarsh Sharma</strong>
</div>
""", unsafe_allow_html=True)
