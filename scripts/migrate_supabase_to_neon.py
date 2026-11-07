"""
scripts/migrate_supabase_to_neon.py
Migrate CSV exports from Supabase into Neon Postgres.
"""
import os
import csv
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_UNPOOLED") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL / DATABASE_URL_UNPOOLED not found in .env")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def migrate_documents(cur):
    path = os.path.join(DATA_DIR, "Supabase Snippet Untitled query (1).csv")
    if not os.path.exists(path):
        print(f"Skipping documents: {path} not found")
        return
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            cur.execute("""
                INSERT INTO public.documents (id, user_id, filename, s3_key, service_name, doc_type, pinecone_ns, created_at, status, error_reason, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                row.get("id"),
                row.get("user_id"),
                row.get("filename"),
                row.get("s3_key"),
                row.get("service_name"),
                row.get("doc_type"),
                row.get("pinecone_ns"),
                row.get("created_at"),
                row.get("status") or "ready",
                row.get("error_reason") or None,
                row.get("source_url") or None,
            ))
            count += 1
        print(f"Migrated {count} documents")

def migrate_chats(cur):
    path = os.path.join(DATA_DIR, "Supabase Snippet Untitled query (2).csv")
    if not os.path.exists(path):
        print(f"Skipping chats: {path} not found")
        return
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            sources = row.get("sources")
            # Ensure sources is valid json
            if sources:
                try:
                    json.loads(sources)
                except Exception:
                    sources = "[]"
            else:
                sources = "[]"

            cur.execute("""
                INSERT INTO public.chats (id, document_id, user_id, role, content, sources, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                row.get("id"),
                row.get("document_id"),
                row.get("user_id"),
                row.get("role"),
                row.get("content"),
                sources,
                row.get("created_at")
            ))
            count += 1
        print(f"Migrated {count} chats")

def migrate_summaries(cur):
    path = os.path.join(DATA_DIR, "Supabase Snippet Untitled query (3).csv")
    if not os.path.exists(path):
        print(f"Skipping summaries: {path} not found")
        return
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            sources = row.get("sources")
            if sources:
                try:
                    json.loads(sources)
                except Exception:
                    sources = "[]"
            else:
                sources = "[]"

            cur.execute("""
                INSERT INTO public.summaries (id, document_id, user_id, topic_label, summary_text, sources, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                row.get("id"),
                row.get("document_id"),
                row.get("user_id"),
                row.get("topic_label"),
                row.get("summary_text"),
                sources,
                row.get("created_at")
            ))
            count += 1
        print(f"Migrated {count} summaries")

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            migrate_documents(cur)
            migrate_chats(cur)
            migrate_summaries(cur)
        conn.commit()
        print("Data migration completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Data migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
