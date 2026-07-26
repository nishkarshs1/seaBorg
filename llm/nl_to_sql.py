import os

import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from sqlalchemy.engine import Engine
from sqlalchemy import text

from .prompts import SQL_PROMPT
from .geo_mapping import detect_region

load_dotenv()

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "GRANT"
]


def _preprocess_question(question: str, ocean: str | None = None) -> str:
    """
    Detect a geographic region in the question and append coordinate
    context so the LLM can generate correct lat/lon WHERE clauses.
    If the question doesn't have a region but an ocean filter is active,
    appends that ocean's bounds as context.
    """
    region_name, bounds = detect_region(question)
    
    if bounds is None and ocean and ocean.lower() != "all oceans":
        from llm.geo_mapping import map_region_to_coordinates
        bounds = map_region_to_coordinates(ocean)
        region_name = ocean

    if bounds is None:
        return question
        
    hint = (
        f" (Note: '{region_name}' corresponds to latitude BETWEEN "
        f"{bounds['lat_min']} AND {bounds['lat_max']} and longitude "
        f"BETWEEN {bounds['lon_min']} AND {bounds['lon_max']})"
    )
    return question + hint


def generate_sql(question: str, ocean: str | None = None) -> str:
    """
    Sends SQL_PROMPT to the LLM and returns a raw SQL string.

    If the question mentions a known ocean or sea, or if an ocean parameter
    is provided, coordinate context is injected automatically.

    Args:
        question: The user's natural language question.
        ocean: Optional ocean filter string.

    Returns:
        A raw SQL string from the LLM. May be unsafe - always validate
        with safe_sql_query() before executing.

    Side effects:
        Makes a Groq API call.
    """
    enriched = _preprocess_question(question, ocean)
    client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": SQL_PROMPT.format(question=enriched),
            }
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def safe_sql_query(
    sql: str, engine: Engine
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Validates sql against forbidden keywords and executes if safe.

    Args:
        sql: SQL string to validate and execute.
        engine: SQLAlchemy engine connected to the seaborg database.

    Returns:
        (DataFrame, None) if the query is safe and executes successfully.
        (None, error_message) if the query contains forbidden keywords or fails.

    Side effects:
        Executes a SELECT query against PostgreSQL if safe.
    """
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            return None, "Unsafe SQL rejected"

    try:
        with engine.connect() as conn:
            result = pd.read_sql(text(sql), conn)
        return result, None
    except Exception as exc:
        return None, f"SQL execution error: {str(exc)}"