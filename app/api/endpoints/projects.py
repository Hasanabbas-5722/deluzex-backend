from fastapi import APIRouter
from typing import List
from app import models

router = APIRouter()

@router.get("")
async def read_projects(skip: int = 0, limit: int = 100):
    return await models.Project.find_all().skip(skip).limit(limit).to_list()

@router.post("")
async def create_project(project: models.Project):
    await project.insert()
    return project
