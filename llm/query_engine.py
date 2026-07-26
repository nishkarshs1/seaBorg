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

def has_ocean_intent(question: str) -> bool:
    msg = question.lower()
    
    # 1. Check for float ID (regex)
    import re
    if re.search(r'(?:[A-Z][0-9]{7}|[0-9]{7})', msg):
        return True
        
    # 2. Check for coordinates
    if extract_coordinates(question):
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


def is_conversational_only(question: str) -> bool:
    msg = question.lower().strip().strip("!?.,")
    
    # Casual greetings and polite responses
    greetings = {
        "hello", "hi", "hey", "greetings", "good morning", "good afternoon", 
        "good evening", "thanks", "thank you", "ok", "okay", "cool", 
        "who are you", "what is your name", "what can you do", "help", 
        "clear", "bye", "goodbye", "exit"
    }
    
    if msg in greetings:
        return True
        
    # Check if the query is very short and has no oceanographic terms
    if len(msg.split()) <= 3 and not has_ocean_intent(question):
        return True
        
    return False


def answer_query(question: str, context_rows: pd.DataFrame, history_tuple: tuple | None = None, ocean: str | None = None) -> dict:
    import re
    
    # Fast Conversational Bypass: Skip SQL generation & database check for greetings
    if is_conversational_only(question):
        sql = "-- Conversational query (no database lookup required)"
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
        model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        history = []
        if history_tuple:
            for h in history_tuple:
                role = "user" if h[0] == "user" else "assistant"
                content = h[1]
                if content.strip():
                    history.append({"role": role, "content": content})
        
        system_prompt = (
            "You are SeaBorg, an intelligent AI assistant specialized in oceanography and ARGO float data. "
            "Acknowledge greetings and casual questions warmly and concisely. Introduce your capabilities briefly "
            "if asked. Do not try to reference databases or tables for casual chat."
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                timeout=10.0,
            )
            answer = response.choices[0].message.content.strip()
            return {
                "status": "ok",
                "refusal_type": None,
                "answer": answer,
                "sql": sql
            }
        except Exception as e:
            return {
                "status": "refused",
                "refusal_type": "llm_error",
                "answer": f"Greetings! I had an issue connecting to my LLM engine: {e}",
                "sql": sql
            }

    try:
        sql = generate_sql(question, ocean)
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
        question, context_rows if context_rows is not None else pd.DataFrame(), history=history, sql=sql
    )

    # Build proper messages array: system → history turns → current user message
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": user_content})
    
    models_to_try = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama-3.2-3b-preview", "gemma2-9b-it"]
    user_model = os.getenv("LLM_MODEL")
    if user_model and user_model in models_to_try:
        models_to_try.remove(user_model)
        models_to_try.insert(0, user_model)

    import time
    import re
    answer = None
    
    for current_model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=current_model,
                messages=messages,
                temperature=0.1,
                max_tokens=1024,
                timeout=30.0,
            )
            answer = response.choices[0].message.content.strip()
            break
        except Exception as e:
            err_str = str(e).lower()
            if "rate_limit" in err_str or "429" in err_str or "limit reached" in err_str:
                print(f"[DEBUG] Model {current_model} rate limited: {e}. Trying fallback model...", flush=True)
                time.sleep(1.0)
                continue
            raise e

    if answer is None:
        answer = "I'm experiencing high traffic right now. Please try your request again in a few moments."
    
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