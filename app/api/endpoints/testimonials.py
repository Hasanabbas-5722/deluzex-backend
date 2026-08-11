from fastapi import APIRouter
from typing import List
from app import models
from app.core.database import db

router = APIRouter()

@router.get("")
def read_testimonials(skip: int = 0, limit: int = 100):
    docs = list(db.testimonials.find().skip(skip).limit(limit))
    return [models.Testimonial(**doc) for doc in docs]

@router.post("")
def create_testimonial(testimonial: models.Testimonial):
    result = db.testimonials.insert_one(testimonial.model_dump(by_alias=True, exclude_none=True))
    testimonial.id = str(result.inserted_id)
    return testimonial
