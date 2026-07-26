"""
SeaBorg Accuracy Test Suite
============================
Tests 50 solo queries + 100 follow-up queries against the live API.
Checks: chart_type accuracy, data relevance, answer quality, data-answer consistency.

Usage:
    python scripts/test_accuracy.py [--url http://localhost:8001]
"""
import sys, os, json, time, argparse, re
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests

DEFAULT_URL = "http://localhost:8001"

SOLO_QUERIES = [
    # Depth / Profile queries
    ("What was the deepest dive recorded in 2024?", ["profile", "none"], "Deepest dive query"),
    ("Show me the depth profile of float 6990615", ["profile"], "Explicit depth profile"),
    ("What is the maximum depth reached by any float?", ["profile", "none"], "Max depth aggregate"),
    ("Deepest measurement in the Indian Ocean", ["profile", "none"], "Regional depth query"),
    ("How deep does float 2903892 go?", ["profile", "none"], "Float-specific depth"),
    
    # Temperature queries
    ("What is the average temperature at 500m depth?", ["none", "profile"], "Avg temp at depth"),
    ("Show temperature profile for float 6990615", ["profile"], "Explicit temp profile"),
    ("What was the coldest temperature recorded?", ["none", "profile"], "Min temp query"),
    ("Temperature at the surface for float 2903892", ["none", "profile"], "Surface temp"),
    ("Which float recorded temperature above 25°C?", ["none", "profile"], "High temp filter"),
    
    # Salinity queries
    ("What is the salinity at 200m for float 6990615?", ["none", "profile"], "Salinity at depth"),
    ("Show salinity profile for float 2903892", ["profile"], "Explicit salinity profile"),
    ("Average salinity in the Arabian Sea", ["none", "summary"], "Regional salinity"),
    
    # Timeseries queries
    ("Show temperature trend for float 6990615 over time", ["timeseries"], "Explicit timeseries"),
    ("How has salinity changed over the year for float 2903892?", ["timeseries"], "Salinity trend"),
    ("Temperature change over months for float 6990615", ["timeseries"], "Monthly temp trend"),
    ("Show me the trend of depth measurements for float 6990615", ["timeseries"], "Depth trend"),
    
    # Map queries
    ("Show me floats near 15N 70E", ["map"], "Coordinate map query"),
    ("Where are the ARGO floats in the Indian Ocean?", ["map", "none"], "Regional map"),
    ("Show map of all floats", ["map"], "General map request"),
    ("Map of floats in the Arabian Sea", ["map"], "Named region map"),
    ("Location of float 6990615", ["map", "none"], "Float location"),
    
    # Trajectory queries
    ("Show the journey of float 6990615", ["3d_trajectory"], "Float journey"),
    ("What path did float 2903892 take?", ["3d_trajectory"], "Float path"),
    ("Track of float 6990615", ["3d_trajectory"], "Float track"),
    
    # TS Diagram queries
    ("Show TS diagram for float 6990615", ["ts_diagram"], "Explicit TS diagram"),
    ("Temperature vs salinity for float 2903892", ["ts_diagram"], "Temp vs salinity"),
    
    # Comparison queries
    ("Compare float 6990615 and float 2903892", ["comparison"], "Float comparison"),
    ("Difference between float 6990615 and 2903892 temperature", ["comparison"], "Temp comparison"),
    
    # Anomaly queries
    ("Are there any temperature anomalies for float 6990615?", ["anomaly"], "Temp anomaly"),
    ("Show unusual salinity measurements", ["anomaly", "none"], "Salinity anomaly"),
    
    # Summary queries
    ("Summarize the data for float 6990615", ["summary", "none"], "Float summary"),
    ("Give me an overview of float 2903892", ["summary", "none"], "Float overview"),
    
    # Conversational
    ("Hello", ["none"], "Greeting"),
    ("What can you do?", ["none"], "Capability question"),
    ("Thank you!", ["none"], "Thanks"),
    ("Who are you?", ["none"], "Identity question"),
    ("How does ARGO work?", ["none"], "General knowledge"),
    
    # Edge cases
    ("Show temperature data for 2030", ["none"], "Future date rejection"),
    ("Data at coordinates 200N 400E", ["none"], "Invalid coordinates"),
    ("Temperature above 50°C and below 10°C", ["none"], "Contradiction"),
    ("Show me float 9999999", ["none", "profile", "map"], "Non-existent float"),
    
    # Short queries
    ("deepest dive", ["profile", "none"], "Short depth query"),
    ("temperature", ["none"], "Single word query"),
    ("float 6990615", ["none", "profile", "summary"], "Just float ID"),
    ("map", ["none"], "Single word map"),
    ("salinity profile", ["profile", "none"], "Short profile query"),
    
    # Complex queries
    ("What float recorded the highest temperature in the Arabian Sea in 2024?", ["none", "profile"], "Complex multi-filter"),
    ("Show me all measurements deeper than 1000m", ["profile", "none"], "Depth threshold"),
    ("How many profiles does float 6990615 have?", ["none", "summary"], "Count query"),
]

