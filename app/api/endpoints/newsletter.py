from fastapi import APIRouter, HTTPException
from app import models
from app.core.database import db

router = APIRouter()

@router.post("/subscribe")
def subscribe_newsletter(subscriber: models.NewsletterSubscriber):
    existing = db.newsletter_subscribers.find_one({"email": subscriber.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already subscribed")
    
    result = db.newsletter_subscribers.insert_one(subscriber.model_dump(by_alias=True, exclude_none=True))
    subscriber.id = str(result.inserted_id)
    return subscriber
