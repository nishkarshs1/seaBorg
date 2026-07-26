import os
import functools
import json
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

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
        
    records = df.to_dict(orient="records")
    cleaned_records = []
    
    for r in records:
        cleaned_r = {}
        for k, v in r.items():
            if pd.isna(v) or v is None:
                cleaned_r[k] = None
            elif isinstance(v, pd.Timestamp) or hasattr(v, 'strftime'):
                cleaned_r[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(v, 'item') and callable(getattr(v, 'item')):
                try:
                    cleaned_r[k] = v.item()
                except Exception:
                    cleaned_r[k] = str(v)
            else:
                cleaned_r[k] = v
                
        cleaned_r["id"] = cleaned_r.get("id") or cleaned_r.get("float_id")
        cleaned_r["float_id"] = cleaned_r.get("float_id") or cleaned_r.get("id")
        cleaned_r["lat"] = cleaned_r.get("latitude")
        cleaned_r["lng"] = cleaned_r.get("longitude")
        cleaned_r["temp"] = cleaned_r.get("temp_c")
        cleaned_r["depth"] = cleaned_r.get("depth_m")
        cleaned_records.append(cleaned_r)
        
    return cleaned_records


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


def is_explanation_followup(message: str) -> bool:
    """Checks if the follow-up question is asking to explain or justify a prior answer/calculation."""
    msg = message.lower().strip()
    keywords = [
        "how did you", "how did ou", "how was this", "how was that",
        "where did", "explain this", "explain that", "explain how",
        "why is it", "why did you", "how calculated", "what formula",
        "how did you find", "how did ou find", "where is that from",
        "how was it found", "how it found", "how you find", "how do you find"
    ]
    return any(kw in msg for kw in keywords)


def has_explicit_chart_request(message: str) -> bool:
    """Checks if the query explicitly asks for a chart/visualization."""
    msg = message.lower()
    keywords = [
        "chart", "plot", "graph", "visualize", "map", "profile", 
        "timeseries", "trend", "trajectory", "journey", "path", "route",
        "diagram", "compare", "comparison", "anomaly", "anomalies", "show me on",
        "draw", "display", "render", "3d"
    ]
    return any(kw in msg for kw in keywords)


def _process_chat_cached(message: str, ocean: str | None = None, history_tuple: tuple | None = None):
    from llm.query_engine import is_conversational_only
    import re as _re

    # ── Context Augmentation for Follow-up Queries ──────────────────────────
    # When a follow-up like "give me exact date" has no ocean intent on its own,
    # extract float IDs and keywords from conversation history to augment the query
    # so retrieval doesn't get bypassed.
    augmented_message = message
    history_context_floats = []
    has_own_float = bool(_re.search(r'(?:[A-Z][0-9]{7}|[0-9]{7})', message))
    is_followup = bool(history_tuple and not has_own_float)
    is_explanation = is_followup and is_explanation_followup(message)

    if is_followup and not is_explanation:
        # Scan history for float IDs and ocean keywords from previous turns
        for role, text in history_tuple:
            found_fids = _re.findall(r'(?:[A-Z][0-9]{7}|[0-9]{7})', text)
            history_context_floats.extend(found_fids)

        # Deduplicate and take the most recent float IDs
        seen = set()
        unique_floats = []
        for fid in reversed(history_context_floats):
            if fid not in seen:
                seen.add(fid)
                unique_floats.append(fid)
        unique_floats = unique_floats[:3]  # Limit to 3 most recent floats

        if unique_floats:
            # Augment the user's message with context from history
            float_context = " ".join(f"Float {fid}" for fid in unique_floats)
            augmented_message = f"{message} (context: {float_context})"

    if is_conversational_only(message) and not history_context_floats:
        res = answer_query(message, pd.DataFrame(), history_tuple=history_tuple, ocean=ocean)
        return (
            res["answer"],
            res.get("sql", "-- SQL query"),
            "none",
            [],
            [],
            [],
            ["Router: Fast conversational query bypass triggered -> Direct LLM chat response"],
            []
        )

    # For follow-up queries that do NOT explicitly ask for a chart, force chart_type = "none"
    if is_followup and not has_explicit_chart_request(message):
        chart_type = "none"
    else:
        chart_type = detect_chart_type(message)

    pipeline_trace = [f"Router: Classified query chart type as '{chart_type}'"]
    
    should_retrieve = (chart_type != "none") or has_ocean_intent(augmented_message) or is_explanation
    
    if should_retrieve:
        top_k = 500 if chart_type == "timeseries" else (100 if chart_type != "none" else 5)
        rows = retrieve(augmented_message, top_k=top_k, ocean=ocean, chart_type=chart_type)
        method = rows.attrs.get("retrieval_method", "FAISS Vector Search")
        if "PostgreSQL" in method:
            pipeline_trace.append("Router: Ocean query detected -> Routed to Relational DB Engine")
            pipeline_trace.append(f"Retrieval: Executed query via {method} -> Retrieved {len(rows)} row(s)")
            if "sql_query" in rows.attrs:
                pipeline_trace.append(f"PostgreSQL SQL Executed: {rows.attrs['sql_query']}")
        else:
            pipeline_trace.append("Router: Ocean query detected -> Routed to Vector Search Engine")
            pipeline_trace.append(f"Retrieval: Executed FAISS Vector index search -> Retrieved {len(rows)} matching profile(s)")
    else:
        if is_explanation:
            pipeline_trace.append("Retrieval: Bypassed database search (explanation follow-up question -> using conversation history)")
        else:
            pipeline_trace.append("Retrieval: Bypassed database search (no oceanographic intent)")
        rows = pd.DataFrame()
        
    # Scientific Validation
    from llm.validation import validate_physical_limits
    validation_warnings = validate_physical_limits(rows)
    if should_retrieve:
        pipeline_trace.append(
            f"Validator: Checked physical constraints on {len(rows)} records -> "
            f"Found {len(validation_warnings)} warning(s)"
        )
        
    pipeline_trace.append("Summarizer: Sending data context to Groq LLM for answer generation")
    res = answer_query(message, rows, history_tuple=history_tuple, ocean=ocean)
    
    is_aggregate = not rows.empty and ("float_id" not in rows.columns or rows["float_id"].isna().all())
    if is_aggregate:
        chart_type = "none"

    if chart_type == "comparison" and not rows.empty and "float_id" in rows.columns:
        unique_fids = rows["float_id"].dropna().unique()
        if len(unique_fids) <= 1:
            chart_type = "profile"
    
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
            pipeline_trace.append("Validator: Time-series rejected due to insufficient measurement dates (< 3)")
    
    # Suppress chart entirely if backend query returns a refusal or rows are empty
    if res.get("status") == "refused" or rows.empty:
        chart_type = "none"
        float_ids = []
        serialized_data = []
        source_files = []
    else:
        float_ids = [str(fid) for fid in rows["float_id"].dropna().unique().tolist() if fid is not None and not pd.isna(fid)] if "float_id" in rows.columns else []
        serialized_data = serialize_df(rows)
        if not float_ids and should_retrieve:
            method = rows.attrs.get("retrieval_method", "")
            if "PostgreSQL" in method:
                source_files = ["PostgreSQL Relational Database Table (argo_profiles)"]
            else:
                source_files = ["Local Dataset (argo.parquet via FAISS index)"]
        else:
            source_files = [f"{fid}_prof.nc" for fid in float_ids]
            
    pipeline_trace.append("Summarizer: Response generated successfully")
    
    return (
        res["answer"],
        res.get("sql", "-- SQL query"),
        chart_type,
        float_ids,
        serialized_data,
        source_files,
        pipeline_trace,
        validation_warnings
    )


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

    (
        answer, sql, chart_type, float_ids, serialized_data,
        source_files, pipeline_trace, validation_warnings
    ) = _process_chat_cached(req.message, req.ocean, history_tuple)

    return ChatResponse(
        answer=answer,
        chart_type=chart_type,
        float_ids=float_ids,
        sql_used=sql,
        confidence=0.85,
        data=serialized_data,
        source_files=source_files,
        pipeline_trace=pipeline_trace,
        validation_warnings=validation_warnings
    )


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """
    Handles POST /chat/stream. Streams LLM response and structured metadata as Server-Sent Events.
    """
    import re
    import time
    from rag.retriever import extract_coordinates

    def event_generator():
        try:
            from llm.query_engine import is_conversational_only

            # ── Context Augmentation (same as non-streaming path) ──────────
            import re as _re
            augmented_message = req.message
            history_context_floats = []

            if req.history and not has_ocean_intent(req.message):
                for h in req.history:
                    text = h.get("text") or h.get("content", "")
                    found_fids = _re.findall(r'(?:[A-Z][0-9]{7}|[0-9]{7})', text)
                    history_context_floats.extend(found_fids)
                seen = set()
                unique_floats = []
                for fid in reversed(history_context_floats):
                    if fid not in seen:
                        seen.add(fid)
                        unique_floats.append(fid)
                unique_floats = unique_floats[:3]
                if unique_floats:
                    float_context = " ".join(f"Float {fid}" for fid in unique_floats)
                    augmented_message = f"{req.message} (context: {float_context})"

            if is_conversational_only(req.message) and not history_context_floats:
                sql = "-- Conversational query (no database lookup required)"
                yield f"data: {json.dumps({'type': 'meta', 'chart_type': 'none', 'sql_used': sql, 'float_ids': [], 'data': []})}\n\n"
                
                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
                model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
                history = []
                if req.history:
                    for h in req.history:
                        role = "user" if h.get("role") == "user" else "assistant"
                        content = h.get("text") or h.get("content") or ""
                        if content.strip():
                            history.append({"role": role, "content": content})
                
                system_prompt = (
                    "You are SeaBorg, an intelligent AI assistant specialized in oceanography and ARGO float data. "
                    "Acknowledge greetings and casual questions warmly and concisely. Introduce your capabilities briefly "
                    "if asked. Do not try to reference databases or tables for casual chat."
                )
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history)
                messages.append({"role": "user", "content": req.message})
                
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024,
                    timeout=10.0,
                    stream=True
                )
                for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield f"data: {json.dumps({'type': 'chunk', 'text': delta})}\n\n"
                
                yield "data: {\"type\": \"done\"}\n\n"
                return

            has_own_float_stream = bool(re.search(r'(?:[A-Z][0-9]{7}|[0-9]{7})', req.message))
            is_followup = bool(req.history and not has_own_float_stream)
            is_explanation = is_followup and is_explanation_followup(req.message)

            if is_followup and not has_explicit_chart_request(req.message):
                chart_type = "none"
            else:
                chart_type = detect_chart_type(req.message)

            pipeline_trace = [f"Router: Classified query chart type as '{chart_type}'"]
            
            should_retrieve = (chart_type != "none") or has_ocean_intent(augmented_message) or is_explanation
            
            if should_retrieve:
                top_k = 500 if chart_type == "timeseries" else (100 if chart_type != "none" else 5)
                rows = retrieve(augmented_message, top_k=top_k, ocean=req.ocean, chart_type=chart_type)
                method = rows.attrs.get("retrieval_method", "FAISS Vector Search")
                if "PostgreSQL" in method:
                    pipeline_trace.append("Router: Ocean query detected -> Routed to Relational DB Engine")
                    pipeline_trace.append(f"Retrieval: Executed query via {method} -> Retrieved {len(rows)} row(s)")
                    if "sql_query" in rows.attrs:
                        pipeline_trace.append(f"PostgreSQL SQL Executed: {rows.attrs['sql_query']}")
                else:
                    pipeline_trace.append("Router: Ocean query detected -> Routed to Vector Search Engine")
                    pipeline_trace.append(f"Retrieval: Executed FAISS Vector index search -> Retrieved {len(rows)} matching profile(s)")
            else:
                if is_explanation:
                    pipeline_trace.append("Retrieval: Bypassed database search (explanation follow-up question -> using conversation history)")
                else:
                    pipeline_trace.append("Retrieval: Bypassed database search (no oceanographic intent)")
                rows = pd.DataFrame()

            try:
                from llm.nl_to_sql import generate_sql
                sql = generate_sql(req.message, req.ocean)
            except Exception:
                sql = "-- SQL generation failed"

            # Scientific Validation
            from llm.validation import validate_physical_limits
            validation_warnings = validate_physical_limits(rows)
            if should_retrieve:
                pipeline_trace.append(
                    f"Validator: Checked physical constraints on {len(rows)} records -> "
                    f"Found {len(validation_warnings)} warning(s)"
                )

            # Check timeseries constraints
            is_timeseries_refused = False
            fallback_msg = ""
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
                    is_timeseries_refused = True
                    pipeline_trace.append("Validator: Time-series rejected due to insufficient measurement dates (< 3)")

            if is_timeseries_refused:
                yield f"data: {json.dumps({'type': 'meta', 'chart_type': 'none', 'sql_used': sql, 'float_ids': [], 'data': [], 'source_files': [], 'pipeline_trace': pipeline_trace, 'validation_warnings': validation_warnings})}\n\n"
                yield f"data: {json.dumps({'type': 'chunk', 'text': fallback_msg})}\n\n"
                yield "data: {\"type\": \"done\"}\n\n"
                return

            coords = extract_coordinates(req.message)
            if coords:
                lat, lon = coords
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    yield f"data: {json.dumps({'type': 'meta', 'chart_type': 'none', 'sql_used': sql, 'float_ids': [], 'data': [], 'source_files': [], 'pipeline_trace': pipeline_trace, 'validation_warnings': validation_warnings})}\n\n"
                    yield f"data: {json.dumps({'type': 'chunk', 'text': 'Invalid coordinates: Latitude must be between -90 and 90, and Longitude must be between -180 and 180.'})}\n\n"
                    yield "data: {\"type\": \"done\"}\n\n"
                    return

            cleaned_q = re.sub(r'\b(?:float|id|no\.?|number)\s+\d+\b', '', req.message.lower())
            found_years = []
            for m in re.finditer(r'\b(20\d{2})[-/]\d{2}(?:[-/]\d{2})?\b', cleaned_q):
                found_years.append(int(m.group(1)))
            for m in re.finditer(r'\b(?:in|on|for|during|before|after|to|at|since|until|date|year)\s+(20\d{2})\b', cleaned_q):
                found_years.append(int(m.group(1)))
                
            if found_years:
                max_year = max(found_years)
                current_max_year = 2026
                try:
                    from db.connection import get_engine
                    from sqlalchemy import text
                    engine = get_engine()
                    with engine.connect() as conn:
                        res_max = conn.execute(text("SELECT MAX(EXTRACT(YEAR FROM date)) FROM argo_profiles")).scalar()
                        if res_max:
                            current_max_year = int(res_max)
                except Exception:
                    try:
                        from rag.retriever import _df
                        if _df is not None and "date" in _df.columns:
                            parquet_max = pd.to_datetime(_df["date"]).dt.year.max()
                            if parquet_max:
                                current_max_year = int(parquet_max)
                    except Exception:
                        pass

                if max_year > current_max_year:
                    yield f"data: {json.dumps({'type': 'meta', 'chart_type': 'none', 'sql_used': sql, 'float_ids': [], 'data': [], 'source_files': [], 'pipeline_trace': pipeline_trace, 'validation_warnings': validation_warnings})}\n\n"
                    yield f"data: {json.dumps({'type': 'chunk', 'text': f'The requested date ({max_year}) is in the future. The ARGO dataset contains historical measurements and does not support future predictions.'})}\n\n"
                    yield "data: {\"type\": \"done\"}\n\n"
                    return

            if coords and not rows.empty and "distance_km" in rows.columns:
                closest_dist = rows.iloc[0]["distance_km"]
                if closest_dist > 500.0:
                    lat_q, lon_q = coords
                    lat_q_str = f"{abs(lat_q)}N" if lat_q >= 0 else f"{abs(lat_q)}S"
                    lon_q_str = f"{abs(lon_q)}E" if lon_q >= 0 else f"{abs(lon_q)}W"
                    closest_lat = rows.iloc[0]["latitude"]
                    closest_lon = rows.iloc[0]["longitude"]
                    closest_lat_str = f"{closest_lat:.2f}"
                    closest_lon_str = f"{closest_lon:.2f}"
                    warning = (
                        f"No ARGO float data found within 500km of ({lat_q_str}, {lon_q_str}). "
                        f"Closest available record is {closest_dist:,.0f}km away at ({closest_lat_str}, {closest_lon_str})."
                    )
                    yield f"data: {json.dumps({'type': 'meta', 'chart_type': 'none', 'sql_used': sql, 'float_ids': [], 'data': [], 'source_files': [], 'pipeline_trace': pipeline_trace, 'validation_warnings': validation_warnings})}\n\n"
                    yield f"data: {json.dumps({'type': 'chunk', 'text': warning})}\n\n"
                    yield "data: {\"type\": \"done\"}\n\n"
                    return

            _q = req.message.lower()
            _impossible_patterns = [
                (r'(?:temperature|temp|salinity|depth|pressure)\w*[^.!?]*?(?:above|greater than|more than|over|>)\s*(\d+(?:\.\d+)?)\s*(?:°c|c|psu|m|dbar)?[^.!?]*?and[^.!?]*?(?:below|less than|under|<)\s*(\d+(?:\.\d+)?)', True),
                (r'(?:temperature|temp|salinity|depth|pressure)\w*[^.!?]*?(?:below|less than|under|<)\s*(\d+(?:\.\d+)?)\s*(?:°c|c|psu|m|dbar)?[^.!?]*?and[^.!?]*?(?:above|greater than|more than|over|>)\s*(\d+(?:\.\d+)?)', False),
            ]
            is_contradiction_found = False
            for pattern, first_is_high in _impossible_patterns:
                m = re.search(pattern, _q)
                if m:
                    a, b = float(m.group(1)), float(m.group(2))
                    is_contradiction = (a > b) if first_is_high else (b > a)
                    if is_contradiction:
                        is_contradiction_found = True
                        break

            if is_contradiction_found:
                yield f"data: {json.dumps({'type': 'meta', 'chart_type': 'none', 'sql_used': sql, 'float_ids': [], 'data': [], 'source_files': [], 'pipeline_trace': pipeline_trace, 'validation_warnings': validation_warnings})}\n\n"
                yield f"data: {json.dumps({'type': 'chunk', 'text': 'No records match these constraints \u2014 the conditions given cannot be satisfied simultaneously.'})}\n\n"
                yield "data: {\"type\": \"done\"}\n\n"
                return

            if rows.empty:
                chart_type = "none"
                float_ids = []
                serialized_data = []
                source_files = []
            else:
                is_aggregate = "float_id" not in rows.columns or rows["float_id"].isna().all()
                if is_aggregate:
                    chart_type = "none"

                if chart_type == "comparison" and not rows.empty and "float_id" in rows.columns:
                    unique_fids = rows["float_id"].dropna().unique()
                    if len(unique_fids) <= 1:
                        chart_type = "profile"
                float_ids = [str(fid) for fid in rows["float_id"].dropna().unique().tolist() if fid is not None and not pd.isna(fid)] if "float_id" in rows.columns else []
                serialized_data = serialize_df(rows)
                if not float_ids and should_retrieve:
                    method = rows.attrs.get("retrieval_method", "")
                    if "PostgreSQL" in method:
                        source_files = ["PostgreSQL Relational Database Table (argo_profiles)"]
                    else:
                        source_files = ["Local Dataset (argo.parquet via FAISS index)"]
                else:
                    source_files = [f"{fid}_prof.nc" for fid in float_ids]

            pipeline_trace.append("Summarizer: Streaming tokens from Groq LLM...")
            
            yield f"data: {json.dumps({'type': 'meta', 'chart_type': chart_type, 'sql_used': sql, 'float_ids': float_ids, 'data': serialized_data, 'source_files': source_files, 'pipeline_trace': pipeline_trace, 'validation_warnings': validation_warnings})}\n\n"

            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
            model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
            history = None
            if req.history:
                history = [{"role": h.get("role", ""), "text": h.get("text") or h.get("content", "")} for h in req.history]

            from llm.prompts import build_prompt
            system_prompt, user_content, history_messages = build_prompt(
                req.message, rows, history=history
            )

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history_messages)
            messages.append({"role": "user", "content": user_content})

            models_to_try = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.2-3b-preview", "gemma2-9b-it"]
            user_model = os.getenv("LLM_MODEL")
            if user_model and user_model in models_to_try:
                models_to_try.remove(user_model)
                models_to_try.insert(0, user_model)

            response = None
            for current_model in models_to_try:
                try:
                    response = client.chat.completions.create(
                        model=current_model,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1024,
                        timeout=30.0,
                        stream=True
                    )
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if "rate_limit" in err_str or "429" in err_str or "limit reached" in err_str:
                        print(f"[DEBUG] Streaming model {current_model} rate limited: {e}. Trying fallback model...", flush=True)
                        time.sleep(1.0)
                        continue
                    raise e

            if response:
                for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield f"data: {json.dumps({'type': 'chunk', 'text': delta})}\n\n"

            yield "data: {\"type\": \"done\"}\n\n"
        except Exception as e:
            print(f"Streaming error: {e}", flush=True)
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
            yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
