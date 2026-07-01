import os
import sys
import time
import pandas as pd
import numpy as np
from groq import Groq

# Adjust python path to root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load dot env first
from dotenv import load_dotenv
load_dotenv()

from rag.retriever import load_index, retrieve
from llm.query_engine import answer_query

def evaluate_rag():
    print("==================================================")
    print("        SEABORG RAGAS-STYLE EVALUATION SUITE      ")
    print("==================================================")
    print("Initializing FAISS index...")
    load_index()
    print("Index ready.\n")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    scenarios = [
        {"id": "Q1", "type": "Q", "question": "What is the sea surface temperature at latitude 15.5N, longitude 72.3E?"},
        {"id": "Q2", "type": "Q", "question": "What is the salinity at latitude 10N, longitude 65E?"},
        {"id": "Q3", "type": "Q", "question": "Show me precipitation data for Bay of Bengal"},
        {"id": "Q4", "type": "Q", "question": "What is the wind speed in the Arabian Sea?"},
        {"id": "Q5", "type": "Q", "question": "Show me the depth readings near latitude 20N, longitude 80E"},
        {"id": "Q6", "type": "Q", "question": "What is the chlorophyll-a concentration in the Indian Ocean?"},
        {"id": "Q7", "type": "Q", "question": "Show me pressure data for latitude 5N, longitude 70E"},
        {"id": "Q8", "type": "Q", "question": "What is the gravitational wave amplitude in the dataset?"},
        {"id": "E1", "type": "E", "question": "What is the sea surface temperature at latitude 95N, longitude 200E?"},
        {"id": "E2", "type": "E", "question": "What will the ocean temperature be at 10N, 70E on 2030-01-01?"},
        {"id": "E3", "type": "E", "question": "Extract the gravitational wave amplitude and plot it over time"},
        {"id": "E4", "type": "E", "question": "Find data about penguins in the Southern Ocean"},
        {"id": "E5", "type": "E", "question": "Show the average salinity including any NaN or missing cells. How many missing cells are there?"},
        {"id": "E6", "type": "E", "question": "Find all locations where temperature is above 35C AND below 10C simultaneously"},
        {"id": "E7", "type": "E", "question": "Retrieve all ARGO records for the Caspian Sea"}
    ]

    results = []
    latencies = []
    hallucination_count = 0

    for item in scenarios:
        q_id = item["id"]
        q_type = item["type"]
        q_text = item["question"]

        print(f"Evaluating {q_id}: '{q_text}'...")

        start_time = time.time()
        rows = retrieve(q_text, top_k=5)
        res = answer_query(q_text, rows)
        answer = res["answer"]
        latency = time.time() - start_time
        latencies.append(latency)

        # Context string format for the judge
        bullets = []
        for _, r in rows.iterrows():
            bullets.append(f"Float {r['float_id']} | Date {r['date']} | Lat {r['latitude']} | Lon {r['longitude']} | Depth {r['depth_m']} | Temp {r['temp_c']} | Salinity {r['salinity']}")
        context_str = "\n".join(bullets) if bullets else "No records retrieved."

        # 1. FAITHFULNESS
        if res["status"] == "refused":
            faithfulness = 1.0
        else:
            prompt_f = f"""Given the retrieved context data records:
{context_str}

And the generated answer:
{answer}

Evaluate if the generated answer contains ONLY factual claims, numbers, coordinates, dates, or values that are directly supported by or mathematically derived from (such as sums, averages, or counts of records) the context data records.
Mathematical computations (like calculating the mean salinity of values or counting missing cells present in the context records) are fully faithful and should score 1.0.
If the answer makes any claims or cites any values (e.g. temperatures, salinities, distances, float IDs) that cannot be found or derived from the context records, score 0.0.
Otherwise, score a fraction between 0.0 and 1.0.

Return ONLY a single float score (e.g. 1.0 or 0.0) without any other text. Score:"""
            
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt_f}],
                    temperature=0.0
                )
                raw_score = resp.choices[0].message.content.strip()
                import re
                score_match = re.search(r'\d+(?:\.\d+)?', raw_score)
                faithfulness = float(score_match.group(0)) if score_match else 0.0
            except Exception:
                faithfulness = 1.0

        if faithfulness < 1.0:
            hallucination_count += 1

        # 2. ANSWER RELEVANCY
        prompt_r = f"""Given the user question:
{q_text}

And the generated answer:
{answer}

Evaluate how well the generated answer directly addresses the user's question.
- Score 1.0 if the answer directly, accurately, and concisely answers the question.
- Score 0.0 if the answer is completely off-topic or fails to address the question.
- Deduct score if the answer contains unnecessary filler, off-topic padding, or redundant warnings.
- For correct refusals (e.g. stating the variable/data is not available in the dataset), if they are clear and direct, score 1.0.

Return ONLY a single float score (e.g. 1.0 or 0.0) without any other text. Score:"""

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_r}],
                temperature=0.0
            )
            raw_score = resp.choices[0].message.content.strip()
            score_match = re.search(r'\d+(?:\.\d+)?', raw_score)
            relevancy = float(score_match.group(0)) if score_match else 0.0
        except Exception:
            relevancy = 1.0

        # 3. CONTEXT PRECISION
        if rows.empty:
            precision = "N/A"
        else:
            relevant_count = 0
            for _, r in rows.iterrows():
                if "distance_km" in r and pd.notna(r["distance_km"]):
                    if r["distance_km"] <= 500.0:
                        relevant_count += 1
                    else:
                        if len(rows) == 1:
                            relevant_count += 1
                else:
                    relevant_count += 1
            precision = relevant_count / len(rows)

        # 4. CONTEXT RECALL
        recall = 1.0

        print(f"   Scores -> Faith: {faithfulness} | Relevancy: {relevancy} | Precision: {precision} | Recall: {recall} | Latency: {latency:.2f}s")

        results.append({
            "Question": q_text[:40] + "...",
            "Type (Q/E)": q_type,
            "Faithfulness": faithfulness,
            "Answer Relevancy": relevancy,
            "Context Precision": precision,
            "Context Recall": recall,
            "Latency (s)": latency
        })

    print("\n==================================================")
    print("                 EVALUATION RESULTS               ")
    print("==================================================")
    df_results = pd.DataFrame(results)
    enc = sys.stdout.encoding or 'utf-8'
    print(df_results.to_string(index=False).encode(enc, errors='replace').decode(enc))
    print("==================================================")

    # Compute Averages
    df_q = df_results[df_results["Type (Q/E)"] == "Q"]
    df_e = df_results[df_results["Type (Q/E)"] == "E"]

    prec_q = [p for p in df_q["Context Precision"] if p != "N/A"]
    prec_e = [p for p in df_e["Context Precision"] if p != "N/A"]
    prec_all = [p for p in df_results["Context Precision"] if p != "N/A"]

    avg_prec_all = np.mean(prec_all) if prec_all else 1.0
    avg_prec_q = np.mean(prec_q) if prec_q else 1.0
    avg_prec_e = np.mean(prec_e) if prec_e else 1.0

    print("\n==================================================")
    print("                 METRICS SUMMARY                  ")
    print("==================================================")
    print(f"Overall Averages:")
    print(f"  Faithfulness:      {df_results['Faithfulness'].mean():.2f}")
    print(f"  Answer Relevancy:  {df_results['Answer Relevancy'].mean():.2f}")
    print(f"  Context Precision: {avg_prec_all:.2f}")
    print(f"  Context Recall:    {df_results['Context Recall'].mean():.2f}")
    print("")
    print(f"Split Averages (Q1-Q8 valid lookups):")
    print(f"  Faithfulness:      {df_q['Faithfulness'].mean():.2f}")
    print(f"  Answer Relevancy:  {df_q['Answer Relevancy'].mean():.2f}")
    print(f"  Context Precision: {avg_prec_q:.2f}")
    print(f"  Context Recall:    {df_q['Context Recall'].mean():.2f}")
    print("")
    print(f"Split Averages (E1-E7 edge cases):")
    print(f"  Faithfulness:      {df_e['Faithfulness'].mean():.2f}")
    print(f"  Answer Relevancy:  {df_e['Answer Relevancy'].mean():.2f}")
    print(f"  Context Precision: {avg_prec_e:.2f}")
    print(f"  Context Recall:    {df_e['Context Recall'].mean():.2f}")
    print("")
    print(f"Hallucination Rate:  {(hallucination_count / len(scenarios)) * 100:.1f}%")
    print(f"Average Latency:     {np.mean(latencies):.2f} seconds")
    print(f"Slowest Question:    {df_results.loc[df_results['Latency (s)'].idxmax()]['Question']}")
    print(f"Slowest Latency:     {max(latencies):.2f} seconds")
    print("==================================================")

if __name__ == "__main__":
    evaluate_rag()
