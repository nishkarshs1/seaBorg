import os
import sys
import io
import re
import pandas as pd

# Adjust python path to root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag.retriever import load_index, retrieve
from llm.query_engine import answer_query, REFUSAL_MESSAGE

# 15 Verified test scenarios (Q1-Q8, E1-E7) with robust, index-independent validation rules
SCENARIOS = [
    {
        "id": "Q1",
        "question": "What is the sea surface temperature at latitude 15.5N, longitude 72.3E?",
        "expected_type": "ANSWER",
        "keywords": ["float", "temperature"]
    },
    {
        "id": "Q2",
        "question": "What is the salinity at latitude 10N, longitude 65E?",
        "expected_type": "ANSWER",
        "keywords": ["float", "salinity"]
    },
    {
        "id": "Q3",
        "question": "Show me precipitation data for Bay of Bengal",
        "expected_type": "REFUSAL",
        "keywords": ["variable is not available in the ARGO dataset"]
    },
    {
        "id": "Q4",
        "question": "What is the wind speed in the Arabian Sea?",
        "expected_type": "REFUSAL",
        "keywords": ["variable is not available in the ARGO dataset"]
    },
    {
        "id": "Q5",
        "question": "Show me the depth readings near latitude 20N, longitude 80E",
        "expected_type": "REFUSAL",
        "keywords": ["No ARGO float data found within 500km"]
    },
    {
        "id": "Q6",
        "question": "What is the chlorophyll-a concentration in the Indian Ocean?",
        "expected_type": "REFUSAL",
        "keywords": ["ARGO dataset"]
    },
    {
        "id": "Q7",
        "question": "Show me pressure data for latitude 5N, longitude 70E",
        "expected_type": "ANSWER",
        "keywords": ["pressure"]
    },
    {
        "id": "Q8",
        "question": "What is the gravitational wave amplitude in the dataset?",
        "expected_type": "REFUSAL",
        "keywords": ["variable is not available in the ARGO dataset"]
    },
    {
        "id": "E1",
        "question": "What is the sea surface temperature at latitude 95N, longitude 200E?",
        "expected_type": "REFUSAL",
        "keywords": ["Invalid coordinates"]
    },
    {
        "id": "E2",
        "question": "What will the ocean temperature be at 10N, 70E on 2030-01-01?",
        "expected_type": "REFUSAL",
        "keywords": ["in the future", "does not support future predictions"]
    },
    {
        "id": "E3",
        "question": "Extract the gravitational wave amplitude and plot it over time",
        "expected_type": "REFUSAL",
        "keywords": ["variable is not available in the ARGO dataset"]
    },
    {
        "id": "E4",
        "question": "Find data about penguins in the Southern Ocean",
        "expected_type": "REFUSAL",
        "keywords": ["outside the scope of ARGO ocean data"]
    },
    {
        "id": "E5",
        "question": "Show the average salinity including any NaN or missing cells. How many missing cells are there?",
        "expected_type": "ANSWER",
        "keywords": ["average salinity", "missing cells"]
    },
    {
        "id": "E6",
        "question": "Find all locations where temperature is above 35C AND below 10C simultaneously",
        "expected_type": "REFUSAL",
        "keywords": ["cannot be satisfied simultaneously"]
    },
    {
        "id": "E7",
        "question": "Retrieve all ARGO records for the Caspian Sea",
        "expected_type": "REFUSAL",
        "keywords": ["No ARGO float data exists for this region"]
    }
]

def run_suite():
    print("==================================================")
    print("      SEABORG RAG REGRESSION TEST SUITE           ")
    print("==================================================")
    
    print("Initializing FAISS index...")
    load_index()
    print("Index ready.\n")
    
    passed_count = 0
    failed_count = 0
    results = []

    for item in SCENARIOS:
        q_id = item["id"]
        q_text = item["question"]
        expected_type = item["expected_type"]
        keywords = item["keywords"]

        # Capture retriever console output (similarity debug lines)
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout
        try:
            rows = retrieve(q_text, top_k=5)
        finally:
            sys.stdout = old_stdout

        res = answer_query(q_text, rows)
        answer = res["answer"]
        
        # Determine actual type
        is_refusal = (
            answer == REFUSAL_MESSAGE or 
            "No ARGO float data found" in answer or
            "Invalid coordinates" in answer or
            "in the future" in answer or
            "outside the scope" in answer or
            "cannot be satisfied simultaneously" in answer or
            "No ARGO float data exists" in answer or
            "variable is not available" in answer
        )
        actual_type = "REFUSAL" if is_refusal else "ANSWER"
        
        # Validate expectations
        type_ok = (actual_type == expected_type)
        keywords_ok = all(kw.lower() in answer.lower() for kw in keywords)
        
        status = "PASS" if (type_ok and keywords_ok) else "FAIL"
        
        results.append({
            "id": q_id,
            "question": q_text,
            "expected_type": expected_type,
            "actual_type": actual_type,
            "status": status,
            "details": f"Missing keywords: {[kw for kw in keywords if kw.lower() not in answer.lower()]}" if not keywords_ok else "All checks matching"
        })

        if status == "PASS":
            passed_count += 1
        else:
            failed_count += 1

        print(f"[{status}] {q_id}: {q_text}")
        print(f"      Expected: {expected_type} | Actual: {actual_type}")
        print(f"      Response snippet: {answer[:120]}...")
        if status == "FAIL":
            print(f"      Details: {results[-1]['details']}")
        print("-" * 50)

    print("\n==================================================")
    print(f"SUMMARY: Passed {passed_count}/{len(SCENARIOS)} tests. Failed {failed_count} tests.")
    print("==================================================")
    
    if failed_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_suite()
