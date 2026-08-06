from fastapi import APIRouter
from typing import List
from app import models
from app.core.database import db

router = APIRouter()

@router.get("")
def read_projects(skip: int = 0, limit: int = 100):
    docs = list(db.projects.find().skip(skip).limit(limit))
    return [models.Project(**doc) for doc in docs]

@router.post("")
def create_project(project: models.Project):
    result = db.projects.insert_one(project.model_dump(by_alias=True, exclude_none=True))
    project.id = str(result.inserted_id)
    return project
