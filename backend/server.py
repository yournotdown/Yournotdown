"""You're Not Down — FastAPI backend."""
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import requests
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Header, Cookie, Depends
from fastapi.responses import StreamingResponse, Response as FastResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict

from storage_client import init_storage, put_object, get_object, APP_NAME
from seed_data import CATEGORIES, CITIES, BUSINESSES

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Mongo
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
ADMIN_EMAILS = [e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]


# ------------- Models -------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class City(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: str
    name: str
    default: bool = False


class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slug: str
    name: str
    emoji: str
    order: int = 0


class Business(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    image_url: str = ""
    image_path: Optional[str] = None  # storage path if uploaded
    website: str = ""
    phone: str = ""
    address: str = ""
    category_slug: str
    city_slug: str = "nashville"
    featured: bool = False
    order: int = 0
    created_at: str = Field(default_factory=now_iso)


class BusinessCreate(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    image_path: Optional[str] = None
    website: str = ""
    phone: str = ""
    address: str = ""
    category_slug: str
    city_slug: str = "nashville"
    featured: bool = False
    order: int = 0


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category_slug: Optional[str] = None
    city_slug: Optional[str] = None
    featured: Optional[bool] = None
    order: Optional[int] = None


class ReorderItem(BaseModel):
    id: str
    order: int


class ReorderPayload(BaseModel):
    items: List[ReorderItem]


class AnalyticsEvent(BaseModel):
    event_type: str
    business_id: Optional[str] = None
    category_slug: Optional[str] = None
    city_slug: Optional[str] = None


class LeadCreate(BaseModel):
    business_id: str
    email: str
    message: str = ""


# ------------- App -------------
app = FastAPI(title="You're Not Down")
api_router = APIRouter(prefix="/api")


@app.on_event("startup")
async def startup():
    # Object storage
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")

    # Seed cities
    for c in CITIES:
        await db.cities.update_one({"slug": c["slug"]}, {"$setOnInsert": c}, upsert=True)
    # Seed categories
    for cat in CATEGORIES:
        await db.categories.update_one({"slug": cat["slug"]}, {"$setOnInsert": cat}, upsert=True)
    # Seed businesses if empty
    biz_count = await db.businesses.count_documents({})
    if biz_count == 0:
        for i, b in enumerate(BUSINESSES):
            doc = {
                "id": str(uuid.uuid4()),
                "name": b["name"],
                "description": b.get("description", ""),
                "image_url": b.get("image_url", ""),
                "image_path": None,
                "website": b.get("website", ""),
                "phone": b.get("phone", ""),
                "address": b.get("address", ""),
                "category_slug": b["category_slug"],
                "city_slug": "nashville",
                "featured": b.get("featured", False),
                "order": i,
                "created_at": now_iso(),
            }
            await db.businesses.insert_one(doc)
        logger.info(f"Seeded {len(BUSINESSES)} businesses")


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ------------- Auth helpers -------------
async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
):
    token = None
    if session_token:
        token = session_token
    elif authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ------------- Public endpoints -------------
@api_router.get("/health")
async def health():
    return {"status": "ok", "ts": now_iso()}


@api_router.get("/cities")
async def list_cities():
    cities = await db.cities.find({}, {"_id": 0}).to_list(100)
    return cities


@api_router.get("/cities/default")
async def default_city():
    c = await db.cities.find_one({"default": True}, {"_id": 0})
    if not c:
        c = await db.cities.find_one({}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="No city configured")
    return c


@api_router.get("/categories")
async def list_categories():
    cats = await db.categories.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return cats


@api_router.get("/businesses")
async def list_businesses(
    city: str = "nashville",
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    limit: int = 200,
):
    q = {"city_slug": city}
    if category and category != "surprise-me":
        q["category_slug"] = category
    if featured is not None:
        q["featured"] = featured
    cursor = db.businesses.find(q, {"_id": 0}).sort([("featured", -1), ("order", 1)]).limit(limit)
    items = await cursor.to_list(limit)
    if category == "surprise-me":
        import random
        random.shuffle(items)
        items = items[:8]
    return items


@api_router.get("/businesses/{business_id}")
async def get_business(business_id: str):
    b = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not b:
        raise HTTPException(status_code=404, detail="Not found")
    return b


# ------------- File serving (public) -------------
@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = get_object(path)
    except requests.HTTPError as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    return FastResponse(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


# ------------- Analytics -------------
@api_router.post("/analytics/track")
async def track_event(event: AnalyticsEvent, request: Request):
    doc = {
        "id": str(uuid.uuid4()),
        "event_type": event.event_type,
        "business_id": event.business_id,
        "category_slug": event.category_slug,
        "city_slug": event.city_slug,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": now_iso(),
    }
    await db.analytics_events.insert_one(doc)
    return {"ok": True}


# ------------- Leads -------------
@api_router.post("/leads")
async def create_lead(lead: LeadCreate):
    doc = lead.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now_iso()
    await db.leads.insert_one(doc)
    return {"ok": True, "id": doc["id"]}


# ------------- Auth -------------
@api_router.post("/auth/session")
async def auth_session(request: Request, response: Response):
    """Exchange Emergent session_id (from URL fragment) for our session_token cookie."""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    r = requests.get(EMERGENT_AUTH_URL, headers={"X-Session-ID": session_id}, timeout=15)
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()
    email = data["email"].lower()
    name = data.get("name", email)
    picture = data.get("picture", "")
    session_token = data["session_token"]

    # Determine role
    is_admin = False
    if ADMIN_EMAILS:
        is_admin = email in ADMIN_EMAILS
    else:
        # bootstrap: first user becomes admin
        any_admin = await db.users.find_one({"role": "admin"}, {"_id": 0})
        if not any_admin:
            is_admin = True

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        update = {"name": name, "picture": picture}
        # Re-evaluate role on every login so the allowlist is the source of truth.
        if ADMIN_EMAILS:
            update["role"] = "admin" if is_admin else "user"
        elif is_admin and existing.get("role") != "admin":
            update["role"] = "admin"
        await db.users.update_one({"user_id": user_id}, {"$set": update})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": "admin" if is_admin else "user",
            "created_at": now_iso(),
        })

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso(),
    })

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user": user}


