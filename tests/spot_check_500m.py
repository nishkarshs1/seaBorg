"""Quick spot-check: verify 'average temperature at 500m depth' returns actual data, not a refusal."""
import os, sys
sys.path.insert(0, os.path.abspath("."))

from rag.retriever import load_index, retrieve
from llm.query_engine import answer_query

load_index()

question = "What is the average ocean temperature at 500m depth?"
rows = retrieve(question, top_k=5)
res = answer_query(question, rows)

print("STATUS:", res.get("status"))
print("ANSWER:", res.get("answer", "")[:400])
