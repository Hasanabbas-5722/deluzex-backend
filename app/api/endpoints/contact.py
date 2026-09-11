from fastapi import APIRouter, Depends
from app import models
from app.api.deps import get_current_active_admin
from app.core.database import db

router = APIRouter()

@router.get("")
def read_contacts(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_admin)
):
    docs = list(db.contacts.find().sort("created_at", -1).skip(skip).limit(limit))
    return [models.ContactMessage(**doc) for doc in docs]

@router.post("")
def create_contact(contact: models.ContactMessage):
    result = db.contacts.insert_one(contact.model_dump(by_alias=True, exclude_none=True))
    contact.id = str(result.inserted_id)
    return contact
