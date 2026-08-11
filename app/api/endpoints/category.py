from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from app import models, schemas
router = APIRouter()

@router.post("/register", response_model=schemas.StandardResponse)
async def register_user(user_in: schemas.UserRegister):
    
    return schemas.StandardResponse(
        success=True,
        message="User registered successfully.",
        access_token=access_token,
        token_type="bearer",
        data=schemas.UserData(
            id=str(new_user.id),
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
            is_verified=new_user.is_verified,
            created_at=new_user.created_at
        )
    )
