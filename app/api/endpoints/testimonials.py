from fastapi import APIRouter
from typing import List
from app import models

router = APIRouter()

@router.get("")
async def read_testimonials(skip: int = 0, limit: int = 100):
    return await models.Testimonial.find_all().skip(skip).limit(limit).to_list()

@router.post("")
async def create_testimonial(testimonial: models.Testimonial):
    await testimonial.insert()
    return testimonial
