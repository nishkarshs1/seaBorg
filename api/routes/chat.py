import os
import functools
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from fastapi import APIRouter

from api.models import ChatRequest, ChatResponse
from llm.query_engine import answer_query
from rag.retriever import retrieve

load_dotenv()

router = APIRouter()


def detect_chart_type(message: str) -> str:
    """
    Classifies a user message into exactly one chart type using the LLM.
    """
    msg = message.lower().strip()
    
    # Check query length first - if under 15 characters, return "none" immediately.
    if len(msg) < 15:
        return "none"
        
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=10.0)
        model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        prompt = (
            "Classify this query into exactly one of these chart types:\n"
            "- map: showing locations, regions, or coordinates (e.g. show me the map near 15N 70E)\n"
            "- profile: vertical profiles of temperature/salinity/depth (e.g. deepest dive, temperature profile)\n"
            "- timeseries: trends or changes over time (e.g. change over the year, trend over time)\n"
            "- ts_diagram: temperature vs salinity diagram (e.g. ts plot, temp vs salinity)\n"
            "- 3d_trajectory: journey, path, track, route of a float (e.g. journey of float X, 3d path)\n"
            "- comparison: comparing multiple floats or parameters (e.g. compare float A and float B)\n"
            "- anomaly: anomalies, weirdness, deviations, outliers (e.g. weird temperature, salinity anomalies)\n"
            "- summary: statistical overview, metrics, summary card (e.g. summarize stats)\n"
            "- none: simple greetings, off-topic, or queries not requiring a chart (e.g. hello, hey there)\n\n"
            f"Query: {message}\n"
            "Respond with only the chart type word, nothing else."
        )
        import time
        import re
        for attempt in range(5):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=20,
                    timeout=10.0,
                )
                result = response.choices[0].message.content.strip().lower()
                break
            except Exception as e:
                if attempt < 4 and ("rate_limit" in str(e).lower() or "429" in str(e) or "limit reached" in str(e).lower()):
                    wait_time = 2.0
                    match = re.search(r'try again in (\d+(?:\.\d+)?)s', str(e).lower())
                    if match:
                        wait_time = float(match.group(1)) + 0.5
                    print(f"[DEBUG] Rate limited. Sleeping for {wait_time}s...", flush=True)
                    time.sleep(wait_time)
                    continue
                raise e
        
        # Validate that the returned word is indeed one of our valid chart types
        valid_types = {"map", "profile", "timeseries", "ts_diagram", "3d_trajectory", "comparison", "anomaly", "summary", "none"}
        if result in valid_types:
            return result
            
        # If it returned a phrase or invalid type, find the chart type word inside it
        for t in valid_types:
            if t in result:
                return t
                
        return "none"
    except Exception as e:
        print(f"WARNING: Chart classification LLM call failed. Defaulting to 'none'. Error: {e}", flush=True)
        return "none"


def serialize_df(df: pd.DataFrame) -> list[dict]:
    """
    Converts a pandas DataFrame into a list of dicts that is fully JSON serializable,
    handling Timestamp conversion and NaN/NaT/NA to None mapping, and formats keys
    for compatibility with both old Streamlit and new React visualizers.
    """
    if df.empty:
        return []
    out = df.copy()
    if "date" in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out["date"]):
            out["date"] = out["date"].dt.strftime('%Y-%m-%d')
        else:
            out["date"] = out["date"].astype(str)
            
    # Replace standard pandas null types with None
    out = out.fillna(value=None)
    out = out.replace({pd.NA: None})
    # Also handle numeric float NaNs and Infs which FastAPI/JSON encoding rejects
    out = out.replace({np.nan: None, np.inf: None, -np.inf: None})
    
    records = out.to_dict(orient="records")
    for r in records:
        r["id"] = r.get("id") or r.get("float_id")
        r["float_id"] = r.get("float_id") or r.get("id")
        r["lat"] = r.get("latitude")
        r["lng"] = r.get("longitude")
        r["temp"] = r.get("temp_c")
        r["depth"] = r.get("depth_m")
        
    return records


def has_ocean_intent(message: str) -> bool:
    msg = message.lower()
    
    # 1. Check for float ID (regex)
    import re
    if re.search(r'(?:[A-Z][0-9]{7}|[0-9]{7})', msg):
        return True
        
    # 2. Check for coordinates (latitude / longitude coords pattern)
    from rag.retriever import extract_coordinates
    if extract_coordinates(message):
        return True
        
    # 3. Check for keywords
    ocean_keywords = [
        "temperature", "temp", "temp_c", "salinity", "depth", "pressure", "dbar",
        "ocean", "argo", "float", "profile", "sea surface", "anomalies", "trajectory",
        "journey", "path", "route", "track", "oxygen"
    ]
    if any(kw in msg for kw in ocean_keywords):
        return True
        
    return False


@functools.lru_cache(maxsize=20)
def _process_chat_cached(message: str, ocean: str | None = None, history_tuple: tuple | None = None):
    chart_type = detect_chart_type(message)
    
    # Skip retrieval entirely if the chart is "none" and there is no oceanographic intent in the query
    should_retrieve = (chart_type != "none") or has_ocean_intent(message)
    
    if should_retrieve:
        # Fetch 100 rows if a chart is triggered to supply sufficient plotting points.
        # Otherwise, default to 5 rows to keep text response context concise.
        top_k = 500 if chart_type == "timeseries" else (100 if chart_type != "none" else 5)
        rows = retrieve(message, top_k=top_k, ocean=ocean, chart_type=chart_type)
    else:
        rows = pd.DataFrame()
        
    res = answer_query(message, rows, history_tuple=history_tuple)
    
    if chart_type == "timeseries" and not rows.empty:
        num_distinct_dates = 0
        if "date" in rows.columns:
            unique_dates = pd.to_datetime(rows["date"]).dt.date.unique()
            num_distinct_dates = len(unique_dates)
        if num_distinct_dates < 3:
            chart_type = "none"
            fids = rows["float_id"].unique().tolist() if "float_id" in rows.columns else []
            fid_str = ", ".join(str(f) for f in fids) if fids else "unknown"
            fallback_msg = f"Insufficient time-series data: only {num_distinct_dates} distinct measurement dates available for float {fid_str}. A minimum of 3 dates is required to show a meaningful trend."
            res = {
                "status": "refused",
                "refusal_type": "sparse_timeseries",
                "answer": fallback_msg,
                "sql": res.get("sql", "-- SQL query")
            }
    
    # Suppress chart entirely if backend query returns a refusal or rows are empty
    if res.get("status") == "refused" or rows.empty:
        chart_type = "none"
        float_ids = []
        serialized_data = []
    else:
        float_ids = rows["float_id"].unique().tolist() if "float_id" in rows.columns else []
        serialized_data = serialize_df(rows)
        
    return res["answer"], res.get("sql", "-- SQL query"), chart_type, float_ids, serialized_data


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Handles POST /chat. Retrieves ARGO context, calls LLM, returns structured response.
    """
    history_tuple = None
    if req.history:
        # Convert list of dicts to tuple of tuples to make it hashable for lru_cache
        history_tuple = tuple(
            (h.get("role", ""), h.get("text") or h.get("content", ""))
            for h in req.history
        )

    answer, sql, chart_type, float_ids, serialized_data = _process_chat_cached(
        req.message, req.ocean, history_tuple
    )

    return ChatResponse(
        answer=answer,
        chart_type=chart_type,
        float_ids=float_ids,
        sql_used=sql,
        confidence=0.85,
        data=serialized_data
    )