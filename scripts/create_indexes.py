import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set in environment.")
        return

    print("Connecting to database...")
    engine = create_engine(database_url, future=True)

    statements = [
        "CREATE INDEX IF NOT EXISTS idx_float_id ON argo_profiles (float_id);",
        "CREATE INDEX IF NOT EXISTS idx_date ON argo_profiles (date);",
        "CREATE INDEX IF NOT EXISTS idx_depth_m ON argo_profiles (depth_m);",
        "CREATE INDEX IF NOT EXISTS idx_lat_lon ON argo_profiles (latitude, longitude);"
    ]

    try:
        with engine.begin() as conn:
            for stmt in statements:
                print(f"Executing: {stmt}")
                conn.execute(text(stmt))
        print("Indexes created successfully!")
    except Exception as e:
        print(f"Error creating indexes: {e}")

if __name__ == "__main__":
    main()
