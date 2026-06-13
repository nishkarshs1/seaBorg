import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

_engine = None

def get_engine():
    """
    Returns a global SQLAlchemy engine with connection pooling.
    """
    global _engine
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is not set.")
        
        _engine = create_engine(
            database_url,
            future=True,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
    return _engine
