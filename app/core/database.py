from pymongo import MongoClient
import os

# In a real app, use environment variables. Default to local dev MongoDB.
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://deluzexdata_db_user:h1NcEh52LTJtZ3cE@deluzex.eszrr2w.mongodb.net/")
DATABASE_NAME = "Deluzex"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

def init_db():
    # Validate that the MongoDB server is reachable
    client.admin.command("ping")
    return db

