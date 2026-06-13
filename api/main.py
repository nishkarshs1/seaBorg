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
if _environment == "production":
    _origins = [os.getenv("FRONTEND_URL", "")]
else:
    _origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
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

    Loads the FAISS index into memory and verifies the database connection.
    Prints 'SeaBorg API ready.' on success.

    Side effects:
        Loads FAISS index and Parquet DataFrame into module-level rag.retriever state.
        Opens and closes a PostgreSQL connection to verify connectivity.
    """
    load_index()

    from db.connection import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    print("SeaBorg API ready.")