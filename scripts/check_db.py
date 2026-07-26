import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    res = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
    tables = [r[0] for r in res.fetchall()]
    print(f"Public tables: {tables}")
    if "argo_profiles" in tables:
        count = conn.execute(text("SELECT COUNT(*) FROM argo_profiles")).scalar()
        floats = conn.execute(text("SELECT COUNT(DISTINCT float_id) FROM argo_profiles")).scalar()
        print(f"Rows: {count}, Distinct floats: {floats}")
    else:
        print("argo_profiles table does not exist yet.")
