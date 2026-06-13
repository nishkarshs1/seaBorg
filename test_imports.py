import importlib
import sys

modules_to_test = [
    "api.main", "api.models", "api.tools",
    "api.routes.chat", "api.routes.data", "api.routes.export",
    "frontend.app", 
    "frontend.components.chart_panel", "frontend.components.chat_panel", "frontend.components.sidebar",
    "ingestion.db_loader", "ingestion.downloader", "ingestion.parser", "ingestion.qc_filter",
    "llm.geo_mapping", "llm.nl_to_sql", "llm.prompts", "llm.query_engine",
    "rag.embedder", "rag.indexer", "rag.retriever", "rag.summariser",
    "visualisation.exporter", "visualisation.map_chart", "visualisation.profile_chart", "visualisation.timeseries_chart"
]

for mod in modules_to_test:
    try:
        importlib.import_module(mod)
        print(f"[OK] {mod}")
    except Exception as e:
        print(f"[ERROR] {mod}: {e}")
