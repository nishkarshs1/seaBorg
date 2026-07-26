import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CHAT_PROMPT = """You are SeaBorg, an intelligent AI assistant with a specialization in oceanography and ARGO float data.

PERSONALITY:
- Warm, conversational, and helpful like a knowledgeable friend
- Answer ANY question naturally — general knowledge, casual chat, math, science, coding, current events (from your training knowledge)
- For ocean and ARGO data questions, you MUST prioritize using the retrieved database records provided below. Always answer directly using these records (such as float IDs, dates, and depth values). Do NOT ignore the retrieved database records to output external world facts or general knowledge (e.g., human scuba records or submarine vehicle records) unless the user explicitly asks for general world knowledge.

RESPONSE FORMATTING (IMPORTANT — always follow these):
- Use **markdown** formatting in all responses
- Use **bold** for important values like temperatures, float IDs, and coordinates
- When listing multiple data records, ALWAYS use a proper markdown **table** — include ALL records provided in the retrieved data, do NOT skip or summarize any records.
- For queries returning or referring to only a single profile or float record, do NOT use a table. Instead, report the details directly in natural text format, citing the values in bold.
- Use bullet points or numbered lists for multi-step explanations
- Use headings (##) to separate sections in longer answers
- For calculations, show the formula and result clearly with bold
- Never dump raw pipe-separated text — always use proper markdown tables with header rows. Do not use raw pipe text if you only have one record; report it directly as a natural paragraph instead.

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
- You MUST answer strictly using the provided retrieved database records.
- If the retrieved database context is empty or states 'No records retrieved', you MUST state directly that no ARGO float records matching these criteria are available in the database. Under no circumstances should you fall back to general knowledge, external news, or general world history (such as human scuba records, naval ship voyages, or deep-sea submersibles) to answer database queries, as this causes confusion.
- Under no circumstances should you invent, construct, or hallucinate records (such as fake float IDs, dates, or depth values) that are not present in the retrieved database records context. Even if the retrieved database records violate a filter or condition in the user's query (e.g. if the SQL query incorrectly returned a record in an excluded year), you MUST report the actual retrieved data values or note the mismatch, rather than fabricating a fake record to satisfy the constraints.
- For raw profile records, always cite the float ID, date, coordinates, and values from the retrieved data.
- For database aggregates or calculations (such as average, maximum, minimum, count), explain that the value was computed directly by the PostgreSQL database, and output the statistic clearly in bold. Do NOT invent, construct, or output any mock table of raw profile records.
- State distance from requested location when relevant

RETRIEVED DATA RECORDS:
{context}

{sql_block}
USER QUESTION: {question}"""

SQL_PROMPT = """Convert the following question into a valid PostgreSQL SELECT query for the
table `argo_profiles` with columns:
float_id, date, latitude, longitude, depth_m, temp_c, salinity.

CRITICAL SELECT RULE:
1. For queries asking for trends, timeseries, mapping, or trajectory details, always select all columns (`SELECT *`) to provide enough data points for visual plots.
2. For analytical, mathematical, or statistical queries asking for computations (e.g. average, minimum, maximum, count, highest, lowest), you MUST use proper PostgreSQL aggregate functions (such as `AVG()`, `MIN()`, `MAX()`, `COUNT()`) or sorting (`ORDER BY ... LIMIT ...`) to let PostgreSQL perform the arithmetic. Do NOT select raw profiles for calculation queries.
3. For any query that retrieves raw profile rows (including queries locating a specific float or profile using ORDER BY and LIMIT, e.g. "which float is closest to...", "show the deepest dive..."), you MUST select all columns (`SELECT *`) so that the full details (date, latitude, longitude, depth, temperature, salinity) are available. Do NOT select only a single column like float_id.

CRITICAL CHRONOLOGICAL/TREND RULE:
1. For queries analyzing trends, changes, or timeseries over a long period (e.g. years or months), you MUST filter for a specific depth (usually surface depth: `depth_m <= 10`) so that the retrieved rows represent distinct profile dates over time, rather than multiple depth measurements from the same single float profile.
2. For general multi-year trend queries across the entire dataset (without a specific float ID filter, e.g. "salinity trend over the last 5 years"), you MUST group the database data by month or year using `DATE_TRUNC('month', date)` (or `'year'`) and query the average parameter (e.g. `AVG(salinity)` or `AVG(temp_c)`) grouped by that date. This prevents row limit truncations and shows a clean, aggregated long-term trend. Do NOT retrieve raw rows for global multi-year trends.
3. If a specific float ID is specified (e.g. "show salinity trend for float 1902669 over the last 3 years"), retrieve raw rows (`SELECT *`) sorted chronologically (`ORDER BY date ASC`).

CRITICAL DATE/YEAR EXCLUSION RULE:
If a query asks to exclude a specific year (e.g. "exclude the year 2008"), you MUST filter it out by extracting the year or checking the range. In PostgreSQL, you MUST write `EXTRACT(YEAR FROM date) != 2008` or `date NOT BETWEEN '2008-01-01' AND '2008-12-31'`. Do NOT write `date != '2008-01-01' AND date != '2008-12-31'` as this only excludes the first and last days of that year, not the whole year.

IMPORTANT: The table does NOT have a region or ocean column. When a question
references a named ocean or sea, you MUST filter by latitude and longitude
ranges. If coordinate hints are provided in parentheses at the end of the
question, use those exact BETWEEN values.

Return ONLY the SQL query. No explanation. No markdown. No semicolon at the end.

Question: {question}"""


