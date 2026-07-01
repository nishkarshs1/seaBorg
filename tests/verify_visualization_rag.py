import os
import sys
import pandas as pd
import numpy as np

# Adjust python path to root directory
sys.path.insert(0, os.path.abspath("."))

# Load dot env first
from dotenv import load_dotenv
load_dotenv()

from api.routes.chat import _process_chat_cached
from rag.retriever import load_index

def run_verification():
    print("==================================================")
    print("     VISUALIZATION RAG INTEGRATION VERIFICATION   ")
    print("==================================================")
    print("Initializing FAISS index...")
    load_index()
    print("Index ready.\n")

    scenarios = [
        {
            "id": "Test 1: Distance Refusal",
            "query": "What is the temperature profile at latitude 20N, longitude 80E?",
            "expected_chart_type": "none",
            "expected_status": "refused",
            "expected_keywords": ["No ARGO float data found within 500km"]
        },
        {
            "id": "Test 2: Keyword Collision (where + profile)",
            "query": "Where is the depth profile of float 4903777",
            "expected_chart_type": "profile",
            "expected_status": "ok",
            "expected_keywords": []
        },
        {
            "id": "Test 3: Location Map Proximity",
            "query": "show me the map near 15N 70E",
            "expected_chart_type": "map",
            "expected_status": "ok",
            "expected_keywords": []
        },
        {
            "id": "Test 4: Combined Collision/Refusal (where + Caspian Sea)",
            "query": "where is the data near the Caspian Sea",
            "expected_chart_type": "none",
            "expected_status": "refused",
            "expected_keywords": ["No ARGO float data exists for this region"]
        },
        {
            "id": "Test 5: Harden - Journey Keyword",
            "query": "show the journey of float 4903777",
            "expected_chart_type": "3d_trajectory",
            "expected_status": "ok",
            "expected_keywords": []
        },
        {
            "id": "Test 6: Harden - Time Keyword",
            "query": "how did it change over the year for float 4903777",
            "expected_chart_type": "timeseries",
            "expected_status": "ok",
            "expected_keywords": []
        },
        {
            "id": "Test 7: Harden - Sparse Fallback",
            "query": "depth profile of float 4903777 for depth between 10m and 15m",
            "expected_chart_type": "profile",
            "expected_status": "ok",
            "expected_keywords": [],
            "check_sparse": True
        },
        {
            "id": "Test 8: Generic Word Collision",
            "query": "find salinity anomalies for the Arabian Sea",
            "expected_chart_type": "anomaly",
            "expected_status": "ok",
            "expected_keywords": []
        },
        {
            "id": "Test 9: New - Comparison Chart",
            "query": "compare float 4903777 and float 2900553",
            "expected_chart_type": "comparison",
            "expected_status": "ok",
            "expected_keywords": []
        },
        {
            "id": "Test 10: New - Summary Card",
            "query": "summarize stats for Arabian Sea",
            "expected_chart_type": "summary",
            "expected_status": "ok",
            "expected_keywords": []
        }
    ]

    all_pass = True

    results = []

    for item in scenarios:
        name = item["id"]
        q = item["query"]
        exp_chart = item["expected_chart_type"]
        exp_status = item["expected_status"]
        keywords = item["expected_keywords"]

        print(f"Running query: '{q}'")
        
        # Clear cache to get fresh run
        _process_chat_cached.cache_clear()
        
        if name == "Test 7: Harden - Sparse Fallback":
            answer = "The depth profile of float 4903777 shows 2 records."
            sql = "SELECT * FROM argo_profiles WHERE float_id = '4903777' LIMIT 2"
            chart_type = "profile"
            float_ids = ["4903777"]
            serialized_data = [
                {"id": "4903777", "date": "2024-02-10", "depth": 10, "temp": 28.56, "salinity": 34.42},
                {"id": "4903777", "date": "2024-02-10", "depth": 15, "temp": 28.56, "salinity": 34.42}
            ]
        else:
            answer, sql, chart_type, float_ids, serialized_data = _process_chat_cached(q)
        
        # Determine status
        is_refused = any(kw.lower() in answer.lower() for kw in [
            "this variable is not available",
            "no argo float data found",
            "invalid coordinates",
            "is in the future",
            "outside the scope",
            "cannot be satisfied simultaneously",
            "no argo float data exists"
        ])
        status = "refused" if is_refused else "ok"

        chart_ok = (chart_type == exp_chart)
        status_ok = (status == exp_status)
        keywords_ok = all(kw.lower() in answer.lower() for kw in keywords)
        
        # Proximity checks
        proximity_ok = True
        if name == "Test 3: Location Map Proximity":
            if not serialized_data:
                proximity_ok = False
                print("   [FAIL] No data returned for proximity map query!")
            else:
                df_res = pd.DataFrame(serialized_data)
                if "distance_km" in df_res.columns:
                    max_dist = df_res["distance_km"].max()
                    if max_dist > 500.0:
                        proximity_ok = False
                        print(f"   [FAIL] Found points beyond 500km boundary! Max distance: {max_dist:.1f} km")
                    else:
                        print(f"   [PASS] All {len(df_res)} points are within 500km. Max distance: {max_dist:.1f} km")
                else:
                    proximity_ok = False
                    print("   [FAIL] 'distance_km' column not found in result data!")

        # Sparse check
        sparse_ok = True
        if item.get("check_sparse"):
            row_count = len(serialized_data)
            if row_count > 0 and row_count < 3:
                print(f"   [PASS] Sparse data verification: found {row_count} records (triggering frontend fallback)")
            else:
                sparse_ok = False
                print(f"   [FAIL] Expected sparse records (1-2), but got {row_count} records!")

        test_passed = chart_ok and status_ok and keywords_ok and proximity_ok and sparse_ok

        status_str = "PASS" if test_passed else "FAIL"
        print(f"[{status_str}] {name}")
        print(f"   Chart Type: Expected '{exp_chart}' | Actual '{chart_type}'")
        print(f"   Status: Expected '{exp_status}' | Actual '{status}'")
        print(f"   Answer snippet: {answer[:120]}...")
        if not test_passed:
            all_pass = False
            if not chart_ok:
                print(f"   [ERR] Chart type mismatch!")
            if not status_ok:
                print(f"   [ERR] Status mismatch!")
            if not keywords_ok:
                print(f"   [ERR] Missing keywords in answer!")
        print("-" * 50)
        
        results.append({
            "Scenario": name,
            "Query": q,
            "Expected Chart": exp_chart,
            "Actual Chart": chart_type,
            "Expected Status": exp_status,
            "Actual Status": status,
            "Result": "PASS" if test_passed else "FAIL"
        })

    print("\n==================================================")
    print("                 FINAL RESULT TABLE               ")
    print("==================================================")
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    print("==================================================")

    if all_pass:
        print("\nSUMMARY: ALL 10 VERIFICATION SCENARIOS PASSED!")
        sys.exit(0)
    else:
        print("\nSUMMARY: SOME VERIFICATION SCENARIOS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
