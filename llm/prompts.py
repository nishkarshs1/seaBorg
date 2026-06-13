import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CHAT_PROMPT = """You are SeaBorg, an expert AI assistant and ocean scientist. 
You are warm, intelligent, and conversational - like ChatGPT but specialized 
in oceanography and ARGO float data.

Your personality rules:
- Be conversational and engaging, never robotic
- For ocean/data questions: cite specific numbers from the ARGO records below
- For general questions (greetings, math, coding, science): answer helpfully 
  and naturally, then optionally connect to ocean science if interesting
- Never say "I cannot answer that" or "I only know about oceans"
- If greeted with "hi" or "hello": respond warmly and introduce yourself
- Format numbers in bold using markdown
- Use bullet points for lists
- Keep responses concise but complete

ARGO DATA RECORDS (use for ocean questions):
{context}

USER QUESTION: {question}

Respond naturally. Lead with data if ocean-related. Be helpful always."""

SQL_PROMPT = """Convert the following question into a valid PostgreSQL SELECT query for the
table `argo_profiles` with columns:
id, float_id, date, latitude, longitude, depth_m, temp_c, salinity, oxygen, created_at.

IMPORTANT: The table does NOT have a region or ocean column. When a question
references a named ocean or sea, you MUST filter by latitude and longitude
ranges. If coordinate hints are provided in parentheses at the end of the
question, use those exact BETWEEN values.

Return ONLY the SQL query. No explanation. No markdown. No semicolon at the end.

Question: {question}"""


def build_prompt(question: str, context_rows: pd.DataFrame) -> str:
    """
    Formats context_rows as a bullet list and fills CHAT_PROMPT.

    Only the filtered data rows are included - no geographic context is
    injected so the LLM cannot hallucinate region assignments.  Rows are
    capped at 10 to keep the prompt focused.

    Args:
        question: The user's natural language question.
        context_rows: DataFrame of retrieved ARGO rows from retriever.retrieve().

    Returns:
        A fully formatted prompt string ready to send to the LLM.

    Side effects:
        None.
    """
    # Limit to 10 rows to keep the prompt concise and focused
    limited = context_rows.head(10)

    bullets = []
    for _, row in limited.iterrows():
        bullets.append(
            f"• Float {row['float_id']} | {row['date']} | "
            f"{row['depth_m']:.0f}m | {row['temp_c']:.1f}°C | "
            f"{row['salinity']:.2f} PSU"
        )
    context = "\n".join(bullets) if bullets else "No records retrieved."

    return CHAT_PROMPT.format(context=context, question=question)