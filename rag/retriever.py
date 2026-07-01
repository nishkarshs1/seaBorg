import os
import math
import re

SIMILARITY_THRESHOLD = 0.45

def extract_coordinates(query: str) -> tuple[float, float] | None:
    lat_pat = r'(-?\d+(?:\.\d+)?)\s*([NSns])'
    lon_pat = r'(-?\d+(?:\.\d+)?)\s*([EWewOo])'
    
    lat_m = re.search(lat_pat, query)
    lon_m = re.search(lon_pat, query)
    
    if lat_m and lon_m:
        lat_val = float(lat_m.group(1))
        if lat_m.group(2).upper() == 'S':
            lat_val = -lat_val
        lon_val = float(lon_m.group(1))
        if lon_m.group(2).upper() == 'W':
            lon_val = -lon_val
        return lat_val, lon_val
    
    lat_label = re.search(r'lat(?:itude)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)', query, re.IGNORECASE)
    lon_label = re.search(r'lon(?:gitude)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)', query, re.IGNORECASE)
    if lat_label and lon_label:
        return float(lat_label.group(1)), float(lon_label.group(1))
        
    return None

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


import faiss
import pandas as pd
from dotenv import load_dotenv

from .embedder import embed_query


_index = None
_df = None

_ARGO_SCHEMA_COLUMNS = [
    "id",
    "float_id",
    "date",
    "latitude",
    "longitude",
    "depth_m",
    "temp_c",
    "salinity",
    "oxygen",
    "created_at",
]


