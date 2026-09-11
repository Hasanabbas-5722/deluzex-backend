from pymongo import MongoClient
import os
import time
from app.core.logger import app_logger

# In a real app, use environment variables. Default to local dev MongoDB.
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://deluzexdata_db_user:h1NcEh52LTJtZ3cE@deluzex.eszrr2w.mongodb.net/")
DATABASE_NAME = "Deluzex"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

def init_db():
    """Validates MongoDB connection, logs latency, and returns (db, ping_ms, is_connected)."""
    t0 = time.perf_counter()
    try:
        client.admin.command("ping")
        ping_ms = (time.perf_counter() - t0) * 1000.0
        collections = db.list_collection_names()
        app_logger.info(f"MongoDB connection verified: '{DATABASE_NAME}' ({len(collections)} collections, {ping_ms:.1f}ms ping)")
        return db, ping_ms, True
    except Exception as exc:
        app_logger.error(f"Failed to connect to MongoDB: {exc}")
        return db, 0.0, False

