from fastapi import APIRouter, HTTPException
from app import models

router = APIRouter()

@router.post("/subscribe")
async def subscribe_newsletter(subscriber: models.NewsletterSubscriber):
    existing = await models.NewsletterSubscriber.find_one({"email": subscriber.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already subscribed")
    await subscriber.insert()
    return subscriber
