from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app import models
from app.core.database import db
from datetime import datetime
from typing import Optional, List
import io
import csv

router = APIRouter()

@router.post("/subscribe")
def subscribe_newsletter(subscriber: models.NewsletterSubscriber):
    email = str(subscriber.email).strip().lower()
    
    # Check if already subscribed
    existing = db.newsletter_subscribers.find_one({"email": email})
    if existing:
        return {
            "status": "already_subscribed",
            "message": "You're already subscribed. We'll notify you once we go live.",
            "email": email,
            "subscribed_at": existing.get("subscribed_at")
        }
    
    doc = {
        "email": email,
        "subscribed_at": datetime.utcnow(),
        "is_notified": False,
        "notified_at": None,
        "source": subscriber.source or "coming_soon"
    }
    
    result = db.newsletter_subscribers.insert_one(doc)
    doc_id = str(result.inserted_id)
    
    return {
        "status": "success",
        "message": "Thank you. We will notify you as soon as we launch.",
        "subscriber": {
            "id": doc_id,
            "email": email,
            "subscribed_at": doc["subscribed_at"].isoformat(),
            "is_notified": False,
            "source": doc["source"]
        }
    }

@router.get("/subscribers")
def get_subscribers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    notified: Optional[bool] = None
):
    query = {}
    if notified is not None:
        query["is_notified"] = notified
        
    total_count = db.newsletter_subscribers.count_documents({})
    pending_count = db.newsletter_subscribers.count_documents({"is_notified": False})
    notified_count = db.newsletter_subscribers.count_documents({"is_notified": True})
    
    cursor = db.newsletter_subscribers.find(query).sort("subscribed_at", -1).skip(skip).limit(limit)
    subscribers = []
    for doc in cursor:
        doc["id"] = str(doc.get("_id", ""))
        doc["_id"] = str(doc.get("_id", ""))
        if isinstance(doc.get("subscribed_at"), datetime):
            doc["subscribed_at"] = doc["subscribed_at"].isoformat()
        if isinstance(doc.get("notified_at"), datetime):
            doc["notified_at"] = doc["notified_at"].isoformat()
        subscribers.append(doc)
        
    return {
        "total": total_count,
        "pending": pending_count,
        "notified": notified_count,
        "subscribers": subscribers
    }

@router.get("/export-csv")
def export_subscribers_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Email", "Subscribed At (UTC)", "Is Notified", "Notified At", "Source"])
    
    cursor = db.newsletter_subscribers.find({}).sort("subscribed_at", -1)
    for doc in cursor:
        writer.writerow([
            str(doc.get("_id", "")),
            doc.get("email", ""),
            str(doc.get("subscribed_at", "")),
            doc.get("is_notified", False),
            str(doc.get("notified_at", "") or ""),
            doc.get("source", "coming_soon")
        ])
        
    output.seek(0)
    filename = f"deluzex_subscribers_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
