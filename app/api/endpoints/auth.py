import re
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from app import models, schemas
from app.api import deps
from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.database import db

router = APIRouter()

@router.post("/register", response_model=schemas.StandardResponse)
def register_user(user_in: schemas.UserRegister):
    # Check if email exists (case-insensitive)
    existing_user = db.users.find_one({"email": {"$regex": f"^{re.escape(str(user_in.email).strip())}$", "$options": "i"}})
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Create user
    hashed_password = get_password_hash(user_in.password)
    new_user = models.User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        hashed_password=hashed_password,
        phone=user_in.phone,
        accept_terms=user_in.accept_terms,
        is_admin=False # Default to false for public registration
    )
    
    result = db.users.insert_one(new_user.model_dump(by_alias=True, exclude_none=True))
    new_user.id = str(result.inserted_id)

    # Log action
    audit_log = models.AuditLog(
        user_id=new_user.id,
        action="USER_REGISTER",
        details="User registered successfully"
    )
    db.audit_logs.insert_one(audit_log.model_dump(by_alias=True, exclude_none=True))

    # Generate token automatically (optional, but good for UX)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(new_user.id), expires_delta=access_token_expires, is_admin=False
    )

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
            is_admin=False,
            created_at=new_user.created_at
        )
    )

@router.post("/login", response_model=schemas.StandardResponse)
def login_user(user_in: schemas.UserLogin):
    user_data = db.users.find_one({"email": {"$regex": f"^{re.escape(str(user_in.email).strip())}$", "$options": "i"}})
    
    if not user_data:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    user = models.User(**user_data)
        
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Log action
    audit_log = models.AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        details="User logged in successfully"
    )
    db.audit_logs.insert_one(audit_log.model_dump(by_alias=True, exclude_none=True))

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires, is_admin=bool(user.is_admin)
    )

    return schemas.StandardResponse(
        success=True,
        message="User logged in successfully.",
        access_token=access_token,
        token_type="bearer",
        data=schemas.UserData(
            id=str(user.id),
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            is_verified=user.is_verified,
            is_admin=bool(user.is_admin),
            created_at=user.created_at
        )
    )

@router.get("/me", response_model=schemas.StandardResponse)
def get_me(current_user: models.User = Depends(deps.get_current_active_user)):
    return schemas.StandardResponse(
        success=True,
        message="User profile retrieved successfully.",
        data=schemas.UserData(
            id=str(current_user.id),
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            is_verified=current_user.is_verified,
            is_admin=bool(current_user.is_admin),
            created_at=current_user.created_at
        )
    )

@router.post("/admin/login", response_model=schemas.StandardResponse)
def login_admin(user_in: schemas.UserLogin):
    user_data = db.users.find_one({"email": {"$regex": f"^{re.escape(str(user_in.email).strip())}$", "$options": "i"}})
    
    if not user_data:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    user = models.User(**user_data)
        
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive account")
    elif not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied. You do not have administrator privileges.")
    
    # Log action
    audit_log = models.AuditLog(
        user_id=user.id,
        action="ADMIN_LOGIN",
        details="Admin logged in successfully"
    )
    db.audit_logs.insert_one(audit_log.model_dump(by_alias=True, exclude_none=True))

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires, is_admin=True
    )

    return schemas.StandardResponse(
        success=True,
        message="Admin logged in successfully.",
        access_token=access_token,
        token_type="bearer",
        data=schemas.UserData(
            id=str(user.id),
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            is_verified=user.is_verified,
            is_admin=True,
            created_at=user.created_at
        )
    )


