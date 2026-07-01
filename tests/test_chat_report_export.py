import os
import sys
import zipfile
import io
import pandas as pd
from fastapi.testclient import TestClient

# Adjust python path to root directory
sys.path.insert(0, os.path.abspath("."))

# Load dotenv first
from dotenv import load_dotenv
load_dotenv()

from api.main import app
from rag.retriever import load_index

def run_test():
    print("==================================================")
    print("        CHAT REPORT EXPORT INTEGRATION TEST       ")
    print("==================================================")
    print("Initializing FAISS index...")
    load_index()
    print("Index ready.\n")

    client = TestClient(app)

    # 1. Simulate 3 queries
    queries = [
        "What is the salinity of float 4903777 near Lat 8.07, Lng 69.78?",  # Valid lookup
        "Show me precipitation data for Bay of Bengal",                      # Refusal
        "Show me the temperature profile of float 4903777"                  # Chart-generating
    ]

    history = []

    print("Simulating conversation turns...")
    for idx, q in enumerate(queries):
        print(f"  [Turn {idx+1}] Sending query: '{q}'")
        res = client.post("/api/chat", json={"message": q})
        assert res.status_code == 200, f"Chat API failed with status {res.status_code}"
        payload = res.json()
        
        # Determine status
        is_refused = any(kw in payload["answer"].lower() for kw in [
            "this variable is not available",
            "no argo float data found",
            "invalid coordinates",
            "is in the future",
            "outside the scope",
            "cannot be satisfied simultaneously",
            "no argo float data exists"
        ])
        status = "refused" if is_refused else "ok"
        refusal_type = "out_of_domain_variable" if is_refused and "variable is not available" in payload["answer"].lower() else (
            "distance_guard_exceeded" if is_refused and "within 500km" in payload["answer"].lower() else None
        )

        history.append({
            "query": q,
            "response": payload["answer"],
            "chart_type": payload["chart_type"],
            "rows_retrieved": len(payload.get("data", [])),
            "float_ids": payload.get("float_ids", []),
            "status": status,
            "refusal_type": refusal_type,
            "closest_distance_km": payload.get("data", [{}])[0].get("distance_km", None) if payload.get("data") else None,
            "data": payload.get("data", []),
            "timestamp": 1782877039.0 + idx * 100.0
        })

    print("Simulated history constructed successfully.\n")

    # 2. Test 1: Export with include_data = True, include_summary = True, format = "both"
    print("Test 1: Requesting Both format, with Summary and retrieved ARGO data rows...")
    payload_both = {
        "title": "SeaBorg Research Report — Test Session",
        "include_data": True,
        "include_summary": True,
        "format": "both",
        "ocean": "All Oceans",
        "history": history
    }
    
    res_both = client.post("/api/export_report", json=payload_both)
    assert res_both.status_code == 200, f"Export Report API failed with status {res_both.status_code}"
    
    # Read zip contents
    zip_bytes = res_both.content
    zip_in_mem = zipfile.ZipFile(io.BytesIO(zip_bytes))
    file_list = zip_in_mem.namelist()
    print(f"  Export ZIP contains files: {file_list}")
    
    # Assert all files are present in the zip
    pdf_filename = [f for f in file_list if f.endswith(".pdf")][0]
    turn_csv_filename = [f for f in file_list if f.endswith(".csv") and not f.startswith("argo_data")][0]
    data_csv_filename = [f for f in file_list if f.startswith("argo_data")][0]
    
    print(f"  [PASS] Found PDF report: {pdf_filename}")
    print(f"  [PASS] Found main turn CSV: {turn_csv_filename}")
    print(f"  [PASS] Found second data CSV: {data_csv_filename}")
    
    # Read and parse CSVs
    main_df = pd.read_csv(io.BytesIO(zip_in_mem.read(turn_csv_filename)))
    data_df = pd.read_csv(io.BytesIO(zip_in_mem.read(data_csv_filename)))
    
    print(f"  Main CSV shape: {main_df.shape} | Columns: {list(main_df.columns)}")
    print(f"  Data CSV shape: {data_df.shape} | Columns: {list(data_df.columns)}")
    
    assert main_df.shape[0] == 3, f"Expected 3 rows in main CSV, got {main_df.shape[0]}"
    assert "query" in main_df.columns, "Missing 'query' column in main CSV"
    assert "response" in main_df.columns, "Missing 'response' column in main CSV"
    assert "chart_type" in main_df.columns, "Missing 'chart_type' column in main CSV"
    assert "status" in main_df.columns, "Missing 'status' column in main CSV"
    
    print("  [PASS] Main CSV columns and row counts are correct.")
    
    assert data_df.shape[0] > 0, "Expected data rows in second CSV since include_data=True"
    assert "query_index" in data_df.columns, "Missing 'query_index' linking column"
    assert "float_id" in data_df.columns, "Missing 'float_id' column"
    
    print("  [PASS] Second CSV contains correct columns and linking indices.")
    
    # Save files to workspace artifacts directory for manual verification
    out_dir = r"C:\Users\nishk\.gemini\antigravity\brain\5565db96-e137-4ff4-9bcb-3c8839ead437"
    with open(os.path.join(out_dir, pdf_filename), "wb") as f:
        f.write(zip_in_mem.read(pdf_filename))
    with open(os.path.join(out_dir, turn_csv_filename), "wb") as f:
        f.write(zip_in_mem.read(turn_csv_filename))
    with open(os.path.join(out_dir, data_csv_filename), "wb") as f:
        f.write(zip_in_mem.read(data_csv_filename))
        
    print(f"  Saved test files to artifacts folder: {out_dir}\n")

    # 3. Test 2: Export with include_data = False, format = "pdf"
    print("Test 2: Requesting PDF-only format, without retrieved ARGO data rows...")
    payload_pdf = {
        "title": "SeaBorg Research Report — PDF Only",
        "include_data": False,
        "include_summary": True,
        "format": "pdf",
        "ocean": "Indian Ocean",
        "history": history
    }
    
    res_pdf = client.post("/api/export_report", json=payload_pdf)
    assert res_pdf.status_code == 200, f"Export Report API failed with status {res_pdf.status_code}"
    assert res_pdf.headers["content-type"] == "application/pdf", "Expected application/pdf content type"
    
    pdf_bytes = res_pdf.content
    print(f"  [PASS] Received PDF report directly ({len(pdf_bytes)} bytes).")
    
    # Save PDF-only file to artifacts
    pdf_only_name = f"seaborg_report_pdf_only_{pd.Timestamp.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
    with open(os.path.join(out_dir, pdf_only_name), "wb") as f:
        f.write(pdf_bytes)
    print(f"  Saved PDF-only file to artifacts: {pdf_only_name}\n")
    
    # 4. Test 3: Export with include_data = False, format = "csv"
    print("Test 3: Requesting CSV-only format, without retrieved ARGO data rows...")
    payload_csv = {
        "title": "SeaBorg Research Report — CSV Only",
        "include_data": False,
        "include_summary": False,
        "format": "csv",
        "ocean": "All Oceans",
        "history": history
    }
    
    res_csv = client.post("/api/export_report", json=payload_csv)
    assert res_csv.status_code == 200, f"Export Report API failed with status {res_csv.status_code}"
    # Since include_data=False and format=csv, it should return the main CSV directly without zip
    assert "text/csv" in res_csv.headers["content-type"], f"Expected text/csv content type, got {res_csv.headers['content-type']}"
    
    csv_bytes = res_csv.content
    print(f"  [PASS] Received main CSV directly ({len(csv_bytes)} bytes).")
    
    print("\n==================================================")
    print("  ALL REPORT EXPORT INTEGRATION TESTS PASSED!    ")
    print("==================================================")

if __name__ == "__main__":
    run_test()