FOLLOWUP_CHAINS = [
    # Chain 1: Deepest dive follow-ups
    [
        ("What was the deepest dive recorded in 2024?", ["profile", "none"], "Initial: deepest dive"),
        ("give me exact date", ["none"], "Follow-up: exact date"),
        ("how this related to that date", ["none"], "Follow-up: date relationship"),
        ("which float was that?", ["none"], "Follow-up: which float"),
        ("tell me more about it", ["none"], "Follow-up: more info"),
        ("show its temperature profile", ["profile"], "Follow-up: explicit chart request"),
    ],
    
    # Chain 2: Float info chain
    [
        ("Tell me about float 6990615", ["none", "summary"], "Initial: float info"),
        ("how deep does it go?", ["none"], "Follow-up: depth question"),
        ("what temperature did it record?", ["none"], "Follow-up: temp question"),
        ("when was its last measurement?", ["none"], "Follow-up: last measurement"),
        ("how many profiles does it have?", ["none"], "Follow-up: count"),
        ("show me its journey on a map", ["3d_trajectory", "map"], "Follow-up: explicit map"),
    ],
    
    # Chain 3: Temperature exploration
    [
        ("What is the average temperature at 500m depth?", ["none", "profile"], "Initial: avg temp"),
        ("is that normal?", ["none"], "Follow-up: normality check"),
        ("what about at 1000m?", ["none"], "Follow-up: different depth"),
        ("which ocean has the warmest water?", ["none"], "Follow-up: warmest ocean"),
        ("show me the data", ["none", "profile"], "Follow-up: show data"),
        ("can you plot that?", ["none", "profile", "timeseries"], "Follow-up: vague plot request"),
    ],
    
    # Chain 4: Regional exploration
    [
        ("Show me floats near 15N 70E", ["map"], "Initial: coordinate search"),
        ("what temperature did they record?", ["none"], "Follow-up: temp for those floats"),
        ("which one went deepest?", ["none"], "Follow-up: deepest among them"),
        ("tell me about that float", ["none"], "Follow-up: specific float info"),
        ("how far is the nearest float?", ["none"], "Follow-up: distance"),
        ("show salinity for the closest one", ["profile", "none"], "Follow-up: explicit profile"),
    ],
    
    # Chain 5: Timeseries chain
    [
        ("Show temperature trend for float 6990615 over time", ["timeseries"], "Initial: temp timeseries"),
        ("what about salinity?", ["none", "timeseries"], "Follow-up: different parameter"),
        ("is there any pattern?", ["none"], "Follow-up: pattern question"),
        ("when was the peak?", ["none"], "Follow-up: peak time"),
        ("compare it with float 2903892", ["comparison", "none"], "Follow-up: comparison"),
        ("go back to the temperature chart", ["timeseries", "none"], "Follow-up: return to original"),
    ],
    
    # Chain 6: Comparison chain
    [
        ("Compare float 6990615 and float 2903892", ["comparison"], "Initial: comparison"),
        ("which one goes deeper?", ["none"], "Follow-up: depth comparison"),
        ("what about temperature?", ["none"], "Follow-up: temp comparison"),
        ("which one is better?", ["none"], "Follow-up: subjective question"),
        ("show them on a map", ["map", "none"], "Follow-up: map request"),
        ("summarize the differences", ["none", "summary"], "Follow-up: summary"),
    ],
    
    # Chain 7: Anomaly exploration
    [
        ("Are there any temperature anomalies for float 6990615?", ["anomaly"], "Initial: anomaly"),
        ("when did that happen?", ["none"], "Follow-up: timing"),
        ("what was the value?", ["none"], "Follow-up: value"),
        ("is this unusual?", ["none"], "Follow-up: assessment"),
        ("show me nearby floats", ["map", "none"], "Follow-up: nearby"),
        ("did they show similar anomalies?", ["none", "anomaly"], "Follow-up: cross-check"),
    ],
    
    # Chain 8: Salinity deep dive
    [
        ("Show salinity profile for float 6990615", ["profile"], "Initial: salinity profile"),
        ("what about at the surface?", ["none"], "Follow-up: surface"),
        ("and at 2000m?", ["none"], "Follow-up: deep"),
        ("how does this compare to the global average?", ["none"], "Follow-up: comparison"),
        ("is the salinity increasing over time?", ["none", "timeseries"], "Follow-up: trend"),
        ("what causes this?", ["none"], "Follow-up: explanation"),
    ],
    
    # Chain 9: Quick fire follow-ups
    [
        ("What is the coldest temperature recorded?", ["none", "profile"], "Initial: coldest temp"),
        ("where?", ["none"], "Follow-up: location (1 word)"),
        ("when?", ["none"], "Follow-up: time (1 word)"),
        ("how cold?", ["none"], "Follow-up: value (2 words)"),
        ("which float?", ["none"], "Follow-up: float ID (2 words)"),
        ("show on map", ["map", "none"], "Follow-up: map (2 words)"),
    ],
    
    # Chain 10: TS Diagram chain
    [
        ("Show TS diagram for float 6990615", ["ts_diagram"], "Initial: TS diagram"),
        ("what water mass is this?", ["none"], "Follow-up: water mass"),
        ("add float 2903892 to the plot", ["ts_diagram", "comparison", "none"], "Follow-up: add float"),
        ("what are the outliers?", ["none", "anomaly"], "Follow-up: outliers"),
        ("zoom into the surface layer", ["none"], "Follow-up: zoom"),
        ("save this as a report", ["none"], "Follow-up: export"),
    ],
    
    # Chain 11: Journey/trajectory chain
    [
        ("Show the journey of float 2903892", ["3d_trajectory"], "Initial: journey"),
        ("how far did it travel?", ["none"], "Follow-up: distance"),
        ("what direction?", ["none"], "Follow-up: direction"),
        ("where did it start?", ["none"], "Follow-up: origin"),
        ("where is it now?", ["none"], "Follow-up: current location"),
        ("did it cross any ocean boundaries?", ["none"], "Follow-up: boundary"),
    ],
    
    # Chain 12: General science chain
    [
        ("How deep is the Indian Ocean on average?", ["none"], "Initial: general science"),
        ("what about the Pacific?", ["none"], "Follow-up: different region"),
        ("show me ARGO float data from there", ["none", "map"], "Follow-up: data request"),
        ("what temperature do they usually record?", ["none"], "Follow-up: typical temp"),
        ("is there seasonal variation?", ["none"], "Follow-up: seasonality"),
        ("show me the trend", ["none", "timeseries"], "Follow-up: trend request"),
    ],
    
    # Chain 13: Error recovery chain
    [
        ("Show data for float 9999999", ["none", "profile"], "Initial: non-existent float"),
        ("ok what floats do you have?", ["none"], "Follow-up: list floats"),
        ("tell me about the first one", ["none"], "Follow-up: vague reference"),
        ("show its depth profile", ["none", "profile"], "Follow-up: profile request"),
        ("thanks that's helpful", ["none"], "Follow-up: thanks"),
        ("bye", ["none"], "Follow-up: goodbye"),
    ],
    
    # Chain 14: Multi-parameter chain
    [
        ("What temperature and salinity does float 6990615 have at 100m?", ["none", "profile"], "Initial: multi-param"),
        ("and at 500m?", ["none"], "Follow-up: different depth"),
        ("plot both parameters vs depth", ["profile", "none"], "Follow-up: explicit plot"),
        ("which parameter changes more?", ["none"], "Follow-up: analysis"),
        ("show as TS diagram", ["ts_diagram", "none"], "Follow-up: explicit TS"),
        ("explain the relationship", ["none"], "Follow-up: explanation"),
    ],
    
    # Chain 15: Date-focused chain
    [
        ("What data do we have from January 2024?", ["none"], "Initial: date filter"),
        ("how many measurements?", ["none"], "Follow-up: count"),
        ("which floats were active?", ["none"], "Follow-up: active floats"),
        ("show the temperature range", ["none", "profile"], "Follow-up: range"),
        ("what about February?", ["none"], "Follow-up: different month"),
        ("plot the monthly comparison", ["none", "comparison", "timeseries"], "Follow-up: comparison"),
    ],
    
    # Chain 16: Depth exploration
    [
        ("Show all measurements below 2000m", ["profile", "none"], "Initial: deep measurements"),
        ("that's very deep, which float?", ["none"], "Follow-up: which float"),
        ("what was the pressure?", ["none"], "Follow-up: pressure"),
        ("is that the deepest in our dataset?", ["none"], "Follow-up: comparison"),
        ("show the depth profile", ["profile", "none"], "Follow-up: explicit profile"),
    ],
    
    # Chain 17: Vague follow-ups stress test
    [
        ("Tell me about ocean temperatures", ["none"], "Initial: vague topic"),
        ("more details", ["none"], "Follow-up: more details"),
        ("can you elaborate?", ["none"], "Follow-up: elaborate"),
        ("what else?", ["none"], "Follow-up: what else"),
        ("interesting", ["none"], "Follow-up: reaction"),
    ],
]


