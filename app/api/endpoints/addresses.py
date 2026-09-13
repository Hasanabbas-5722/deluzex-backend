from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.core.database import db
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse

router = APIRouter()

def serialize_address(doc: dict) -> dict:
    if not doc:
        return {}
    doc_copy = dict(doc)
    doc_copy["id"] = str(doc_copy.get("_id", ""))
    return doc_copy

@router.get("", response_model=List[AddressResponse])
def get_user_addresses(email: Optional[str] = Query(None)):
    """
    Fetch all saved delivery addresses for a given user email from MongoDB.
    """
    query = {}
    if email:
        query["user_email"] = email.strip().lower()

    docs = list(db.addresses.find(query).sort("created_at", -1))
    return [AddressResponse(**serialize_address(d)) for d in docs]


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_user_address(address_in: AddressCreate):
    """
    Save a new delivery address to MongoDB.
    """
    email_clean = address_in.user_email.strip().lower()
    
    # Check if user has any existing addresses
    existing_count = db.addresses.count_documents({"user_email": email_clean})
    is_default = address_in.is_default
    if existing_count == 0:
        is_default = True

    # If this is default, reset all other addresses for this user
    if is_default:
        db.addresses.update_many(
            {"user_email": email_clean},
            {"$set": {"is_default": False}}
        )

    doc_data = address_in.model_dump()
    doc_data["user_email"] = email_clean
    doc_data["is_default"] = is_default
    doc_data["created_at"] = datetime.utcnow()

    res = db.addresses.insert_one(doc_data)
    created_doc = db.addresses.find_one({"_id": res.inserted_id})
    return AddressResponse(**serialize_address(created_doc))


@router.put("/{address_id}", response_model=AddressResponse)
def update_user_address(address_id: str, address_in: AddressUpdate):
    """
    Update an existing delivery address in MongoDB.
    """
    if not ObjectId.is_valid(address_id):
        raise HTTPException(status_code=400, detail="Invalid address ID format")

    existing = db.addresses.find_one({"_id": ObjectId(address_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Address not found")

    update_data = {k: v for k, v in address_in.model_dump(exclude_unset=True).items() if v is not None}

    if update_data.get("is_default") is True:
        db.addresses.update_many(
            {"user_email": existing["user_email"]},
            {"$set": {"is_default": False}}
        )

    if update_data:
        db.addresses.update_one({"_id": ObjectId(address_id)}, {"$set": update_data})

    updated = db.addresses.find_one({"_id": ObjectId(address_id)})
    return AddressResponse(**serialize_address(updated))


@router.put("/{address_id}/default", response_model=AddressResponse)
def set_default_address(address_id: str):
    """
    Set an address as the default delivery address for the user.
    """
    if not ObjectId.is_valid(address_id):
        raise HTTPException(status_code=400, detail="Invalid address ID format")

    existing = db.addresses.find_one({"_id": ObjectId(address_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Address not found")

    user_email = existing.get("user_email")
    if user_email:
        db.addresses.update_many(
            {"user_email": user_email},
            {"$set": {"is_default": False}}
        )

    db.addresses.update_one({"_id": ObjectId(address_id)}, {"$set": {"is_default": True}})
    updated = db.addresses.find_one({"_id": ObjectId(address_id)})
    return AddressResponse(**serialize_address(updated))


@router.delete("/{address_id}")
def delete_user_address(address_id: str):
    """
    Delete an address from MongoDB.
    """
    if not ObjectId.is_valid(address_id):
        raise HTTPException(status_code=400, detail="Invalid address ID format")

    existing = db.addresses.find_one({"_id": ObjectId(address_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Address not found")

    user_email = existing.get("user_email")
    was_default = existing.get("is_default", False)

    db.addresses.delete_one({"_id": ObjectId(address_id)})

    # If deleted was default, make the most recent remaining address default
    if was_default and user_email:
        next_addr = db.addresses.find_one({"user_email": user_email}, sort=[("created_at", -1)])
        if next_addr:
            db.addresses.update_one({"_id": next_addr["_id"]}, {"$set": {"is_default": True}})

    return {"success": True, "message": "Address deleted successfully"}
