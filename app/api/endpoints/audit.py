import re
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, status
from bson import ObjectId

from app.core.database import db
from app.schemas.audit import AuditLogResponse, AuditStatsResponse

router = APIRouter()

def serialize_audit_doc(doc: dict) -> dict:
    if not doc:
        return {}
    item = dict(doc)
    item["id"] = str(item.get("_id", ""))
    if "user_id" in item and item["user_id"]:
        item["user_id"] = str(item["user_id"])
    
    # Backwards compatibility with older audit logs
    if not item.get("actor_email") and item.get("user_id"):
        # Attempt to lookup user email
        try:
            u = db.users.find_one({"_id": ObjectId(item["user_id"])})
            if u:
                item["actor_email"] = u.get("email")
                item["actor_name"] = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email")
                item["actor_role"] = "Admin" if u.get("is_admin") else "Customer"
        except Exception:
            pass

    if not item.get("description"):
        item["description"] = item.get("details") or f"Action {item.get('action', 'executed')}"

    if not item.get("action_category"):
        act = item.get("action", "").upper()
        if "LOGIN" in act or "REGISTER" in act or "AUTH" in act:
            item["action_category"] = "auth"
        elif "PRODUCT" in act or "CATEGORY" in act or "CATALOG" in act:
            item["action_category"] = "catalog"
        elif "ORDER" in act or "PAYMENT" in act:
            item["action_category"] = "orders"
        elif "CONTENT" in act or "CMS" in act:
            item["action_category"] = "cms"
        else:
            item["action_category"] = "general"

    return item

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    category: Optional[str] = Query(None, description="Filter category: auth, catalog, orders, cms, security, all"),
    search: Optional[str] = Query(None, description="Search by actor name, email, target, or action"),
    status: Optional[str] = Query(None, description="Filter status: SUCCESS, FAILED"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0)
):
    query: dict = {}

    if category and category.lower() != "all":
        cat = category.lower()
        if cat == "auth":
            query["$or"] = [
                {"action_category": "auth"},
                {"action": {"$regex": "(LOGIN|REGISTER|AUTH)", "$options": "i"}}
            ]
        elif cat == "catalog":
            query["$or"] = [
                {"action_category": "catalog"},
                {"action": {"$regex": "(PRODUCT|CATEGORY|PROJECT|BLOG)", "$options": "i"}}
            ]
        elif cat == "orders":
            query["$or"] = [
                {"action_category": "orders"},
                {"action": {"$regex": "(ORDER|PAYMENT)", "$options": "i"}}
            ]
        elif cat == "cms":
            query["$or"] = [
                {"action_category": "cms"},
                {"action": {"$regex": "(CONTENT|CMS|SETTING)", "$options": "i"}}
            ]
        else:
            query["action_category"] = cat

    if status:
        query["status"] = status.upper()

    if search:
        s_regex = re.escape(search.strip())
        search_filter = {
            "$or": [
                {"actor_email": {"$regex": s_regex, "$options": "i"}},
                {"actor_name": {"$regex": s_regex, "$options": "i"}},
                {"action": {"$regex": s_regex, "$options": "i"}},
                {"target_name": {"$regex": s_regex, "$options": "i"}},
                {"description": {"$regex": s_regex, "$options": "i"}},
                {"details": {"$regex": s_regex, "$options": "i"}},
                {"ip_address": {"$regex": s_regex, "$options": "i"}},
            ]
        }
        if "$or" in query:
            query = {"$and": [query, search_filter]}
        else:
            query.update(search_filter)

    cursor = db.audit_logs.find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = list(cursor)
    return [serialize_audit_doc(d) for d in docs]


