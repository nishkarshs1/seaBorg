from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:12345@localhost:5432/seaborg')
with engine.connect() as conn:
    print(conn.execute(text('SELECT COUNT(*) FROM argo_profiles;')).scalar())
