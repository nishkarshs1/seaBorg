import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

# Adjust python path to root directory
sys.path.insert(0, os.path.abspath("."))

from api.routes.chat import _process_chat_cached

queries = [
    "hey",
    "what else do you do",
    "what is 2+2",
    "what is temperature at 10N 65E",
    "tell me more about that float",
    "ok cool",
    "suiiiiii",
    "find salinity anomalies near that location"
]

def main():
    from rag.retriever import load_index
    load_index()
    history = []
    print("==================================================")
    print("      SEABORG CONVERSATION FLOW TEST              ")
    print("==================================================")
    
    for i, q in enumerate(queries):
        print(f"\n[{i+1}] Query: '{q}'")
        
        # Convert history list of dicts to tuple of tuples
        history_tuple = tuple((h["role"], h["text"]) for h in history) if history else None
        
        # Call process chat
        answer, sql, chart_type, float_ids, data = _process_chat_cached(q, None, history_tuple)
        
        print(f"Chart Type: {chart_type}")
        print(f"SQL Used: {sql}")
        print(f"Answer:\n{answer}")
        print("-" * 50)
        
        # Append to history
        history.append({"role": "user", "text": q})
        history.append({"role": "ai", "text": answer})
        
        # Keep last 10 messages (5 turns)
        history = history[-10:]

if __name__ == "__main__":
    main()
