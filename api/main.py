import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.routes import chat, data, export
from rag.retriever import load_index

load_dotenv()

app = FastAPI(title="SeaBorg API", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
_environment = os.getenv("ENVIRONMENT", "development")
_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
]
_frontend_url = os.getenv("FRONTEND_URL")
if _frontend_url:
    _origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(export.router, prefix="/api")

@app.get("/health", tags=["Health"])
def health_check():
    """Simple health check endpoint for deployment orchestration (like Railway)."""
    return {"status": "ok", "service": "seaborg-api"}


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup() -> None:
    """
    Runs at server startup.

    Loads the FAISS index into memory, verifies the database connection,
    and auto-seeds the database from the bundled Parquet file if empty.

    Side effects:
        Loads FAISS index and Parquet DataFrame into module-level rag.retriever state.
        Opens and closes a PostgreSQL connection to verify connectivity.
        Seeds argo_profiles table from Parquet if the table is empty or missing.
    """
    load_index()

    from db.connection import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Auto-seed: populate database from parquet if table is empty/missing
    _auto_seed_database(engine)

    print("SeaBorg API ready.")


def _auto_seed_database(engine) -> None:
    """
    Seeds the argo_profiles table from the bundled Parquet file if it is
    empty or does not exist. This makes deploys to Railway fully automatic.
    """
    import pandas as pd

    parquet_path = os.getenv("PARQUET_PATH", "data/processed/argo.parquet")
    if not os.path.exists(parquet_path):
        print(f"[AUTO-SEED] Parquet file not found at {parquet_path}. Skipping.")
        return

    try:
        with engine.connect() as conn:
            # Check if table exists and has data
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'argo_profiles')"
            ))
            table_exists = result.scalar()

            if table_exists:
                count = conn.execute(text("SELECT COUNT(*) FROM argo_profiles")).scalar()
                if count > 0:
                    print(f"[AUTO-SEED] Database already has {count} rows. Skipping seed.")
                    return

        # Table is empty or missing — seed from parquet
        print(f"[AUTO-SEED] Empty database detected. Loading data from {parquet_path}...")
        df = pd.read_parquet(parquet_path)

        if df.empty:
            print("[AUTO-SEED] Parquet file is empty. Nothing to seed.")
            return

        # Insert in chunks and attempt checkpoint if supported by host
        df.to_sql("argo_profiles", engine, if_exists="append", index=False, chunksize=2000)
        try:
            with engine.connect() as conn:
                conn.execute(text("CHECKPOINT"))
                conn.commit()
        except Exception:
            pass
        print(f"[AUTO-SEED] Successfully loaded {len(df)} rows into argo_profiles.")

    except Exception as e:
        print(f"[AUTO-SEED] Warning: Could not auto-seed database: {e}")