@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats():
    total_events = db.audit_logs.count_documents({})
    
    # 24h count
    since_24h = datetime.utcnow() - timedelta(hours=24)
    recent_24h_events = db.audit_logs.count_documents({"created_at": {"$gte": since_24h}})

    # Logins count
    total_logins = db.audit_logs.count_documents({
        "$or": [
            {"action_category": "auth"},
            {"action": {"$regex": "(LOGIN|REGISTER)", "$options": "i"}}
        ]
    })

    # Modifications count
    total_modifications = db.audit_logs.count_documents({
        "$or": [
            {"action_category": {"$in": ["catalog", "orders", "cms"]}},
            {"action": {"$regex": "(_CREATE|_UPDATE|_DELETE)", "$options": "i"}}
        ]
    })

    # Unique actors
    distinct_emails = db.audit_logs.distinct("actor_email")
    distinct_user_ids = db.audit_logs.distinct("user_id")
    unique_actors = set(filter(None, distinct_emails + [str(u) for u in distinct_user_ids]))
    total_unique_actors = max(len(unique_actors), 1)

    # Categories
    cat_counts = {
        "auth": total_logins,
        "catalog": db.audit_logs.count_documents({
            "$or": [
                {"action_category": "catalog"},
                {"action": {"$regex": "(PRODUCT|CATEGORY|PROJECT|BLOG)", "$options": "i"}}
            ]
        }),
        "orders": db.audit_logs.count_documents({
            "$or": [
                {"action_category": "orders"},
                {"action": {"$regex": "(ORDER|PAYMENT)", "$options": "i"}}
            ]
        }),
        "cms": db.audit_logs.count_documents({
            "$or": [
                {"action_category": "cms"},
                {"action": {"$regex": "(CONTENT|CMS)", "$options": "i"}}
            ]
        }),
    }

    return {
        "total_events": total_events,
        "total_logins": total_logins,
        "total_modifications": total_modifications,
        "total_unique_actors": total_unique_actors,
        "recent_24h_events": recent_24h_events,
        "category_counts": cat_counts
    }


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log_detail(log_id: str):
    if not ObjectId.is_valid(log_id):
        raise HTTPException(status_code=400, detail="Invalid log ID")
    doc = db.audit_logs.find_one({"_id": ObjectId(log_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return serialize_audit_doc(doc)


@router.post("/seed-sample")
def seed_sample_audit_logs():
    """
    Seed realistic audit logs showcasing who is entering and who is changing what.
    """
    now = datetime.utcnow()
    sample_events = [
        {
            "actor_email": "hasanabbas@gmail.com",
            "actor_name": "Hasanabbas Chaudhary",
            "actor_role": "Admin",
            "action": "ADMIN_LOGIN",
            "action_category": "auth",
            "target_type": "auth",
            "target_id": "portal",
            "target_name": "Admin Control Panel",
            "description": "Administrator logged in to portal with multi-factor verification",
            "details": "Session initialized from macOS Chrome",
            "ip_address": "103.24.120.15",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0",
            "status": "SUCCESS",
            "created_at": now - timedelta(minutes=12)
        },
        {
            "actor_email": "hasanabbas@gmail.com",
            "actor_name": "Hasanabbas Chaudhary",
            "actor_role": "Admin",
            "action": "PRODUCT_UPDATE",
            "action_category": "catalog",
            "target_type": "product",
            "target_id": "prod_lumina_01",
            "target_name": "Lumina Brass Pendant",
            "description": "Updated price from ₹18,500 to ₹19,800 and updated stock inventory",
            "details": "Price increased +7%, inventory status adjusted to in-stock",
            "changes": {
                "before": {"price": 18500, "in_stock": True, "stock_count": 4},
                "after": {"price": 19800, "in_stock": True, "stock_count": 12}
            },
            "ip_address": "103.24.120.15",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "status": "SUCCESS",
            "created_at": now - timedelta(minutes=45)
        },
        {
            "actor_email": "hasanabbas@gmail.com",
            "actor_name": "Hasanabbas Chaudhary",
            "actor_role": "Admin",
            "action": "ORDER_STATUS_UPDATE",
            "action_category": "orders",
            "target_type": "order",
            "target_id": "ORD-6821-X",
            "target_name": "Order #ORD-6821-X",
            "description": "Marked order status from 'Processing' to 'Shipped' via BlueDart Air",
            "details": "Tracking ID: BLUEDART_99482103",
            "changes": {
                "before": {"status": "processing", "tracking_number": None},
                "after": {"status": "shipped", "tracking_number": "BLUEDART_99482103"}
            },
            "ip_address": "103.24.120.15",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "status": "SUCCESS",
            "created_at": now - timedelta(hours=2, minutes=15)
        },
        {
            "actor_email": "sp894936@gmail.com",
            "actor_name": "Soni Patel",
            "actor_role": "Customer",
            "action": "USER_LOGIN",
            "action_category": "auth",
            "target_type": "auth",
            "target_id": "storefront",
            "target_name": "Deluzex Storefront",
            "description": "Customer signed in from mobile device",
            "details": "Successful OAuth / password credential check",
            "ip_address": "49.36.14.88",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "status": "SUCCESS",
            "created_at": now - timedelta(hours=3, minutes=10)
        },
        {
            "actor_email": "hasanabbas@gmail.com",
            "actor_name": "Hasanabbas Chaudhary",
            "actor_role": "Admin",
            "action": "CATEGORY_CREATE",
            "action_category": "catalog",
            "target_type": "category",
            "target_id": "cat_architectural",
            "target_name": "Architectural Flush Mounts",
            "description": "Created new luxury product category 'Architectural Flush Mounts'",
            "details": "Assigned slug: architectural-flush-mounts with sequence #5",
            "changes": {
                "after": {"name": "Architectural Flush Mounts", "slug": "architectural-flush-mounts", "sequence": 5}
            },
            "ip_address": "103.24.120.15",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "status": "SUCCESS",
            "created_at": now - timedelta(hours=5)
        },
        {
            "actor_email": "unknown@182.70.4.12",
            "actor_name": "Unknown Visitor",
            "actor_role": "Guest",
            "action": "LOGIN_FAILED",
            "action_category": "security",
            "target_type": "auth",
            "target_id": "admin_login",
            "target_name": "Admin Login Gateway",
            "description": "Failed login attempt with invalid administrator credentials",
            "details": "Attempted username: superadmin (invalid password)",
            "ip_address": "182.70.4.12",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/127.0",
            "status": "FAILED",
            "created_at": now - timedelta(hours=8)
        },
        {
            "actor_email": "hasanabbas@gmail.com",
            "actor_name": "Hasanabbas Chaudhary",
            "actor_role": "Admin",
            "action": "CONTENT_UPDATE",
            "action_category": "cms",
            "target_type": "cms",
            "target_id": "home_hero_banner",
            "target_name": "Homepage Hero Headline",
            "description": "Updated hero banner title to 'Sculpted Illumination for Rare Interiors'",
            "details": "CMS content key updated: home_hero_banner",
            "changes": {
                "before": {"title": "Where Lights becomes Design"},
                "after": {"title": "Sculpted Illumination for Rare Interiors"}
            },
            "ip_address": "103.24.120.15",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "status": "SUCCESS",
            "created_at": now - timedelta(days=1, hours=2)
        }
    ]

    result = db.audit_logs.insert_many(sample_events)
    return {"message": "Sample audit logs created successfully", "count": len(result.inserted_ids)}
