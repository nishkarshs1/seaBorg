<div align="center">
  <h1>SeaBorg 🌊</h1>
  <p><strong>AI-Powered Ocean Intelligence Platform</strong></p>
  <p>Query, explore, and visualise real ARGO float oceanographic data using plain natural language.</p>

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=for-the-badge&logo=streamlit)](https://streamlit.io)
[![LLaMA](https://img.shields.io/badge/LLaMA_3-via_Groq-purple?style=for-the-badge)](https://groq.com)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-blue?style=for-the-badge)](https://faiss.ai)

</div>

## What is SeaBorg?

SeaBorg is a full-stack AI system that makes real ARGO float oceanographic data accessible through natural language. Ask it anything about ocean temperature, salinity, or depth - it retrieves the most relevant sensor readings from a database of **209,767 real measurements** and generates grounded, data-driven answers alongside interactive Plotly visualizations.

Built as a practical implementation of the **OceanGPT ACL 2024** research paper - applying Retrieval-Augmented Generation to live oceanographic sensor data.

## Screenshots

**Ocean Chat - Natural language querying with live map visualization**

<img src="screenshots/chat.png" alt="Ocean Chat" width="800" />

**Data Explorer - 209,767 ARGO readings across 23 floats (2002-2026)**

<img src="screenshots/explorer.png" alt="Data Explorer" width="800" />

**How It Works - Complete ML pipeline documentation**

<img src="screenshots/how_it_works.png" alt="How It Works" width="800" />

**Advanced Analytics - T-S diagrams, depth distributions, temporal analysis**

<img src="screenshots/analytics.png" alt="Analytics" width="800" />

## System Metrics

| Metric                | Value       |
| --------------------- | ----------- |
| ARGO Records          | 209,767     |
| Active Floats         | 23          |
| Date Coverage         | 2002 - 2026 |
| Embedding Dimensions  | 384D        |
| FAISS Retrieval Speed | 16.85ms     |
| QC Pass Rate          | 75.34%      |
| Groq API Latency      | ~1.2s       |
| Avg LLM Tokens        | 84          |
| LLM Temperature       | 0.2         |
| Max Depth Recorded    | 2,054m      |

## Architecture

```
User Question (natural language)
        |
        v
Streamlit Frontend (4-page platform)
        |
        v POST /api/chat
FastAPI Backend (port 8001)
        |
        +---> RAG Retriever
        |         |
        |         v
        |     FAISS Index (209,767 vectors, 384D)
        |         |
        |         v
        |     Top-5 relevant ARGO records
        |
        +---> LLM (LLaMA 3 via Groq)
        |         |
        |         v
        |     Grounded answer + SQL query
        |
        +---> Chart Type Detection
                  |
                  v
        JSON Response: {answer, chart_type, float_ids, sql_used}
                  |
                  v
        Plotly Chart (map / depth profile / timeseries)
```

## The SeaBorg Pipeline

```
Raw .nc files
    |
    v
ETL Pipeline (ingestion/)
    Parser     - xarray reads NetCDF multidimensional arrays
    QC Filter  - Accept QC flags 1 & 2 only
                 Range: temp -3 to 40C, salinity 20-42 PSU
    DB Loader  - PostgreSQL + Parquet storage
    |
    v
Text Summaries (rag/summariser.py)
    Each row -> "Float D13857 recorded 14.2C at 100m on 2023-04-12..."
    |
    v
Embeddings (rag/embedder.py)
    all-MiniLM-L6-v2 -> 384-dimensional vectors
    |
    v
FAISS Index (rag/indexer.py)
    IndexFlatL2, 209,767 vectors
    |
    v  [At query time]
Semantic Retrieval (rag/retriever.py)
    Question -> vector -> top-5 nearest ARGO records
    |
    v
LLM Generation (llm/query_engine.py)
    Context + question -> LLaMA 3 via Groq -> grounded answer
    |
    v
NL-to-SQL (llm/nl_to_sql.py)
    Question -> PostgreSQL query + safety filter
    |
    v
FastAPI Response + Plotly Chart
```

## ML Algorithms

**Sentence Transformers (all-MiniLM-L6-v2)**

- Architecture: 6-layer transformer, 384-dimensional embeddings
- Purpose: Semantic encoding of ocean data summaries
- Why chosen: Lightweight (80MB), CPU-compatible, optimized for similarity search

**FAISS (Facebook AI Similarity Search)**

- Index type: IndexFlatL2 (exact L2 nearest neighbor)
- Scale: 209,767 vectors indexed
- Speed: 16.85ms average retrieval time on CPU

**RAG (Retrieval-Augmented Generation)**

- Retriever: FAISS semantic search finds top-5 relevant records
- Generator: LLaMA 3 produces grounded answers from retrieved context
- Key advantage: LLM reads only real sensor data - zero hallucination on numbers

**LLaMA 3 via Groq**

- Model: llama-3.1-8b-instant
- Temperature: 0.2 (factual, consistent outputs)
- Max tokens: 1024 per response

**NL-to-SQL with Safety Filter**

- Translates natural language to PostgreSQL queries
- Blocks: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, GRANT
- Transparent: generated SQL shown in UI expander

**Quality Control Pipeline**

- ARGO QC flags: Accept 1 (Good) and 2 (Probably good) only
- Range validation: temp -3 to 40C, salinity 20-42 PSU, depth > 0m
- Result: 75.34% QC pass rate on raw sensor data

## Why RAG over Fine-tuning?

| Approach           | Pros                                 | Cons                       | SeaBorg     |
| ------------------ | ------------------------------------ | -------------------------- | ----------- |
| RAG                | Always latest data, no hallucination | Slower inference           | YES         |
| Fine-tuning        | Fast, domain adapted                 | Expensive, data goes stale | Future Work |
| Prompt engineering | Simple                               | Limited context            | Partial     |

Ocean data changes constantly. A fine-tuned model would go stale immediately. RAG always retrieves the exact, latest ARGO readings before answering.

## SeaBorg vs OceanGPT (ACL 2024)

| Feature                         | OceanGPT    | SeaBorg     |
| ------------------------------- | ----------- | ----------- |
| RAG pipeline                    | YES         | YES         |
| Domain embeddings               | YES         | YES         |
| NL-to-SQL                       | YES         | YES         |
| Real ocean data (ARGO)          | NO (static) | YES (live)  |
| Interactive visualization       | NO          | YES         |
| Multi-page educational platform | NO          | YES         |
| Export functionality            | NO          | YES         |
| LLM fine-tuning                 | YES         | Future Work |
| DoInstruct framework            | YES         | Future Work |

Paper: [OceanGPT: A Large Language Model for Ocean Science Tasks (ACL 2024)](https://arxiv.org/abs/2310.02031)
Repository: [github.com/OceanGPT/OceanGPT](https://github.com/OceanGPT/OceanGPT)

## Pages

| Page          | Description                                                                |
| ------------- | -------------------------------------------------------------------------- |
| Ocean Chat    | Natural language chat with real-time ARGO data retrieval and Plotly charts |
| Data Explorer | Interactive world map, 209,767 readings, float statistics table            |
| How It Works  | Full ML pipeline documentation, algorithm cards, system metrics            |
| Analytics     | T-S diagrams, temperature/depth distributions, temporal analysis           |

## API Endpoints

**POST /api/chat**

```json
Request:  {"message": "temperature at 500m Indian Ocean"}
Response: {
  "answer": "Based on retrieved float data...",
  "chart_type": "profile",
  "float_ids": ["1900121", "1902669"],
  "sql_used": "SELECT * FROM argo_profiles WHERE depth_m BETWEEN 480 AND 520",
  "confidence": 0.85
}
```

**GET /api/stats** - Total rows, float count, date range, avg temperature

**GET /api/floats** - All float IDs with date ranges and coordinates

**POST /api/export** - Download data as CSV or NetCDF

## Tech Stack

**Backend**

- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy
- FAISS (faiss-cpu)
- sentence-transformers
- Groq API (LLaMA 3)
- xarray + netCDF4
- Pandas + PyArrow (Parquet)

**Frontend**

- Streamlit
- Plotly (scatter_geo, depth profiles, timeseries)
- Custom CSS (glassmorphism dark theme)

## Running Locally

```bash
# 1. Clone and install
git clone https://github.com/nishkarshs1/seaBorg.git
cd seaBorg
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Fill in DATABASE_URL and GROQ_API_KEY

# 3. Setup database
python scripts/setup_db.py

# 4. Download ARGO data and ingest
# Place .nc files in data/raw/
python scripts/run_ingestion.py
python scripts/build_index.py

# 5. Run backend (Terminal 1)
uvicorn api.main:app --reload --port 8001

# 6. Run frontend (Terminal 2)
streamlit run frontend/app.py
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)

## Project Structure

```
seaBorg/
├── api/                    # FastAPI backend
│   ├── main.py             # App entry + startup
│   ├── models.py           # Pydantic schemas
│   └── routes/             # chat, data, export endpoints
├── frontend/               # Streamlit UI
│   ├── app.py              # Main entry + CSS
│   ├── components/         # sidebar, chat_panel, chart_panel
│   └── pages/              # 4 pages: chat, explorer, about, analytics
├── ingestion/              # ETL pipeline
│   ├── parser.py           # NetCDF parsing (xarray)
│   ├── qc_filter.py        # Quality control filtering
│   └── db_loader.py        # PostgreSQL + Parquet storage
├── rag/                    # RAG pipeline
│   ├── summariser.py       # Row to text conversion
│   ├── embedder.py         # sentence-transformers
│   ├── indexer.py          # FAISS index builder
│   └── retriever.py        # Semantic search
├── llm/                    # LLM layer
│   ├── prompts.py          # Prompt templates
│   ├── query_engine.py     # RAG + LLM orchestration
│   └── nl_to_sql.py        # NL to SQL + safety filter
├── visualisation/          # Plotly chart generators
│   ├── map_chart.py        # Geospatial float map
│   ├── profile_chart.py    # Depth profile (inverted Y)
│   └── timeseries_chart.py # Temporal trends
├── scripts/                # Setup and ingestion scripts
├── .env.example            # Environment template
└── requirements.txt
```

## Author

**Nishkarsh Sharma**
B.Tech CSE, IIITDM Jabalpur (2nd Year)
[GitHub](https://github.com/nishkarshs1)

_SeaBorg - Making ocean data accessible to everyone._
