import re
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Request
from app import models, schemas
from app.api import deps
from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.database import db
from app.core.audit import record_audit_event

router = APIRouter()

@router.post("/register", response_model=schemas.StandardResponse)
def register_user(user_in: schemas.UserRegister, request: Request):
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
    record_audit_event(
        action="USER_REGISTER",
        action_category="auth",
        actor_id=new_user.id,
        actor_email=new_user.email,
        actor_name=f"{new_user.first_name} {new_user.last_name}".strip(),
        actor_role="Customer",
        target_type="auth",
        target_id=str(new_user.id),
        target_name="User Registration",
        description=f"New user registered: {new_user.email}",
        details="Customer completed registration and accepted terms",
        request=request
    )

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
def login_user(user_in: schemas.UserLogin, request: Request):
    user_data = db.users.find_one({"email": {"$regex": f"^{re.escape(str(user_in.email).strip())}$", "$options": "i"}})
    
    if not user_data:
        record_audit_event(
            action="LOGIN_FAILED",
            action_category="security",
            actor_email=user_in.email,
            actor_role="Guest",
            target_type="auth",
            target_name="Customer Login",
            description=f"Failed login attempt for non-existent email: {user_in.email}",
            status="FAILED",
            request=request
        )
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    user = models.User(**user_data)
        
    if not verify_password(user_in.password, user.hashed_password):
        record_audit_event(
            action="LOGIN_FAILED",
            action_category="security",
            actor_id=user.id,
            actor_email=user.email,
            actor_name=f"{user.first_name} {user.last_name}".strip(),
            actor_role="Customer",
            target_type="auth",
            target_name="Customer Login",
            description=f"Failed login attempt with invalid password for {user.email}",
            status="FAILED",
            request=request
        )
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Log action
    record_audit_event(
        action="USER_LOGIN",
        action_category="auth",
        actor_id=user.id,
        actor_email=user.email,
        actor_name=f"{user.first_name} {user.last_name}".strip() or user.email,
        actor_role="Admin" if user.is_admin else "Customer",
        target_type="auth",
        target_id=str(user.id),
        target_name="Storefront Sign In",
        description=f"User signed in successfully: {user.email}",
        request=request
    )

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
            phone=current_user.phone,
            city=current_user.city,
            country=current_user.country,
            is_verified=current_user.is_verified,
            is_admin=bool(current_user.is_admin),
            created_at=current_user.created_at
        )
    )

@router.patch("/me", response_model=schemas.StandardResponse)
def update_me(
    profile_in: schemas.UserProfileUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    from bson import ObjectId
    update_fields = {}
    if profile_in.first_name is not None:
        update_fields["first_name"] = profile_in.first_name.strip()
    if profile_in.last_name is not None:
        update_fields["last_name"] = profile_in.last_name.strip()
    if profile_in.phone is not None:
        update_fields["phone"] = profile_in.phone.strip()
    if profile_in.city is not None:
        update_fields["city"] = profile_in.city.strip()
    if profile_in.country is not None:
        update_fields["country"] = profile_in.country.strip()
    if profile_in.email is not None and str(profile_in.email).strip().lower() != str(current_user.email).lower():
        clean_email = str(profile_in.email).strip()
        user_oid = ObjectId(current_user.id) if isinstance(current_user.id, str) and ObjectId.is_valid(current_user.id) else current_user.id
        existing = db.users.find_one({
            "email": {"$regex": f"^{re.escape(clean_email)}$", "$options": "i"},
            "_id": {"$ne": user_oid}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Email is already in use by another account.")
        update_fields["email"] = clean_email

    user_oid = ObjectId(current_user.id) if isinstance(current_user.id, str) and ObjectId.is_valid(current_user.id) else current_user.id
    if update_fields:
        db.users.update_one({"_id": user_oid}, {"$set": update_fields})

    updated_doc = db.users.find_one({"_id": user_oid})
    updated_user = models.User(**updated_doc) if updated_doc else current_user

    return schemas.StandardResponse(
        success=True,
        message="Profile updated successfully.",
        data=schemas.UserData(
            id=str(updated_user.id),
            first_name=updated_user.first_name,
            last_name=updated_user.last_name,
            email=updated_user.email,
            phone=updated_user.phone,
            city=updated_user.city,
            country=updated_user.country,
            is_verified=updated_user.is_verified,
            is_admin=bool(updated_user.is_admin),
            created_at=updated_user.created_at
        )
    )

@router.post("/me/password", response_model=schemas.StandardResponse)
def update_password(
    pass_in: schemas.UserPasswordUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    from bson import ObjectId
    if not verify_password(pass_in.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if len(pass_in.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")

    new_hash = get_password_hash(pass_in.new_password)
    user_oid = ObjectId(current_user.id) if isinstance(current_user.id, str) and ObjectId.is_valid(current_user.id) else current_user.id
    db.users.update_one({"_id": user_oid}, {"$set": {"hashed_password": new_hash}})

    return schemas.StandardResponse(
        success=True,
        message="Password updated successfully.",
    )

@router.post("/admin/login", response_model=schemas.StandardResponse)
def login_admin(user_in: schemas.UserLogin, request: Request):
    user_data = db.users.find_one({"email": user_in.email})

    if not user_data:
        record_audit_event(
            action="LOGIN_FAILED",
            action_category="security",
            actor_email=user_in.email,
            actor_role="Guest",
            target_type="auth",
            target_id="admin_portal",
            target_name="Admin Login Gateway",
            description=f"Admin login failed: Email '{user_in.email}' not found",
            status="FAILED",
            request=request
        )
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    user = models.User(**user_data)
        
    if not verify_password(user_in.password, user.hashed_password):
        record_audit_event(
            action="LOGIN_FAILED",
            action_category="security",
            actor_id=user.id,
            actor_email=user.email,
            actor_name=f"{user.first_name} {user.last_name}".strip(),
            actor_role="Admin" if user.is_admin else "Customer",
            target_type="auth",
            target_id="admin_portal",
            target_name="Admin Login Gateway",
            description=f"Admin login failed: Incorrect password for '{user.email}'",
            status="FAILED",
            request=request
        )
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive account")
    elif not user.is_admin:
        record_audit_event(
            action="ACCESS_DENIED",
            action_category="security",
            actor_id=user.id,
            actor_email=user.email,
            actor_name=f"{user.first_name} {user.last_name}".strip(),
            actor_role="Customer",
            target_type="auth",
            target_id="admin_portal",
            target_name="Admin Login Gateway",
            description=f"Non-admin user '{user.email}' attempted to access admin portal",
            status="WARNING",
            request=request
        )
        raise HTTPException(status_code=403, detail="Access denied. You do not have administrator privileges.")
    
    # Log action
    record_audit_event(
        action="ADMIN_LOGIN",
        action_category="auth",
        actor_id=user.id,
        actor_email=user.email,
        actor_name=f"{user.first_name} {user.last_name}".strip() or user.email,
        actor_role="Admin",
        target_type="auth",
        target_id="admin_portal",
        target_name="Admin Control Panel",
        description=f"Administrator '{user.email}' authenticated successfully",
        details="Access granted with full administrator privileges",
        status="SUCCESS",
        request=request
    )

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


