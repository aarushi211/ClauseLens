"""
scripts/test_neon_integration.py
End-to-end test proving Neon Postgres & Auth integration works.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.core.config import settings
from api.core import database
from api.core.neon_db import NeonDB

def test_neon_db():
    print("--- 1. Testing NeonDB Client Directly ---")
    db = NeonDB(settings.DATABASE_URL)
    
    # Test SELECT documents
    res = db.table("documents").select("*").limit(5).execute()
    print(f"NeonDB: Fetched {len(res.data)} documents from Neon Postgres.")
    assert len(res.data) > 0, "No documents found in Neon DB!"
    for d in res.data:
        print(f"  Doc: {d.get('id')} - {d.get('filename')} ({d.get('service_name')})")

    # Test SELECT chats
    res_chats = db.table("chats").select("*").limit(3).execute()
    print(f"NeonDB: Fetched {len(res_chats.data)} chats from Neon Postgres.")
    assert len(res_chats.data) > 0, "No chats found in Neon DB!"

    # Test SELECT summaries
    res_summaries = db.table("summaries").select("*").limit(3).execute()
    print(f"NeonDB: Fetched {len(res_summaries.data)} summaries from Neon Postgres.")
    assert len(res_summaries.data) > 0, "No summaries found in Neon DB!"

    # Test INSERT & DELETE
    print("Testing INSERT into Neon...")
    test_id = "00000000-0000-0000-0000-000000000001"
    db.table("documents").insert({
        "id": test_id,
        "user_id": "test-user-neon",
        "filename": "neon_test.pdf",
        "s3_key": "test_key",
        "pinecone_ns": "test_ns",
        "status": "ready"
    }).execute()
    
    verify_insert = db.table("documents").select("*").eq("id", test_id).single().execute()
    assert verify_insert.data is not None, "Failed to retrieve inserted row!"
    print(f"NeonDB INSERT verified: {verify_insert.data.get('filename')}")

    print("Testing DELETE from Neon...")
    db.table("documents").delete().eq("id", test_id).execute()
    verify_delete = db.table("documents").select("*").eq("id", test_id).single().execute()
    assert verify_delete.data is None, "Failed to delete test row!"
    print("NeonDB DELETE verified!")
    db.close()
    print("--- 1. NeonDB Direct Test: PASSED ---\n")

def test_fastapi_app():
    print("--- 2. Testing FastAPI Endpoints with NeonDB ---")
    database.init_db()
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    print(f"GET /health: {res.status_code} {res.json()}")
    assert res.status_code == 200

    # 2. Auth login
    login_res = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    print(f"POST /auth/login: {login_res.status_code} {login_res.json().get('user')}")
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 3. History documents with token
    headers = {"Authorization": f"Bearer {token}"}
    hist_res = client.get("/history/documents", headers=headers)
    print(f"GET /history/documents: {hist_res.status_code}")
    docs = hist_res.json().get("documents", [])
    print(f"Retrieved {len(docs)} documents through API connected to Neon.")
    assert len(docs) > 0, "No documents returned via API"

    print("--- 2. FastAPI End-to-End Test: PASSED ---\n")

if __name__ == "__main__":
    test_neon_db()
    test_fastapi_app()
    print("ALL NEON INTEGRATION TESTS PASSED SUCCESSFULLY!")
