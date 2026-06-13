import os
import time
import json
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from dotenv import load_dotenv

# Make sure imports work from root directory
import sys
sys.path.append(str(Path(__file__).parent.parent))

from rag.retriever import load_index, retrieve
from rag.embedder import _get_model
from groq import Groq

load_dotenv()

def evaluate():
    metrics = {}
    print("Starting SeaBorg RAG Evaluation...")

    # 1. Retrieval Speed
    print("\n--- 1. Retrieval Speed ---")
    queries = [
        "temperature Indian Ocean",
        "salinity at 500m",
        "float depth profile",
        "ocean conditions near India",
        "warm water region"
    ]
    
    # Ensure index is loaded
    load_index()
    
    retrieval_times = []
    top5_similarities = []
    
    # Warm up
    from rag.embedder import embed_query
    from rag.retriever import _index
    retrieve("warm up query", top_k=1)
    
    for q in queries:
        start_time = time.perf_counter()
        query_vec = embed_query(q).astype("float32")
        distances, indices = _index.search(query_vec, 5)
        end_time = time.perf_counter()
        
        duration_ms = (end_time - start_time) * 1000
        retrieval_times.append(duration_ms)
        
        # In FAISS IndexFlatL2, the distances returned are L2 squared distances
        # We normalized vectors before inserting, so L2 distance squared = 2 - 2 * cosine_sim
        # So cosine_sim = 1 - (L2_sq / 2)
        sims = [1.0 - (d / 2.0) for d in distances[0]]
        if sims:
            top5_similarities.append(np.mean(sims))
            
    avg_retrieval_ms = np.mean(retrieval_times)
    metrics["avg_retrieval_ms"] = avg_retrieval_ms
    print(f"Average retrieval time: {avg_retrieval_ms:.2f} ms")

    # 2. Embedding Stats
    print("\n--- 2. Embedding Stats ---")
    model = _get_model()
    # SentenceTransformer all-MiniLM-L6-v2 has 384 dims
    embedding_dim = model.get_sentence_embedding_dimension()
    metrics["embedding_dimensions"] = embedding_dim
    print(f"Embedding dimensions: {embedding_dim}")
    
    from rag.retriever import _index
    num_vectors = _index.ntotal if _index else 0
    metrics["total_vectors_indexed"] = num_vectors
    print(f"Total vectors indexed: {num_vectors}")
    
    index_path = os.getenv("FAISS_INDEX_PATH", "indexes/argo.faiss")
    if os.path.exists(index_path):
        index_size_mb = os.path.getsize(index_path) / (1024 * 1024)
    else:
        index_size_mb = 0
    metrics["index_size_mb"] = index_size_mb
    print(f"Index size on disk: {index_size_mb:.2f} MB")
    
    avg_sim = np.mean(top5_similarities) if top5_similarities else 0.0
    metrics["avg_cosine_similarity"] = avg_sim
    print(f"Average cosine similarity of top-5: {avg_sim:.4f}")

    # 3. Data Quality Metrics
    print("\n--- 3. Data Quality Metrics ---")
    parquet_path = os.getenv("PARQUET_PATH", "data/processed/argo.parquet")
    df = pd.read_parquet(parquet_path)
    clean_rows = len(df)
    
    # Calculate raw rows directly from NetCDF files
    raw_dir = Path("data/raw")
    total_raw_rows = 0
    if raw_dir.exists():
        for nc_file in raw_dir.glob("*.nc"):
            try:
                ds = xr.open_dataset(nc_file)
                if "N_PROF" in ds.dims and "N_LEVELS" in ds.dims:
                    total_raw_rows += ds.dims["N_PROF"] * ds.dims["N_LEVELS"]
                ds.close()
            except Exception as e:
                pass
                
    # If no raw files, fallback to clean_rows to avoid div/0
    if total_raw_rows == 0:
        total_raw_rows = clean_rows
        
    qc_pass_rate = (clean_rows / total_raw_rows) * 100 if total_raw_rows > 0 else 0
    
    metrics["total_raw_rows"] = total_raw_rows
    metrics["clean_rows"] = clean_rows
    metrics["qc_pass_rate_percent"] = qc_pass_rate
    
    temp_min, temp_max = float(df['temp_c'].min()), float(df['temp_c'].max())
    sal_min, sal_max = float(df['salinity'].min()), float(df['salinity'].max())
    depth_min, depth_max = float(df['depth_m'].min()), float(df['depth_m'].max())
    
    metrics["temp_range"] = [temp_min, temp_max]
    metrics["salinity_range"] = [sal_min, sal_max]
    metrics["depth_range"] = [depth_min, depth_max]
    
    print(f"Total raw rows parsed: {total_raw_rows}")
    print(f"Rows after QC filtering: {clean_rows}")
    print(f"QC pass rate: {qc_pass_rate:.2f}%")
    print(f"Temperature range: {temp_min:.2f} to {temp_max:.2f} °C")
    print(f"Salinity range: {sal_min:.2f} to {sal_max:.2f} PSU")
    print(f"Depth range: {depth_min:.2f} to {depth_max:.2f} m")

    # 4. LLM Response Metrics
    print("\n--- 4. LLM Response Metrics ---")
    llm_times = []
    llm_tokens = []
    
    print("Running LLM queries (this will take a few moments)...")
    for q in queries:
        results_df = retrieve(q, top_k=5)
        # Construct context block from dataframe
        context_texts = []
        for _, row in results_df.iterrows():
            # Format row nicely
            text = f"Float {row['float_id']} at {row['date']}: Depth {row['depth_m']}m, Temp {row['temp_c']}°C, Salinity {row['salinity']}"
            context_texts.append(text)
        context_block = "\\n\\n".join(context_texts)
        
        start_time = time.perf_counter()
        try:
            client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)
            model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
            prompt = f"Answer the following question based on the context:\n\nContext:\n{context_block}\n\nQuestion: {q}"
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            answer_text = response.choices[0].message.content
            end_time = time.perf_counter()
            
            llm_times.append(end_time - start_time)
            
            # Approximate token count (1 word ~ 1.3 tokens)
            approx_tokens = len(answer_text.split()) * 1.3
            llm_tokens.append(approx_tokens)
        except Exception as e:
            print(f"Error querying Groq: {e}")
            
    avg_llm_time = np.mean(llm_times) if llm_times else 0
    avg_tokens = np.mean(llm_tokens) if llm_tokens else 0
    
    metrics["avg_llm_response_time_sec"] = avg_llm_time
    metrics["avg_llm_tokens"] = avg_tokens
    
    print(f"Average response time from Groq API: {avg_llm_time:.2f} seconds")
    print(f"Average tokens in response: {avg_tokens:.0f}")

    # Save to metrics.json
    print("\nSaving to metrics.json...")
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
    print("Done!")

if __name__ == "__main__":
    evaluate()