@api_router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ------------- Admin: businesses -------------
@api_router.get("/admin/businesses")
async def admin_list_businesses(user=Depends(require_admin)):
    items = await db.businesses.find({}, {"_id": 0}).sort([("order", 1)]).to_list(1000)
    return items


@api_router.post("/admin/businesses")
async def admin_create_business(body: BusinessCreate, user=Depends(require_admin)):
    biz = Business(**body.model_dump())
    await db.businesses.insert_one(biz.model_dump())
    return biz.model_dump()


@api_router.patch("/admin/businesses/{business_id}")
async def admin_update_business(business_id: str, body: BusinessUpdate, user=Depends(require_admin)):
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update:
        return await db.businesses.find_one({"id": business_id}, {"_id": 0})
    res = await db.businesses.update_one({"id": business_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return await db.businesses.find_one({"id": business_id}, {"_id": 0})


@api_router.delete("/admin/businesses/{business_id}")
async def admin_delete_business(business_id: str, user=Depends(require_admin)):
    res = await db.businesses.delete_one({"id": business_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api_router.post("/admin/businesses/reorder")
async def admin_reorder(payload: ReorderPayload, user=Depends(require_admin)):
    for it in payload.items:
        await db.businesses.update_one({"id": it.id}, {"$set": {"order": it.order}})
    return {"ok": True, "count": len(payload.items)}


# ------------- Admin: image upload -------------
@api_router.post("/admin/upload")
async def admin_upload(file: UploadFile = File(...), user=Depends(require_admin)):
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    ct = file.content_type or "application/octet-stream"
    if ct not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported content-type: {ct}")
    ext = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg").lower()
    path = f"{APP_NAME}/images/{user['user_id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 8MB)")
    result = put_object(path, data, ct)
    storage_path = result["path"]
    await db.uploaded_files.insert_one({
        "id": str(uuid.uuid4()),
        "storage_path": storage_path,
        "original_filename": file.filename,
        "content_type": ct,
        "size": result.get("size", len(data)),
        "uploaded_by": user["user_id"],
        "is_deleted": False,
        "created_at": now_iso(),
    })
    return {"path": storage_path, "url": f"/api/files/{storage_path}"}


# ------------- Admin: categories -------------
@api_router.get("/admin/categories")
async def admin_list_categories(user=Depends(require_admin)):
    return await db.categories.find({}, {"_id": 0}).sort("order", 1).to_list(100)


# ------------- Admin: analytics -------------
@api_router.get("/admin/analytics/business/{business_id}")
async def admin_business_analytics(business_id: str, days: int = 30, user=Depends(require_admin)):
    biz = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    # Totals per event type (all time)
    pipeline = [
        {"$match": {"business_id": business_id}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
    ]
    rows = await db.analytics_events.aggregate(pipeline).to_list(100)
    totals = {r["_id"]: r["count"] for r in rows}

    # Daily timeline for the last N days
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    tl_pipeline = [
        {"$match": {"business_id": business_id, "timestamp": {"$gte": since}}},
        {
            "$group": {
                "_id": {
                    "day": {"$substr": ["$timestamp", 0, 10]},
                    "event_type": "$event_type",
                },
                "count": {"$sum": 1},
            }
        },
    ]
    tl_rows = await db.analytics_events.aggregate(tl_pipeline).to_list(10000)

    # Build {day: {event_type: count}}
    by_day: dict = {}
    for r in tl_rows:
        day = r["_id"]["day"]
        et = r["_id"]["event_type"]
        by_day.setdefault(day, {})[et] = r["count"]

    # Fill missing days
    timeline = []
    today = datetime.now(timezone.utc).date()
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        row = by_day.get(d, {})
        timeline.append({
            "day": d,
            "business_view": row.get("business_view", 0),
            "website_click": row.get("website_click", 0),
            "phone_click": row.get("phone_click", 0),
            "directions_click": row.get("directions_click", 0),
        })

    return {
        "business": biz,
        "totals": {
            "business_view": totals.get("business_view", 0),
            "website_click": totals.get("website_click", 0),
            "phone_click": totals.get("phone_click", 0),
            "directions_click": totals.get("directions_click", 0),
        },
        "timeline": timeline,
    }


@api_router.get("/admin/analytics/summary")
async def admin_analytics_summary(user=Depends(require_admin)):
    pipeline = [
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
    ]
    rows = await db.analytics_events.aggregate(pipeline).to_list(100)
    summary = {r["_id"]: r["count"] for r in rows}

    # per-category
    cat_pipeline = [
        {"$match": {"event_type": "category_click"}},
        {"$group": {"_id": "$category_slug", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cat_rows = await db.analytics_events.aggregate(cat_pipeline).to_list(100)

    # per-business
    biz_pipeline = [
        {"$match": {"business_id": {"$ne": None}}},
        {"$group": {"_id": {"business_id": "$business_id", "event_type": "$event_type"}, "count": {"$sum": 1}}},
    ]
    biz_rows = await db.analytics_events.aggregate(biz_pipeline).to_list(5000)
    by_biz = {}
    for r in biz_rows:
        bid = r["_id"]["business_id"]
        et = r["_id"]["event_type"]
        by_biz.setdefault(bid, {})[et] = r["count"]

    # attach business names
    biz_ids = list(by_biz.keys())
    businesses = await db.businesses.find({"id": {"$in": biz_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
    name_map = {b["id"]: b["name"] for b in businesses}
    business_breakdown = [
        {"business_id": bid, "name": name_map.get(bid, "(deleted)"), **counts}
        for bid, counts in by_biz.items()
    ]
    business_breakdown.sort(key=lambda x: -(x.get("business_view", 0)))

    total_events = await db.analytics_events.count_documents({})

    return {
        "total_events": total_events,
        "by_event_type": summary,
        "by_category": [{"category_slug": r["_id"], "count": r["count"]} for r in cat_rows],
        "by_business": business_breakdown,
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)
