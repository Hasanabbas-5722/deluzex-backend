import logging
from datetime import datetime
from typing import Optional, Any, Dict
from fastapi import Request
from bson import ObjectId

from app.core.database import db

logger = logging.getLogger("audit")

def get_client_ip(request: Optional[Request]) -> str:
    if not request:
        return "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"

def record_audit_event(
    action: str,
    action_category: str = "general",
    actor_id: Optional[Any] = None,
    actor_email: Optional[str] = None,
    actor_name: Optional[str] = None,
    actor_role: str = "User",
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    target_name: Optional[str] = None,
    description: Optional[str] = None,
    details: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    status: str = "SUCCESS",
) -> Optional[str]:
    """
    Safely insert an audit log record into MongoDB.
    Non-blocking: Never raises an exception that disrupts the caller.
    """
    try:
        ip = get_client_ip(request)
        ua = request.headers.get("user-agent", "") if request else ""

        user_obj_id = None
        if actor_id:
            try:
                user_obj_id = ObjectId(actor_id) if isinstance(actor_id, str) and ObjectId.is_valid(actor_id) else actor_id
            except Exception:
                user_obj_id = None

        doc = {
            "user_id": user_obj_id,
            "actor_email": actor_email,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "action": action,
            "action_category": action_category,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            "target_name": target_name,
            "description": description or details or f"Performed {action}",
            "details": details or description,
            "changes": changes,
            "ip_address": ip,
            "user_agent": ua,
            "status": status,
            "created_at": datetime.utcnow()
        }

        result = db.audit_logs.insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        return None