def build_prompt(question: str, context_rows: pd.DataFrame, history: list[dict] | None = None, sql: str | None = None) -> tuple:
    """
    Returns (system_prompt, user_content, history_messages) for proper role-based LLM calls.
    history_messages is a list of {"role": "user"|"assistant", "content": str} dicts.
    """
    if context_rows.empty:
        context = "No records retrieved."
    else:
        # Check if this is an aggregate result (does not have standard float_id and temp_c/salinity columns with non-null values)
        is_aggregate = "float_id" not in context_rows.columns or context_rows["float_id"].isna().all()
        
        if is_aggregate:
            # Build a clear, explicit context block so the LLM knows exactly what the computed value means
            lines = ["DATABASE AGGREGATE RESULT (computed by PostgreSQL, not estimated):"]
            if sql:
                lines.append(f"SQL Query: {sql}")
            for _, row in context_rows.iterrows():
                for col, val in row.items():
                    if pd.notna(val):
                        # Map common aggregate column names to human-readable labels
                        label_map = {
                            "avg": "Average", "min": "Minimum", "max": "Maximum",
                            "count": "Count", "sum": "Sum",
                        }
                        label = label_map.get(col.lower(), col)
                        import numpy as np
                        if isinstance(val, (float, np.floating)):
                            val_str = f"{val:.2f}"
                        elif isinstance(val, (int, np.integer)):
                            val_str = f"{val:,}"
                        else:
                            val_str = str(val)
                        lines.append(f"• {label}: {val_str}")
            lines.append("Report this value directly and concisely. Do NOT ask the user for more information.")
            context = "\n".join(lines)
        else:
            q_lower = question.lower()
            is_timeseries = any(kw in q_lower for kw in ["trend", "change", "over time", "history", "timeseries", "year", "monthly"])
            if is_timeseries and "date" in context_rows.columns:
                limited = context_rows.drop_duplicates(subset=["date"]).head(10)
            else:
                limited = context_rows.head(10)

            # Build metadata overview of the full returned dataset
            total_rows = len(context_rows)
            min_date = context_rows['date'].min() if 'date' in context_rows.columns else None
            max_date = context_rows['date'].max() if 'date' in context_rows.columns else None
            unique_floats = context_rows['float_id'].nunique() if 'float_id' in context_rows.columns else 0
            
            # Format dates nicely
            min_date_str = str(min_date)[:10] if pd.notna(min_date) else "unknown"
            max_date_str = str(max_date)[:10] if pd.notna(max_date) else "unknown"
            
            if total_rows > 1:
                summary_header = (
                    f"DATABASE RETRIEVAL SUMMARY:\n"
                    f"• Total records matching filters in database: {total_rows}\n"
                    f"• Time range of retrieved dataset: {min_date_str} to {max_date_str}\n"
                    f"• Number of unique floats matching filters: {unique_floats}\n\n"
                    f"Here is a small subset of the retrieved records for detail reference:\n"
                )
            else:
                summary_header = (
                    f"DATABASE RETRIEVAL SUMMARY:\n"
                    f"• Total records matching filters in database: {total_rows}\n"
                    f"• Note: This is the single record retrieved by the PostgreSQL database scan. It represents the exact match or extremum (e.g. maximum/minimum) matching your query filters.\n\n"
                )

            bullets = []
            for _, row in limited.iterrows():
                dist_str = ""
                if "distance_km" in row and pd.notna(row["distance_km"]):
                    dist_str = f" | distance: {row['distance_km']:.0f} km"
                
                fid = row.get('float_id')
                date_val = row.get('date')
                lat = row.get('latitude')
                lng = row.get('longitude')
                depth = row.get('depth_m')
                temp = row.get('temp_c')
                sal = row.get('salinity')
                
                fid_str = f"Float {fid}" if pd.notna(fid) else "Float unknown"
                date_str = f"{date_val}" if pd.notna(date_val) else "Date unknown"
                lat_str = f"Lat {lat:.2f}" if pd.notna(lat) else "Lat unknown"
                lng_str = f"Lng {lng:.2f}" if pd.notna(lng) else "Lng unknown"
                depth_str = f"depth: {depth:.0f}m" if pd.notna(depth) else "depth unknown"
                press_str = f"pressure: {depth:.0f} dbar" if pd.notna(depth) else "pressure unknown"
                temp_str = f"temperature: {temp:.1f}°C" if pd.notna(temp) else "temperature unknown"
                sal_str = f"salinity: {sal:.2f} PSU" if pd.notna(sal) else "salinity unknown"
                
                bullets.append(
                    f"• {fid_str} | {date_str} | {lat_str} | {lng_str}{dist_str} | {depth_str} | {press_str} | {temp_str} | {sal_str}"
                )
            context = summary_header + "\n".join(bullets) if bullets else "No records retrieved."

    # Format as proper system + user + history messages
    sql_block = f"DATABASE SQL EXECUTED:\n{sql}\n" if sql else ""
    filled = CHAT_PROMPT.format(context=context, sql_block=sql_block, question=question)
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