def call_chat_api(url: str, message: str, history: list = None) -> dict:
    payload = {"message": message, "history": history or []}
    try:
        resp = requests.post(f"{url}/api/chat", json=payload, timeout=60)
        if resp.status_code == 404:
            resp = requests.post(f"{url}/chat", json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e), "answer": "", "chart_type": "error", "data": [], "float_ids": []}


def validate_data_for_chart(chart_type: str, data: list) -> list:
    issues = []
    if not data:
        if chart_type not in ("none", "error"):
            issues.append(f"Chart type '{chart_type}' but no data returned")
        return issues
    
    sample = data[0] if data else {}
    keys = set(sample.keys()) if sample else set()
    
    if chart_type == "timeseries":
        if "date" not in keys:
            issues.append("Timeseries chart but no 'date' column in data")
        dates = set()
        for row in data:
            if row.get("date"):
                dates.add(str(row["date"])[:10])
        if len(dates) < 3:
            issues.append(f"Timeseries chart but only {len(dates)} distinct dates (need ≥3)")
    
    elif chart_type == "profile":
        has_depth = "depth" in keys or "depth_m" in keys or "pressure_dbar" in keys
        if not has_depth:
            issues.append("Profile chart but no depth/pressure column in data")
    
    elif chart_type == "map":
        has_coords = ("lat" in keys or "latitude" in keys) and ("lng" in keys or "longitude" in keys)
        if not has_coords:
            issues.append("Map chart but no latitude/longitude columns in data")
    
    elif chart_type == "ts_diagram":
        has_temp = "temp" in keys or "temp_c" in keys
        has_sal = "salinity" in keys
        if not has_temp:
            issues.append("TS diagram but no temperature column")
        if not has_sal:
            issues.append("TS diagram but no salinity column")
    
    return issues


