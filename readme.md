<div align="center">
  <h1>SeaBorg 🌊</h1>
  <h3>AI-Powered Ocean Intelligence Platform</h3>
  <p>Query, explore, and visualise <strong>694,182 real ARGO float sensor readings</strong> using plain natural language.<br/>Ask about ocean temperature, salinity, or depth - get grounded AI answers with live Plotly charts.</p>

[![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react)](http://localhost:8080)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)](http://localhost:8001)
[![Docker](https://img.shields.io/badge/Docker-nishkarshs1%2Fseaborg-2496ED?style=for-the-badge&logo=docker)](https://hub.docker.com/r/nishkarshs1/seaborg)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![ACL 2024](https://img.shields.io/badge/Based_on-OceanGPT_ACL_2024-gold?style=for-the-badge)](https://arxiv.org/abs/2310.02031)

</div>

## What is SeaBorg?

SeaBorg is a full-stack AI system that makes real ARGO float oceanographic data accessible through natural language. It implements the core RAG architecture from the **OceanGPT ACL 2024** research paper - applying Retrieval-Augmented Generation to live sensor data from robotic ocean floats that have been diving to 2,000m depths since 2002.

Type _"What is the average temperature of the Indian Ocean?"_ and SeaBorg retrieves the 5 most relevant real sensor readings from its FAISS vector index, passes them as grounded context to LLaMA 3, and renders an interactive map alongside the answer - all in under 2 seconds.

## Screenshots

**Ocean Chat - Natural language querying with live ARGO float map**
<img src="screenshots/chat.png" alt="Ocean Chat" width="900" />

**Data Explorer - 694,182 readings across 43 floats spanning 2002 to 2026**
<img src="screenshots/explorer.png" alt="Data Explorer" width="900" />

**How It Works - Full ML pipeline with algorithm cards and system metrics**
<img src="screenshots/how_it_works.png" alt="How It Works" width="900" />

**Advanced Analytics - T-S diagrams, depth distributions, temporal analysis**
<img src="screenshots/analytics.png" alt="Analytics" width="900" />

**System Reliability - RAGAS accuracy scorecards, stress testing benchmarks, and downloadable PDF reports**
<img src="screenshots/evaluation.png" alt="System Reliability" width="900" />

## System Metrics

| Metric                    | Value           |
| ------------------------- | --------------- |
| **ARGO Records**          | **694,182**     |
| **Active Floats**         | **43**          |
| **Date Coverage**         | **2002 - 2026** |
| **Max Depth Recorded**    | **2,054m**      |
| **Embedding Dimensions**  | **384D**        |
| **FAISS Retrieval Speed** | **1.44ms**      |
| **QC Pass Rate**          | **75.34%**      |
| **Groq API Latency**      | **~1.2s**       |
| **Avg LLM Tokens**        | **84**          |
| **LLM Temperature**       | **0.2**         |

## Architecture

```
User Question (natural language)
        |
        v
React Frontend (TanStack Start) - http://localhost:8080
        |  POST /api/chat
        v
FastAPI Backend (Local/Uvicorn) - http://localhost:8001
        |
        +---> RAG Retriever
        |         |
        |         v
        |     FAISS Index (694,182 vectors x 384D)
        |         |
        |         v
        |     Top-5 relevant ARGO sensor records
        |
        +---> LLaMA 3 via Groq
        |         |
        |         v
        |     Grounded answer (reads only retrieved data)
        |
        +---> Chart Type Detection
                  |
                  v
        Response: {answer, chart_type, float_ids, sql_used, confidence}
                  |
                  v
        Plotly Chart (map / depth profile / timeseries)
```

## The SeaBorg Pipeline

```
Raw .nc NetCDF files (ARGO float sensor data)
        |
        v
Stage 1: ETL Pipeline
        parser.py     - xarray reads multidimensional NetCDF arrays
        qc_filter.py  - Accept QC flags 1 (Good) and 2 (Probably good) only
                        Reject: temp outside -3 to 40C, salinity outside 20-42 PSU
        db_loader.py  - Write to PostgreSQL + Parquet (columnar, fast reads)
        |
        v
Stage 2: Text Summaries
        summariser.py - Each row becomes a sentence:
        "Float D13857 recorded 14.2C and 35.10 PSU at 100m on 2023-04-12"
        |
        v
Stage 3: Embeddings
        embedder.py   - all-MiniLM-L6-v2 -> 384-dimensional float32 vectors
        |
        v
Stage 4: FAISS Index
        indexer.py    - IndexFlatL2, exact L2 nearest neighbor
                        694,182 vectors indexed
        |
        v  [At query time]
Stage 5: Semantic Retrieval
        retriever.py  - Question -> vector -> top-5 nearest ARGO records (1.44ms)
        |
        v
Stage 6: LLM Generation
        query_engine.py - Context + question -> LLaMA 3 via Groq -> grounded answer
        |
        v
Stage 7: NL-to-SQL
        nl_to_sql.py  - Question -> PostgreSQL query + 7-keyword safety blocklist
```

## ML Algorithms

**Sentence Transformers (all-MiniLM-L6-v2)**

- Architecture: 6-layer transformer, 384-dimensional output vectors
- Purpose: Converts ocean data text summaries into semantic vectors
- Why chosen: Lightweight (80MB), runs entirely on CPU, optimized for similarity search
- Key property: Similar ocean conditions produce mathematically close vectors

**FAISS (Facebook AI Similarity Search)**

- Index type: IndexFlatL2 - exact L2 Euclidean distance search
- Scale: 694,182 vectors indexed
- Speed: 1.44ms average retrieval on CPU

**RAG (Retrieval-Augmented Generation)**

- Retriever: FAISS semantic search finds the 5 most relevant ARGO records
- Generator: LLaMA 3 reads only the retrieved context to produce answers
- Key advantage: The LLM cannot hallucinate sensor values - it only reads real retrieved data

**LLaMA 3 via Groq**

- Model: llama-3.1-8b-instant
- Provider: Groq LPU inference (ultra-fast hardware)
- Temperature: 0.2 (factual, consistent, minimal creativity)
- Dual role: Answer generation AND natural language to SQL translation

**Natural Language to SQL**

- Input: Plain English question about ocean data
- Output: PostgreSQL query on the argo_profiles table
- Safety filter: Blocks DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, GRANT
- Transparency: Generated SQL shown in UI expander for every response

**Quality Control Pipeline**

- ARGO QC flags: Accept flag 1 (Good) and flag 2 (Probably good) only
- Range validation: Temperature -3 to 40C, Salinity 20 to 42 PSU, Depth > 0m
- Pass rate: 75.34% of raw sensor readings pass QC

## Why RAG over Fine-tuning?

| Approach           | Pros                                      | Cons                           | SeaBorg     |
| ------------------ | ----------------------------------------- | ------------------------------ | ----------- |
| RAG                | Always uses latest data, no hallucination | Slower inference               | YES         |
| Fine-tuning        | Fast inference, domain adapted            | Expensive, data goes stale     | Future Work |
| Prompt engineering | Simple, no training                       | Limited context window         | Partial     |
| Vector DB only     | Fast retrieval                            | No natural language generation | NO          |

Ocean data changes constantly. A fine-tuned model would go stale immediately. RAG always retrieves the exact, latest ARGO readings before answering.

## SeaBorg vs OceanGPT (ACL 2024)

| Feature                      | OceanGPT Paper       | SeaBorg                        |
| ---------------------------- | -------------------- | ------------------------------ |
| RAG pipeline                 | YES                  | YES                            |
| Domain-specific embeddings   | YES                  | YES                            |
| NL-to-SQL                    | YES                  | YES                            |
| Real-time sensor data (ARGO) | NO - static datasets | YES - live ingestion           |
| Interactive visualizations   | NO                   | YES - map, profile, timeseries |
| Multi-page educational UI    | NO                   | YES - 4 pages                  |
| Export functionality (CSV)   | NO                   | YES                            |
| LLM fine-tuning              | YES                  | Future Work                    |
| DoInstruct data framework    | YES                  | Future Work                    |

**Research Paper:** [OceanGPT: A Large Language Model for Ocean Science Tasks (ACL 2024)](https://arxiv.org/abs/2310.02031)

**Original Repository:** [github.com/OceanGPT/OceanGPT](https://github.com/OceanGPT/OceanGPT)

## Pages

| Page               | What it shows                                                                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Ocean Chat**     | Two-column chat + live Plotly chart (map/profile/timeseries auto-selected). Generated SQL visible in expander. CSV download.                     |
| **Data Explorer**  | Stats cards (694,182 records, 43 floats, 2002-2026). Interactive world map with custom rule-based filter builder (filtering by temp, salinity, depth, coordinates), floating filter history panel, and a float summary table. |
| **How It Works**   | Full pipeline diagram. 6 ML algorithm cards. 8 system performance metrics. Why RAG comparison table. ARGO float science. OceanGPT paper section. |
| **Analytics**      | Temperature distribution. Depth distribution. T-S diagram (colored by depth). Readings over time. Float comparison charts.                       |
| **System Reliability**| RAG Accuracy metrics (Faithfulness, Relevancy, Recall, Precision), pass rate logs for multi-turn adversarial stress testing, and PDF download.  |

## API Reference

**POST /api/chat**

```json
Request:
{
  "message": "What is the temperature at 500m depth in the Indian Ocean?"
}

Response:
{
  "answer": "Based on the retrieved ARGO data, Float 1900121 recorded 8.1C at 500m...",
  "chart_type": "profile",
  "float_ids": ["1900121", "1902669"],
  "sql_used": "SELECT * FROM argo_profiles WHERE depth_m BETWEEN 480 AND 520",
  "confidence": 0.85
}
```

Chart types: `"map"` | `"profile"` | `"timeseries"` | `"none"`

**GET /health** - Backend status check

**GET /api/stats** - Total rows, float count, date range, avg temperature

**GET /api/floats** - All float IDs with coordinate ranges

**POST /api/export** - Download filtered data as CSV

## Running with Docker (Recommended)

The entire backend is packaged into a publicly available Docker image - zero setup required.

```bash
# Pull the image
docker pull nishkarshs1/seaborg

# Run with your environment variables
docker run -p 8080:8080 \
  -e GROQ_API_KEY=your_key \
  -e DATABASE_URL=your_postgres_url \
  nishkarshs1/seaborg
```

Backend will be available at `http://localhost:8080`

## Running Locally

```bash
# 1. Clone and install
git clone https://github.com/nishkarshs1/seaBorg.git
cd seaBorg
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env: add DATABASE_URL and GROQ_API_KEY

# 3. Setup PostgreSQL database
python scripts/setup_db.py

# 4. Download ARGO NetCDF files
# Place .nc files in data/raw/
# Free source: https://data-argo.ifremer.fr/dac/incois/

# 5. Run the ETL pipeline
python scripts/run_ingestion.py

# 6. Build the FAISS vector index
python scripts/build_index.py

# 7. Start the backend (Terminal 1)
python start_server.py
# Running on http://localhost:8001

# 8. Start the React frontend (Terminal 2)
cd frontend-react
npm install
npm run dev
# Opens at http://localhost:8080
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)

## Environment Variables

### Backend Configuration (`.env`)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/seaborg
GROQ_API_KEY=your_groq_api_key_here
ENVIRONMENT=development
FRONTEND_URL=http://localhost:8080
FAISS_INDEX_PATH=indexes/argo.faiss
PARQUET_PATH=data/processed/argo.parquet
LLM_MODEL=llama-3.1-8b-instant
### Frontend Configuration (`frontend-react/.env`)
```bash
VITE_API_URL=http://localhost:8001
```

## Project Structure

```
seaBorg/
├── api/
│   ├── main.py             # FastAPI app + CORS configuration
│   ├── models.py           # Pydantic schemas
│   └── routes/
│       ├── chat.py         # POST /api/chat (stateless RAG)
│       ├── data.py         # GET /api/floats, /api/stats
│       └── export.py       # POST /api/export
├── db/
│   └── connection.py       # SQLAlchemy engine and connection helper
├── frontend-react/         # TanStack Start React Frontend
│   ├── src/
│   │   ├── routes/
│   │   │   ├── index.tsx         # Dashboard / Entry
│   │   │   ├── chat.tsx          # Ocean Chat (Plotly widgets)
│   │   │   ├── explorer.tsx      # Data Explorer (Mercator scattergeo)
│   │   │   ├── analytics.tsx     # Advanced Analytics (T-S diagrams, box plots)
│   │   │   ├── about.tsx         # How It Works / Architectural Deep Dive
│   │   │   └── evaluation.tsx    # System Reliability Dashboard (Accuracy stats)
│   │   ├── components/           # UI elements & layout wrappers
│   │   └── lib/
│   │       ├── api.ts            # Dynamic Axios client
│   │       └── mocks.ts          # Charts fallbacks and static metrics
│   ├── vite.config.ts            # Vite & Nitro compiler configuration
│   └── package.json
├── ingestion/
│   ├── downloader.py       # Raw NetCDF file downloader
│   ├── parser.py           # NetCDF parsing with xarray
│   ├── qc_filter.py        # Quality control filtering
│   └── db_loader.py        # PostgreSQL + Parquet writer
├── rag/
│   ├── summariser.py       # Row to natural language
│   ├── embedder.py         # sentence-transformers
│   ├── indexer.py          # FAISS index builder
│   └── retriever.py        # Semantic search
├── llm/
│   ├── prompts.py          # Prompt templates
│   ├── query_engine.py     # RAG + LLM orchestration
│   └── nl_to_sql.py        # NL to SQL + safety filter
├── visualisation/
│   ├── map_chart.py
│   ├── profile_chart.py
│   └── timeseries_chart.py
├── scripts/
│   ├── setup_db.py         # Database initialization script
│   ├── run_ingestion.py    # Main ETL pipeline runner
│   ├── build_index.py      # FAISS index builder script
│   ├── download_argo.py    # Raw data fetching utility
│   ├── download_incois.py  # INCOIS dataset mirror utility
│   ├── evaluate_rag.py     # Offline retrieval/faithfulness evaluator
│   ├── fetch_sample_data.py # Sample mock loader script
│   └── generate_report_pdf.py # Report PDF compiler script
├── tests/
│   ├── test_regression_suite.py # 15 scenario regression runs
│   ├── evaluate_rag.py          # Custom RAGAS-style evaluator
│   ├── test_chat_report_export.py # Chat export validation tests
│   └── verify_visualization_rag.py # Visualizer alignment validation tests
├── Dockerfile
├── .env.example
├── requirements.txt
└── start_server.py         # API uvicorn service startup entrypoint
```

## Author

**Nishkarsh Sharma**
B.Tech CSE, IIITDM Jabalpur (2nd Year)
[GitHub](https://github.com/nishkarshs1) • [Docker Hub](https://hub.docker.com/r/nishkarshs1/seaborg)

_SeaBorg - Making ocean data accessible to everyone._