def _ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensures returned DataFrame matches argo_profiles column schema/order."""
    out = df.copy()
    for col in _ARGO_SCHEMA_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    cols = _ARGO_SCHEMA_COLUMNS + ["distance_km"] if "distance_km" in out.columns else _ARGO_SCHEMA_COLUMNS
    return out[cols]


def load_index() -> None:
    """
    Loads FAISS index and parquet DataFrame once into module-level state.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Reads files from paths configured in environment variables.
    """
    global _index, _df
    if _index is not None and _df is not None:
        return

    load_dotenv()
    faiss_index_path = os.getenv("FAISS_INDEX_PATH")
    parquet_path = os.getenv("PARQUET_PATH")

    if not faiss_index_path:
        raise ValueError("FAISS_INDEX_PATH is not set.")
    if not parquet_path:
        raise ValueError("PARQUET_PATH is not set.")

    try:
        _index = faiss.read_index(faiss_index_path)
        _df = pd.read_parquet(parquet_path).reset_index(drop=True)
    except Exception as e:
        print(f"WARNING: Could not load FAISS or Parquet files. They may not be deployed yet. Error: {e}")
        _index = None
        _df = None


import re
from sqlalchemy import text
from llm.geo_mapping import map_region_to_coordinates

def retrieve(user_query: str, top_k: int = 5, ocean: str | None = None, chart_type: str = "none") -> pd.DataFrame:
    """
    Retrieves top-k nearest rows using a hybrid approach.
    1. Checks for float ID (regex). If found, queries DB directly.
    2. Otherwise, falls back to FAISS semantic search with optional ocean coordinate bounds.

    Args:
        user_query: Natural language user query.
        top_k: Number of rows to return.
        ocean: Optional ocean filter string.

    Returns:
        DataFrame of retrieved rows with argo_profiles schema columns.
    """
    if _index is None or _df is None:
        raise RuntimeError("Index not loaded. Call load_index() before retrieve().")

    bounds = None
    if ocean and ocean.lower() != "all oceans":
        bounds = map_region_to_coordinates(ocean)
    else:
        # Detect named region in the query if no explicit ocean filter is selected
        from llm.geo_mapping import detect_region
        region_name, query_bounds = detect_region(user_query)
        if query_bounds:
            bounds = query_bounds

    # 1. Check for float ID pattern or region bounds
    float_ids = [fid.upper() for fid in re.findall(r'(?:[A-Z][0-9]{7}|[0-9]{7})', user_query, re.IGNORECASE)]
    if float_ids or bounds:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            from db.connection import get_engine
            engine = get_engine()
            
            if float_ids:
                if bounds:
                    subqueries = []
                    for i in range(len(float_ids)):
                        subqueries.append(f"""
                            SELECT * FROM argo_profiles
                            WHERE float_id = :fid_{i}
                              AND latitude >= :lat_min AND latitude <= :lat_max
                              AND longitude >= :lon_min AND longitude <= :lon_max
                            ORDER BY date DESC LIMIT :limit
                        """)
                    sql = " UNION ALL ".join(f"SELECT * FROM ({sq}) AS sub_{i}" for i, sq in enumerate(subqueries))
                    params = {
                        "limit": top_k,
                        "lat_min": bounds["lat_min"],
                        "lat_max": bounds["lat_max"],
                        "lon_min": bounds["lon_min"],
                        "lon_max": bounds["lon_max"],
                    }
                    for i, fid in enumerate(float_ids):
                        params[f"fid_{i}"] = fid
                else:
                    subqueries = []
                    for i in range(len(float_ids)):
                        subqueries.append(f"""
                            SELECT * FROM argo_profiles
                            WHERE float_id = :fid_{i}
                            ORDER BY date DESC LIMIT :limit
                        """)
                    sql = " UNION ALL ".join(f"SELECT * FROM ({sq}) AS sub_{i}" for i, sq in enumerate(subqueries))
                    params = {"limit": top_k}
                    for i, fid in enumerate(float_ids):
                        params[f"fid_{i}"] = fid
            else:
                # Query by region bounds only
                sql = """
                    SELECT * FROM argo_profiles
                    WHERE latitude >= :lat_min AND latitude <= :lat_max
                      AND longitude >= :lon_min AND longitude <= :lon_max
                    ORDER BY date DESC LIMIT :limit
                """
                params = {
                    "limit": top_k,
                    "lat_min": bounds["lat_min"],
                    "lat_max": bounds["lat_max"],
                    "lon_min": bounds["lon_min"],
                    "lon_max": bounds["lon_max"],
                }

            coords = extract_coordinates(user_query)

            with engine.connect() as conn:
                rows = pd.read_sql(text(sql), conn, params=params)
            if not rows.empty:
                if coords:
                    lat_q, lon_q = coords
                    distances_km = []
                    for _, r in rows.iterrows():
                        distances_km.append(haversine_distance(lat_q, lon_q, r["latitude"], r["longitude"]))
                    rows["distance_km"] = distances_km
                return _ensure_schema(rows)

    # 3. Fallback to FAISS (with optional coordinates post-filtering)
    coords = extract_coordinates(user_query)
    effective_threshold = 0.0 if (coords or bounds) else 0.30
    
    query_vec = embed_query(user_query).astype("float32")
    
    # Increase search depth for spatial sorting or year/bounds post-filtering
    year_match = re.search(r'\b(20\d{2})\b', user_query)
    search_k = min(200 if coords else (len(_df) if (bounds or year_match) else top_k), len(_df))
    distances, indices = _index.search(query_vec, search_k)
    similarities = 1.0 - (distances[0] / 2.0)
    
    print(f"[DEBUG] Top-5 similarities: {similarities[:5].tolist()}", flush=True)
    
    valid_mask = similarities >= effective_threshold
    valid_indices = indices[0][valid_mask]
    if len(valid_indices) == 0:
        return _ensure_schema(pd.DataFrame())
        
    candidate_rows = _df.iloc[valid_indices].copy()
    
    # Post-filter by year if specified in query
    year_match = re.search(r'\b(20\d{2})\b', user_query)
    if year_match:
        target_year = year_match.group(1)
        year_mask = candidate_rows["date"].astype(str).str.startswith(target_year)
        if year_mask.any():
            candidate_rows = candidate_rows[year_mask]
            
    k_limit = top_k
    if coords:
        lat_q, lon_q = coords
        distances_km = []
        for _, r in candidate_rows.iterrows():
            distances_km.append(haversine_distance(lat_q, lon_q, r["latitude"], r["longitude"]))
        candidate_rows["distance_km"] = distances_km
        # Sort by actual Haversine distance
        candidate_rows = candidate_rows.sort_values("distance_km")
        
        # Apply the 500km distance guard directly to candidate rows (if closest is within 500km)
        if not candidate_rows.empty and candidate_rows.iloc[0]["distance_km"] <= 500.0:
            candidate_rows = candidate_rows[candidate_rows["distance_km"] <= 500.0]
        
        # Set limit based on chart_type rather than query string keyword checking
        if chart_type != "none":
            k_limit = top_k
        else:
            k_limit = 1

    if bounds:
        filtered = candidate_rows[
            (candidate_rows["latitude"] >= bounds["lat_min"]) &
            (candidate_rows["latitude"] <= bounds["lat_max"]) &
            (candidate_rows["longitude"] >= bounds["lon_min"]) &
            (candidate_rows["longitude"] <= bounds["lon_max"])
        ]
        rows = filtered.head(k_limit).reset_index(drop=True)
    else:
        rows = candidate_rows.head(k_limit).reset_index(drop=True)

    return _ensure_schema(rows)
