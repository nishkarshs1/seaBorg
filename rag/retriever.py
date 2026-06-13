import os

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
    return out[_ARGO_SCHEMA_COLUMNS]


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

    _index = faiss.read_index(faiss_index_path)
    _df = pd.read_parquet(parquet_path).reset_index(drop=True)


import re
from sqlalchemy import text

def retrieve(user_query: str, top_k: int = 5) -> pd.DataFrame:
    """
    Retrieves top-k nearest rows using a hybrid approach.
    1. Checks for float ID (regex). If found, queries DB directly.
    2. Otherwise, falls back to FAISS semantic search.

    Args:
        user_query: Natural language user query.
        top_k: Number of rows to return.

    Returns:
        DataFrame of retrieved rows with argo_profiles schema columns.

    Side effects:
        May query PostgreSQL if a float ID is detected.
    """
    if _index is None or _df is None:
        raise RuntimeError("Index not loaded. Call load_index() before retrieve().")


    # 1. Check for float ID pattern
    match = re.search(r'(?:[A-Z][0-9]{7}|[0-9]{7})', user_query, re.IGNORECASE)
    if match:
        float_id = match.group(0).upper()
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            from db.connection import get_engine
            engine = get_engine()
            sql = "SELECT * FROM argo_profiles WHERE float_id = :fid ORDER BY date DESC LIMIT :limit"
            with engine.connect() as conn:
                rows = pd.read_sql(text(sql), conn, params={"fid": float_id, "limit": top_k})
            if not rows.empty:
                return _ensure_schema(rows)

    # 3. Fallback to FAISS
    query_vec = embed_query(user_query).astype("float32")
    search_k = min(top_k, len(_df))
    _, indices = _index.search(query_vec, search_k)
    rows = _df.iloc[indices[0]].reset_index(drop=True)
    return _ensure_schema(rows)
