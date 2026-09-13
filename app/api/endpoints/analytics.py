import re
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Request, Query, status
from bson import ObjectId

from app.core.database import db
from app.schemas.visitor_log import (
    VisitEventCreate,
    VisitorLogResponse,
    AnalyticsStatsResponse,
    DeviceBreakdown,
    TopPage,
    DailyTrend,
    MemberActivity,
)

router = APIRouter()

def serialize_log(doc: dict) -> dict:
    if not doc:
        return {}
    doc_copy = dict(doc)
    doc_copy["id"] = str(doc_copy.get("_id", ""))
    return doc_copy

def parse_user_agent(ua_str: str, screen_width: Optional[int] = None) -> tuple[str, str, str]:
    ua = ua_str.lower() if ua_str else ""

    # Device
    if screen_width and screen_width <= 768:
        device = "Mobile"
    elif screen_width and screen_width <= 1024:
        device = "Tablet"
    elif "ipad" in ua or "tablet" in ua:
        device = "Tablet"
    elif "mobi" in ua or "android" in ua or "iphone" in ua:
        device = "Mobile"
    else:
        device = "Desktop"

    # Browser
    if "edg" in ua:
        browser = "Edge"
    elif "chrome" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"
    else:
        browser = "Other"

    # OS
    if "windows" in ua:
        os = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os = "macOS"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os = "iOS"
    elif "android" in ua:
        os = "Android"
    elif "linux" in ua:
        os = "Linux"
    else:
        os = "Other"

    return device, browser, os

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


@router.post("/visit", status_code=status.HTTP_201_CREATED)
def record_visitor(event: VisitEventCreate, request: Request):
    """
    Record a page visit event into MongoDB.
    """
    ip = get_client_ip(request)
    device, browser, os_name = parse_user_agent(event.user_agent or "", event.screen_width)

    # Don't log admin pages into visitor logs
    if event.path.startswith("/admin"):
        return {"success": True, "skipped": True}

    doc = {
        "visitor_id": event.visitor_id,
        "session_id": event.session_id,
        "path": event.path or "/",
        "referrer": event.referrer or "",
        "ip_address": ip,
        "user_agent": event.user_agent or "",
        "device_type": device,
        "browser": browser,
        "os": os_name,
        "is_member": bool(event.is_member),
        "user_email": event.user_email.strip().lower() if event.user_email else None,
        "user_name": event.user_name.strip() if event.user_name else None,
        "user_id": str(event.user_id) if event.user_id else None,
        "created_at": datetime.utcnow(),
    }

    res = db.visitor_logs.insert_one(doc)
    return {"success": True, "id": str(res.inserted_id)}


