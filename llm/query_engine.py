import os

import pandas as pd
from dotenv import load_dotenv
from groq import Groq

from .prompts import build_prompt
from .nl_to_sql import generate_sql

load_dotenv()

from rag.retriever import extract_coordinates

REFUSAL_MESSAGE = (
    "This variable is not available in the ARGO dataset. "
    "Available fields: temperature, salinity, pressure, depth, "
    "latitude, longitude, date."
)

def answer_query(question: str, context_rows: pd.DataFrame, history_tuple: tuple | None = None) -> dict:
    import re
    try:
        sql = generate_sql(question)
    except Exception:
        sql = "-- SQL generation failed"

    # 1. Coordinate bounds check (Latitude -90 to 90, Longitude -180 to 180)
    coords = extract_coordinates(question)
    if coords:
        lat, lon = coords
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return {
                "status": "refused",
                "refusal_type": "invalid_coordinates",
                "answer": "Invalid coordinates: Latitude must be between -90 and 90, and Longitude must be between -180 and 180.",
                "sql": sql
            }

    # 2. Future date check
    cleaned_q = re.sub(r'\b(?:float|id|no\.?|number)\s+\d+\b', '', question.lower())
    found_years = []
    for m in re.finditer(r'\b(20\d{2})[-/]\d{2}(?:[-/]\d{2})?\b', cleaned_q):
        found_years.append(int(m.group(1)))
    for m in re.finditer(r'\b(?:in|on|for|during|before|after|to|at|since|until|date|year)\s+(20\d{2})\b', cleaned_q):
        found_years.append(int(m.group(1)))
        
    if found_years:
        max_year = max(found_years)
        
        # Get dynamic max year cutoff from dataset
        current_max_year = 2026
        try:
            from db.connection import get_engine
            from sqlalchemy import text
            engine = get_engine()
            with engine.connect() as conn:
                res = conn.execute(text("SELECT MAX(EXTRACT(YEAR FROM date)) FROM argo_profiles")).scalar()
                if res:
                    current_max_year = int(res)
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
            return {
                "status": "refused",
                "refusal_type": "future_date",
                "answer": f"The requested date ({max_year}) is in the future. The ARGO dataset contains historical measurements and does not support future predictions.",
                "sql": sql
            }

    # Check for distance threshold refusal (exceeding 500km)
    if coords and context_rows is not None and not context_rows.empty and "distance_km" in context_rows.columns:
        closest_dist = context_rows.iloc[0]["distance_km"]
        if closest_dist > 500.0:
            lat_q, lon_q = coords
            lat_q_str = f"{abs(lat_q)}N" if lat_q >= 0 else f"{abs(lat_q)}S"
            lon_q_str = f"{abs(lon_q)}E" if lon_q >= 0 else f"{abs(lon_q)}W"
            closest_lat = context_rows.iloc[0]["latitude"]
            closest_lon = context_rows.iloc[0]["longitude"]
            closest_lat_str = f"{closest_lat:.2f}"
            closest_lon_str = f"{closest_lon:.2f}"
            warning = (
                f"No ARGO float data found within 500km of ({lat_q_str}, {lon_q_str}). "
                f"Closest available record is {closest_dist:,.0f}km away at ({closest_lat_str}, {closest_lon_str})."
            )
            return {
                "status": "refused",
                "refusal_type": "distance_guard_exceeded",
                "answer": warning,
                "sql": sql
            }

    # 4. Deterministic impossible-constraints check
    # Only fires when the user asks for the SAME variable to be simultaneously ABOVE X and BELOW Y
    # where X > Y — a logical impossibility. Not triggered by normal range/depth/average queries.
    _q = question.lower()
    _impossible_patterns = [
        # "above/greater than X AND below/less than Y" for temp/salinity/depth/pressure
        # Allows filler words between variable and comparator (e.g. "temperature is above")
        (r'(?:temperature|temp|salinity|depth|pressure)\w*[^.!?]*?(?:above|greater than|more than|over|>)\s*(\d+(?:\.\d+)?)\s*(?:°c|c|psu|m|dbar)?[^.!?]*?and[^.!?]*?(?:below|less than|under|<)\s*(\d+(?:\.\d+)?)', True),
        # "below X AND above Y" reversed
        (r'(?:temperature|temp|salinity|depth|pressure)\w*[^.!?]*?(?:below|less than|under|<)\s*(\d+(?:\.\d+)?)\s*(?:°c|c|psu|m|dbar)?[^.!?]*?and[^.!?]*?(?:above|greater than|more than|over|>)\s*(\d+(?:\.\d+)?)', False),
    ]
    for pattern, first_is_high in _impossible_patterns:
        m = re.search(pattern, _q)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            # Check if the two bounds are logically contradictory
            is_contradiction = (a > b) if first_is_high else (b > a)
            if is_contradiction:
                return {
                    "status": "refused",
                    "refusal_type": "impossible_constraints",
                    "answer": "No records match these constraints \u2014 the conditions given cannot be satisfied simultaneously.",
                    "sql": sql
                }

    client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    history = None
    if history_tuple:
        history = [{"role": h[0], "text": h[1]} for h in history_tuple]
    system_prompt, user_content, history_messages = build_prompt(
        question, context_rows if context_rows is not None else pd.DataFrame(), history=history
    )

    # Build proper messages array: system → history turns → current user message
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_content})
    
    import time
    import re
    for attempt in range(15):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                timeout=30.0,
            )
            answer = response.choices[0].message.content.strip()
            break
        except Exception as e:
            if attempt < 14 and ("rate_limit" in str(e).lower() or "429" in str(e) or "limit reached" in str(e).lower()):
                wait_time = 2.0 + (attempt * 1.5)
                match = re.search(r'try again in (\d+(?:\.\d+)?)s', str(e).lower())
                if match:
                    wait_time = float(match.group(1)) + 0.5
                print(f"[DEBUG] Rate limited. Sleeping for {wait_time:.2f}s...", flush=True)
                time.sleep(wait_time)
                continue
            raise e
    
    is_refusal = (
        "not available in the ARGO dataset" in answer.lower() or
        "not available in the database" in answer.lower() or
        "No ARGO float data found" in answer or
        "Invalid coordinates" in answer or
        "in the future" in answer or
        "cannot be satisfied simultaneously" in answer or
        "No ARGO float data exists" in answer or
        "outside the scope of ARGO" in answer.lower()
    )
    if is_refusal:
        refusal_type = "unknown_refusal"
        if "cannot be satisfied simultaneously" in answer:
            refusal_type = "impossible_constraints"
        elif "No ARGO float data exists" in answer:
            refusal_type = "no_region_data"
        elif "outside the scope" in answer.lower():
            refusal_type = "off_topic"
        elif "not available in the ARGO dataset" in answer.lower():
            refusal_type = "out_of_domain_variable"
            
        return {
            "status": "refused",
            "refusal_type": refusal_type,
            "answer": answer,
            "sql": sql
        }
        
    return {
        "status": "ok",
        "refusal_type": None,
        "answer": answer,
        "sql": sql
    }