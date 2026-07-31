from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os

from app import models

# In a real app, use environment variables. Default to local dev MongoDB.
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://deluzexdata_db_user:h1NcEh52LTJtZ3cE@deluzex.eszrr2w.mongodb.net/")
DATABASE_NAME = "Deluzex"

async def init_db():
    client = AsyncIOMotorClient(MONGO_URI)
    
    # Initialize beanie with all the document models
    await init_beanie(
        database=client[DATABASE_NAME],
        document_models=[
            models.User,
            models.AuditLog,
            models.Category,
            models.Product,
            models.Project,
            models.Testimonial,
            models.NewsletterSubscriber,
            models.CartItem
        ]
    )