def validate_answer_data_consistency(answer: str, data: list, chart_type: str) -> list:
    issues = []
    if not answer or not data:
        return issues
    
    answer_floats = set(re.findall(r'\b(\d{7})\b', answer))
    data_floats = set()
    for row in data:
        fid = row.get("float_id") or row.get("id")
        if fid:
            data_floats.add(str(fid))
    
    if answer_floats and data_floats:
        missing_in_data = answer_floats - data_floats
        if missing_in_data and chart_type != "none":
            issues.append(f"Answer mentions float(s) {missing_in_data} not in chart data {data_floats}")
    
    return issues


def run_solo_tests(url: str) -> dict:
    results = {"passed": 0, "failed": 0, "errors": 0, "details": []}
    
    print("\n" + "=" * 80)
    print("SOLO QUERY TESTS (50 queries)")
    print("=" * 80)
    
    for i, (query, expected_types, desc) in enumerate(SOLO_QUERIES, 1):
        print(f"\n[{i:02d}/50] {desc}")
        print(f"  Query: {query}")
        
        resp = call_chat_api(url, query)
        
        if "error" in resp and resp.get("chart_type") == "error":
            print(f"  [ERROR] ERROR: {resp['error']}")
            results["errors"] += 1
            results["details"].append({
                "test_num": i, "query": query, "desc": desc,
                "status": "ERROR", "error": resp["error"]
            })
            continue
        
        actual_type = resp.get("chart_type", "none")
        data = resp.get("data", [])
        answer = resp.get("answer", "")
        row_count = len(data)
        float_ids = resp.get("float_ids", [])
        
        type_ok = actual_type in expected_types
        data_issues = validate_data_for_chart(actual_type, data)
        consistency_issues = validate_answer_data_consistency(answer, data, actual_type)
        
        all_issues = data_issues + consistency_issues
        passed = type_ok and len(all_issues) == 0
        
        status = "PASS" if passed else "FAIL"
        icon = "[PASS]" if passed else "[FAIL]"
        
        print(f"  Chart: expected={expected_types} actual={actual_type} {'[OK]' if type_ok else '[FAIL]'}")
        print(f"  Data: {row_count} rows, {len(float_ids)} floats")
        if answer:
            print(f"  Answer: {answer[:120]}...")
        if all_issues:
            for issue in all_issues:
                print(f"  [WARN] {issue}")
        print(f"  {icon} {status}")
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "test_num": i, "query": query, "desc": desc,
            "status": status, "expected_types": expected_types,
            "actual_type": actual_type, "row_count": row_count,
            "float_ids": float_ids, "issues": all_issues,
            "answer_preview": answer[:200] if answer else "",
            "type_ok": type_ok
        })
        
        time.sleep(0.2)
    
    return results