@router.get("/stats", response_model=AnalyticsStatsResponse)
def get_analytics_stats():
    """
    Get aggregated analytics: total views, unique visitors, member visits,
    active now, device breakdown, top visited pages, and 7-day trend.
    """
    total_views = db.visitor_logs.count_documents({})

    # Unique visitors by visitor_id
    unique_visitors_list = db.visitor_logs.distinct("visitor_id")
    total_unique = len(unique_visitors_list)

    # Registered members visited
    member_emails = db.visitor_logs.distinct("user_email", {"is_member": True, "user_email": {"$ne": None}})
    total_members = len(member_emails)
    total_guests = max(0, total_unique - total_members)

    # Active now (visited within last 15 minutes)
    fifteen_mins_ago = datetime.utcnow() - timedelta(minutes=15)
    active_now_list = db.visitor_logs.distinct("visitor_id", {"created_at": {"$gte": fifteen_mins_ago}})
    active_now = len(active_now_list)

    # Device breakdown
    desktop_count = db.visitor_logs.count_documents({"device_type": "Desktop"})
    mobile_count = db.visitor_logs.count_documents({"device_type": "Mobile"})
    tablet_count = db.visitor_logs.count_documents({"device_type": "Tablet"})

    # Top visited pages
    pipeline_pages = [
        {"$group": {"_id": "$path", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 6},
    ]
    top_pages_agg = list(db.visitor_logs.aggregate(pipeline_pages))
    top_pages = [TopPage(path=p["_id"] or "/", views=p["count"]) for p in top_pages_agg]

    # Daily trends (last 7 days)
    daily_trends = []
    for i in range(6, -1, -1):
        day_start = (datetime.utcnow() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_str = day_start.strftime("%b %d")

        views_count = db.visitor_logs.count_documents({"created_at": {"$gte": day_start, "$lt": day_end}})
        unique_count = len(db.visitor_logs.distinct("visitor_id", {"created_at": {"$gte": day_start, "$lt": day_end}}))
        members_count = db.visitor_logs.count_documents({"is_member": True, "created_at": {"$gte": day_start, "$lt": day_end}})

        daily_trends.append(DailyTrend(
            date=day_str,
            total_views=views_count,
            unique_visitors=unique_count,
            member_views=members_count,
        ))

    return AnalyticsStatsResponse(
        total_page_views=total_views,
        total_unique_visitors=total_unique,
        total_member_visitors=total_members,
        total_guest_visitors=total_guests,
        active_now=active_now,
        devices=DeviceBreakdown(desktop=desktop_count, mobile=mobile_count, tablet=tablet_count),
        top_pages=top_pages,
        daily_trends=daily_trends,
    )


@router.get("/visitors", response_model=List[VisitorLogResponse])
def get_visitor_logs(
    filter: str = Query("all", description="all, members, guests"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get detailed visitor logs with filtering and search.
    """
    query = {}
    if filter == "members":
        query["is_member"] = True
    elif filter == "guests":
        query["is_member"] = False

    if search and search.strip():
        term = re.escape(search.strip())
        query["$or"] = [
            {"user_email": {"$regex": term, "$options": "i"}},
            {"user_name": {"$regex": term, "$options": "i"}},
            {"path": {"$regex": term, "$options": "i"}},
            {"ip_address": {"$regex": term, "$options": "i"}},
            {"visitor_id": {"$regex": term, "$options": "i"}},
        ]

    docs = list(
        db.visitor_logs.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [VisitorLogResponse(**serialize_log(d)) for d in docs]


@router.get("/members", response_model=List[MemberActivity])
def get_member_visitors():
    """
    Get all registered members who have visited the website,
    with their visit frequency, last seen time, and last visited path.
    """
    pipeline = [
        {"$match": {"is_member": True, "user_email": {"$ne": None}}},
        {"$sort": {"created_at": -1}},
        {
            "$group": {
                "_id": "$user_email",
                "name": {"$first": "$user_name"},
                "total_visits": {"$sum": 1},
                "last_seen": {"$first": "$created_at"},
                "last_path": {"$first": "$path"},
            }
        },
        {"$sort": {"last_seen": -1}},
        {"$limit": 50},
    ]

    agg = list(db.visitor_logs.aggregate(pipeline))
    result = []
    for item in agg:
        email = item["_id"]
        name = item.get("name") or email.split("@")[0].capitalize()
        result.append(MemberActivity(
            email=email,
            name=name,
            total_visits=item["total_visits"],
            last_seen=item["last_seen"],
            last_path=item.get("last_path") or "/",
        ))

    return result


@router.post("/seed-sample")
def seed_sample_traffic():
    """
    Seed initial realistic visitor traffic if database is fresh.
    """
    if db.visitor_logs.count_documents({}) > 0:
        return {"message": "Visitor logs already exist", "count": db.visitor_logs.count_documents({})}

    now = datetime.utcnow()
    sample_pages = ["/", "/shop", "/about", "/projects", "/blogs", "/dashboard/wishlist", "/dashboard/orders"]
    
    sample_events = [
        {"visitor_id": "vis_01", "session_id": "ses_01", "path": "/", "ip_address": "103.24.120.15", "device_type": "Desktop", "browser": "Chrome", "os": "macOS", "is_member": True, "user_email": "hasanabbasc@gmail.com", "user_name": "Hasanabbas Chaudhary", "created_at": now - timedelta(minutes=2)},
        {"visitor_id": "vis_01", "session_id": "ses_01", "path": "/shop", "ip_address": "103.24.120.15", "device_type": "Desktop", "browser": "Chrome", "os": "macOS", "is_member": True, "user_email": "hasanabbasc@gmail.com", "user_name": "Hasanabbas Chaudhary", "created_at": now - timedelta(minutes=1)},
        {"visitor_id": "vis_02", "session_id": "ses_02", "path": "/", "ip_address": "49.36.18.92", "device_type": "Mobile", "browser": "Safari", "os": "iOS", "is_member": True, "user_email": "sp894936@gmail.com", "user_name": "Soni Patel", "created_at": now - timedelta(minutes=8)},
        {"visitor_id": "vis_02", "session_id": "ses_02", "path": "/dashboard/address", "ip_address": "49.36.18.92", "device_type": "Mobile", "browser": "Safari", "os": "iOS", "is_member": True, "user_email": "sp894936@gmail.com", "user_name": "Soni Patel", "created_at": now - timedelta(minutes=5)},
        {"visitor_id": "vis_03", "session_id": "ses_03", "path": "/shop", "ip_address": "157.34.88.204", "device_type": "Desktop", "browser": "Edge", "os": "Windows", "is_member": False, "created_at": now - timedelta(minutes=14)},
        {"visitor_id": "vis_04", "session_id": "ses_04", "path": "/projects", "ip_address": "182.72.102.34", "device_type": "Mobile", "browser": "Chrome", "os": "Android", "is_member": False, "created_at": now - timedelta(minutes=25)},
        {"visitor_id": "vis_05", "session_id": "ses_05", "path": "/blogs", "ip_address": "106.51.72.18", "device_type": "Desktop", "browser": "Firefox", "os": "macOS", "is_member": False, "created_at": now - timedelta(hours=1)},
        {"visitor_id": "vis_06", "session_id": "ses_06", "path": "/", "ip_address": "115.99.14.80", "device_type": "Tablet", "browser": "Safari", "os": "iOS", "is_member": True, "user_email": "abidalipatel170@gmail.com", "user_name": "Aabidali Patel", "created_at": now - timedelta(hours=2)},
        {"visitor_id": "vis_07", "session_id": "ses_07", "path": "/shop", "ip_address": "14.139.122.45", "device_type": "Desktop", "browser": "Chrome", "os": "Windows", "is_member": False, "created_at": now - timedelta(hours=3)},
    ]

    for d in range(1, 7):
        past = now - timedelta(days=d)
        for idx in range(4):
            sample_events.append({
                "visitor_id": f"vis_hist_{d}_{idx}",
                "session_id": f"ses_hist_{d}_{idx}",
                "path": sample_pages[idx % len(sample_pages)],
                "ip_address": f"103.{d * 10}.{idx * 20}.11",
                "device_type": "Desktop" if idx % 2 == 0 else "Mobile",
                "browser": "Chrome" if idx % 2 == 0 else "Safari",
                "os": "macOS" if idx % 2 == 0 else "iOS",
                "is_member": idx == 0,
                "user_email": "hasanabbasc@gmail.com" if idx == 0 else None,
                "user_name": "Hasanabbas Chaudhary" if idx == 0 else None,
                "created_at": past - timedelta(hours=idx * 2),
            })

    db.visitor_logs.insert_many(sample_events)
    return {"message": "Sample visitor logs seeded successfully", "count": len(sample_events)}
