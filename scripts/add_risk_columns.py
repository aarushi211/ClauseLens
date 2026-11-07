import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL_UNPOOLED") or os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
with conn.cursor() as cur:
    cur.execute("ALTER TABLE public.summaries ADD COLUMN IF NOT EXISTS risk_level TEXT DEFAULT 'LOW';")
    cur.execute("ALTER TABLE public.summaries ADD COLUMN IF NOT EXISTS risk_reason TEXT DEFAULT NULL;")
    cur.execute("ALTER TABLE public.summaries ADD COLUMN IF NOT EXISTS unfair_category TEXT DEFAULT NULL;")
conn.commit()
conn.close()
print("Successfully updated public.summaries schema with risk flags!")