def run_followup_tests(url: str) -> dict:
    results = {"passed": 0, "failed": 0, "errors": 0, "details": []}
    
    print("\n" + "=" * 80)
    print("FOLLOW-UP CHAIN TESTS (100+ follow-up queries)")
    print("=" * 80)
    
    total_query_num = 0
    
    for chain_idx, chain in enumerate(FOLLOWUP_CHAINS, 1):
        print(f"\n{'-' * 60}")
        print(f"Chain {chain_idx}/{len(FOLLOWUP_CHAINS)}: {chain[0][2]}")
        print(f"{'-' * 60}")
        
        history = []
        
        for step_idx, (query, expected_types, desc) in enumerate(chain):
            total_query_num += 1
            is_followup = step_idx > 0
            
            print(f"\n  [{total_query_num:03d}] {'-> ' if is_followup else ''}{desc}")
            print(f"    Query: {query}")
            
            resp = call_chat_api(url, query, history)
            
            if "error" in resp and resp.get("chart_type") == "error":
                print(f"    [ERROR] ERROR: {resp['error']}")
                results["errors"] += 1
                results["details"].append({
                    "test_num": total_query_num, "chain": chain_idx,
                    "step": step_idx, "query": query, "desc": desc,
                    "is_followup": is_followup, "status": "ERROR",
                    "error": resp["error"]
                })
                continue
            
            actual_type = resp.get("chart_type", "none")
            data = resp.get("data", [])
            answer = resp.get("answer", "")
            row_count = len(data)
            float_ids = resp.get("float_ids", [])
            
            type_ok = actual_type in expected_types
            data_issues = validate_data_for_chart(actual_type, data)
            consistency_issues = validate_answer_data_consistency(answer, data, actual_type)
            
            followup_issues = []
            if is_followup and expected_types == ["none"] and actual_type != "none" and row_count > 0:
                followup_issues.append(f"Follow-up query got chart '{actual_type}' with {row_count} rows — should be 'none'")
            
            all_issues = data_issues + consistency_issues + followup_issues
            passed = type_ok and len(all_issues) == 0
            
            status = "PASS" if passed else "FAIL"
            icon = "[PASS]" if passed else "[FAIL]"
            
            print(f"    Chart: expected={expected_types} actual={actual_type} {'[OK]' if type_ok else '[FAIL]'}")
            print(f"    Data: {row_count} rows, {len(float_ids)} floats")
            if answer:
                print(f"    Answer: {answer[:100]}...")
            if all_issues:
                for issue in all_issues:
                    print(f"    [WARN] {issue}")
            print(f"    {icon} {status}")
            
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "test_num": total_query_num, "chain": chain_idx,
                "step": step_idx, "query": query, "desc": desc,
                "is_followup": is_followup, "status": status,
                "expected_types": expected_types, "actual_type": actual_type,
                "row_count": row_count, "float_ids": float_ids,
                "issues": all_issues, "answer_preview": answer[:200] if answer else "",
                "type_ok": type_ok
            })
            
            history.append({"role": "user", "text": query})
            history.append({"role": "assistant", "text": answer})
            
            time.sleep(0.3)
    
    return results


