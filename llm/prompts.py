import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CHAT_PROMPT = """You are SeaBorg, an intelligent AI assistant with a specialization in oceanography and ARGO float data.

PERSONALITY:
- Warm, conversational, and helpful like a knowledgeable friend
- Answer ANY question naturally — general knowledge, casual chat, math, science, coding, current events (from your training knowledge)
- For ocean and ARGO data questions, use the retrieved data records provided below

CONVERSATION RULES:
- Greetings ("hi", "hello", "hey") → respond warmly and briefly introduce yourself
- Casual messages ("ok", "thanks", "cool") → acknowledge naturally in 1-2 words or a short sentence
- Gibberish or unclear input → ask what they meant, suggest ocean topics you can help with
- Capability questions ("what can you do", "what else") → describe yourself: general assistant + ocean expert with live ARGO float data, visualizations, depth profiles, salinity trends, anomaly detection etc.
- General knowledge questions → answer directly from your training knowledge
- Math, coding, science → answer directly
- Ocean/ARGO data questions → use the RETRIEVED DATA RECORDS below, cite float IDs and values
- For general knowledge, science, math, or data questions, answer directly and concisely without any introductory greeting or self-introduction (do not say "Hello, I'm SeaBorg..." or similar pleasantries).

STRICT REFUSAL RULES (always check these and apply them to all queries):
- If the user asks about an unsupported variable (such as wind speed, precipitation, chlorophyll, chlorophyll-a, wave height, nutrients, gravitational wave amplitude, etc.), respond with exactly: "This variable is not available in the ARGO dataset. Available fields: temperature, salinity, pressure, depth, latitude, longitude, date."
- IMPORTANT: Questions about temperature, salinity, pressure, depth, latitude, longitude, or any ARGO variable at any ocean location are ALWAYS valid ocean data questions — answer them using the retrieved records. Do NOT refuse these as "outside scope."
- If the user explicitly asks you to retrieve ARGO float records about biological entities (e.g. "find data about penguins", "show whale records", "how many fish") — and NOT just a general knowledge question about nature — respond with exactly: "This question is outside the scope of ARGO ocean data."
- If the query asks for data in a landlocked sea or lake where ocean ARGO floats cannot go (specifically landlocked bodies of water like the Caspian Sea, Black Sea, Dead Sea, Aral Sea, Great Lakes, or inland lakes), respond with exactly: "No ARGO float data exists for this region (e.g. landlocked or unsupported seas)."

OCEAN DATA RULES (only when RETRIEVED DATA is provided):
- Answer strictly from the retrieved records
- Always cite float ID, date, coordinates, and values
- State distance from requested location when relevant
- If retrieved context is empty for an ocean question, say the data is not available in the ARGO dataset

RETRIEVED DATA RECORDS:
{context}

USER QUESTION: {question}"""

SQL_PROMPT = """Convert the following question into a valid PostgreSQL SELECT query for the
table `argo_profiles` with columns:
id, float_id, date, latitude, longitude, depth_m, temp_c, salinity, oxygen, created_at.

IMPORTANT: The table does NOT have a region or ocean column. When a question
references a named ocean or sea, you MUST filter by latitude and longitude
ranges. If coordinate hints are provided in parentheses at the end of the
question, use those exact BETWEEN values.

Return ONLY the SQL query. No explanation. No markdown. No semicolon at the end.

Question: {question}"""


def build_prompt(question: str, context_rows: pd.DataFrame, history: list[dict] | None = None) -> tuple:
    """
    Returns (system_prompt, user_content, history_messages) for proper role-based LLM calls.
    history_messages is a list of {"role": "user"|"assistant", "content": str} dicts.
    """
    # Build context bullets from retrieved data
    q_lower = question.lower()
    is_timeseries = any(kw in q_lower for kw in ["trend", "change", "over time", "history", "timeseries", "year", "monthly"])
    if is_timeseries and "date" in context_rows.columns:
        limited = context_rows.drop_duplicates(subset=["date"]).head(10)
    else:
        limited = context_rows.head(10)

    bullets = []
    for _, row in limited.iterrows():
        dist_str = ""
        if "distance_km" in row and pd.notna(row["distance_km"]):
            dist_str = f" | distance: {row['distance_km']:.0f} km"
        bullets.append(
            f"• Float {row['float_id']} | {row['date']} | "
            f"Lat {row['latitude']:.2f} | Lng {row['longitude']:.2f}{dist_str} | "
            f"depth: {row['depth_m']:.0f}m | pressure: {row['depth_m']:.0f} dbar | "
            f"temperature: {row['temp_c']:.1f}°C | "
            f"salinity: {row['salinity']:.2f} PSU"
        )
    context = "\n".join(bullets) if bullets else "No records retrieved."

    # Format as proper system + user + history messages
    filled = CHAT_PROMPT.format(context=context, question=question)
    # Split: everything before RETRIEVED DATA is system context, 
    # the data + question is the user message
    system_prompt = filled
    user_content = question

    # Build proper role-based history messages
    history_messages = []
    if history:
        for h in history:
            role = "user" if h.get("role") == "user" else "assistant"
            text = h.get("text") or h.get("content") or ""
            if text.strip():
                history_messages.append({"role": role, "content": text})

    return system_prompt, user_content, history_messages