def print_summary(solo: dict, followup: dict):
    print("\n" + "=" * 80)
    print("ACCURACY TEST REPORT")
    print("=" * 80)
    
    solo_total = solo["passed"] + solo["failed"] + solo["errors"]
    fu_total = followup["passed"] + followup["failed"] + followup["errors"]
    
    if solo_total > 0:
        print(f"\nSolo Queries:    {solo['passed']}/{solo_total} passed "
              f"({solo['passed']/solo_total*100:.1f}%)  |  {solo['failed']} failed  |  {solo['errors']} errors")
    if fu_total > 0:
        print(f"Follow-up Queries: {followup['passed']}/{fu_total} passed "
              f"({followup['passed']/fu_total*100:.1f}%)  |  {followup['failed']} failed  |  {followup['errors']} errors")
    
    total_passed = solo["passed"] + followup["passed"]
    total = solo_total + fu_total
    if total > 0:
        print(f"\n----------------------------------------")
        print(f"OVERALL:         {total_passed}/{total} passed ({total_passed/total*100:.1f}%)")
        
        all_details = solo["details"] + followup["details"]
        type_correct = sum(1 for d in all_details if d.get("type_ok", False))
        type_total = sum(1 for d in all_details if d.get("status") != "ERROR")
        if type_total > 0:
            print(f"\nChart Type Classification Accuracy: {type_correct}/{type_total} ({type_correct/type_total*100:.1f}%)")
    
    return total_passed, total


def main():
    parser = argparse.ArgumentParser(description="SeaBorg Accuracy Test Suite")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--solo-only", action="store_true", help="Run only solo tests")
    parser.add_argument("--followup-only", action="store_true", help="Run only follow-up tests")
    parser.add_argument("--output", default=None, help="Save results JSON to file")
    args = parser.parse_args()
    
    print(f"SeaBorg Accuracy Test Suite")
    print(f"API URL: {args.url}")
    
    solo_results = {"passed": 0, "failed": 0, "errors": 0, "details": []}
    followup_results = {"passed": 0, "failed": 0, "errors": 0, "details": []}
    
    if not args.followup_only:
        solo_results = run_solo_tests(args.url)
    
    if not args.solo_only:
        followup_results = run_followup_tests(args.url)
    
    total_passed, total = print_summary(solo_results, followup_results)
    
    output_path = Path(args.output) if args.output else PROJECT_ROOT / "scripts" / "test_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "solo": solo_results,
            "followup": followup_results,
            "summary": {
                "total_passed": total_passed,
                "total": total,
                "accuracy": round(total_passed / total * 100, 1) if total > 0 else 0
            }
        }, f, indent=2, default=str)
    
    print(f"\n[FILE] Results saved to: {output_path}")


if __name__ == "__main__":
    main()
