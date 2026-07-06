"""You're Not Down — FastAPI backend."""
import asyncio
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import requests
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Header, Cookie, Depends
from fastapi.responses import StreamingResponse, Response as FastResponse
from dotenv import load_dotenv
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict

from google_places_photos import (
    describe_google_places_request_error,
    fetch_google_places_photo,
    google_places_photo_media_url,
)
from featured_live_music import (
    FEATURED_LIVE_MUSIC_SLOT,
    active_featured_live_music_event,
    featured_live_music_business,
    featured_live_music_step_event,
    normalize_live_music_event_mode,
)
from ticketmaster_events import (
    TicketmasterClient,
    api_sync_response,
    attach_event_to_step,
    business_supports_live_music_event,
    date_range_sync_report,
    eligible_public_businesses,
    eligible_city_events,
    eligible_ticketmaster_music_events,
    event_upsert,
    events_by_business_id,
    expiration_cleanup_query,
    itinerary_event_pick,
    local_today,
    supported_city_config,
    validate_apply_confirmation,
)
from storage_client import init_storage, put_object, get_object, APP_NAME
from itinerary_buckets import annotate_itinerary_buckets
from tonight_move_sponsorship import (
    TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
    active_tonight_move_sponsorship,
)
from seed_data import (
    CATEGORIES,
    CITIES,
    BUSINESSES,
    CATEGORY_MIGRATIONS,
    REMOVED_CATEGORY_SLUGS,
    canonical_category_slug,
    default_slots_for_category,
)
from mood_system import MOOD_WEIGHTS, SPONSOR_MULTIPLIERS, NAME_TO_TAGS, TAGS as VALID_TAGS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Mongo clients connect lazily. Keep process startup tolerant so Railway can
# serve liveness diagnostics while an external database is temporarily down.
MONGO_URL = os.environ.get("MONGO_URL", "").strip()
DB_NAME = os.environ.get("DB_NAME", "").strip()
ALLOW_EMPTY_DB_BOOTSTRAP = os.environ.get("ALLOW_EMPTY_DB_BOOTSTRAP", "").strip().lower() in {
    "1", "true", "yes", "on",
}
client = AsyncIOMotorClient(
    MONGO_URL or "mongodb://invalid:27017",
    serverSelectionTimeoutMS=3000 if MONGO_URL else 1000,
    connectTimeoutMS=3000,
    socketTimeoutMS=5000,
)
db = client[DB_NAME or "unconfigured"]
startup_maintenance_task = None
startup_maintenance_status = "pending"
STARTUP_MAINTENANCE_ATTEMPTS = 3
EVENT_START_GRACE_MINUTES = max(0, int(os.environ.get("EVENT_START_GRACE_MINUTES", "60")))

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


SLOT_LABELS = [
    {"slot": "dinner", "label": "Dinner", "emoji": "🍽️", "number": 1},
    {"slot": "drinks", "label": "Drinks", "emoji": "🍸", "number": 2},
    {"slot": "entertainment", "label": "Entertainment", "emoji": "🎵", "number": 3},
    {"slot": "late-night", "label": "Late Night", "emoji": "🌃", "number": 4},
]

# Sponsor tier weights for weighted-random selection
SPONSOR_WEIGHTS = {"none": 1, "silver": 5, "gold": 10, "platinum": 20}
VALID_TIERS = set(SPONSOR_WEIGHTS.keys())
VALID_IMPORT_STATUSES = {"pending", "approved", "rejected"}

class Business(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    sponsor_tier: str = "none"
    slots: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    brand_fit_score: Optional[int] = None
    import_override_reason: Optional[str] = None
    google_place_id: Optional[str] = None
    normalized_name_address: Optional[str] = None
    google_rating: Optional[float] = None
    google_user_rating_count: Optional[int] = None
    google_maps_url: str = ""
    google_photo_names: List[str] = Field(default_factory=list)
    google_types: List[str] = Field(default_factory=list)
    imported_status: str = "approved"
    import_source: Optional[str] = None
    imported_at: Optional[str] = None
    import_queries: List[str] = Field(default_factory=list)
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
    sponsor_tier: str = "none"
    slots: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    brand_fit_score: Optional[int] = None
    import_override_reason: Optional[str] = None
    google_place_id: Optional[str] = None
    normalized_name_address: Optional[str] = None
    google_rating: Optional[float] = None
    google_user_rating_count: Optional[int] = None
    google_maps_url: str = ""
    google_photo_names: List[str] = Field(default_factory=list)
    google_types: List[str] = Field(default_factory=list)
    imported_status: str = "approved"
    import_source: Optional[str] = None
    imported_at: Optional[str] = None
    import_queries: List[str] = Field(default_factory=list)
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
    sponsor_tier: Optional[str] = None
    slots: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    brand_fit_score: Optional[int] = None
    import_override_reason: Optional[str] = None
    google_place_id: Optional[str] = None
    normalized_name_address: Optional[str] = None
    google_rating: Optional[float] = None
    google_user_rating_count: Optional[int] = None
    google_maps_url: Optional[str] = None
    google_photo_names: Optional[List[str]] = None
    google_types: Optional[List[str]] = None
    imported_status: Optional[str] = None
    import_source: Optional[str] = None
    imported_at: Optional[str] = None
    import_queries: Optional[List[str]] = None
    order: Optional[int] = None


class ReorderItem(BaseModel):
    id: str
    order: int


class ReorderPayload(BaseModel):
    items: List[ReorderItem]


class BulkImportReviewPayload(BaseModel):
    ids: List[str]
    imported_status: str


class AnalyticsEvent(BaseModel):
    event_type: str
    business_id: Optional[str] = None
    category_slug: Optional[str] = None
    city_slug: Optional[str] = None
    vibe: Optional[str] = None
    itinerary_id: Optional[str] = None


class CityEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    city_slug: str
    venue_name: str
    venue_business_id: Optional[str] = None
    external_event_id: str
    source: str
    title: str
    performers: List[str] = Field(default_factory=list)
    starts_at: Optional[str] = None
    local_date: str
    local_time: Optional[str] = None
    ticket_url: str = ""
    image_url: str = ""
    status: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class TicketmasterSyncPayload(BaseModel):
    city: str = "nashville"
    days: int = Field(default=2, ge=1, le=7)
    apply: bool = False
    confirm: str = ""


class AdminFeaturedLiveMusicEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: Optional[str] = None
    city_slug: str = "nashville"
    active: bool = False
    slot: str = FEATURED_LIVE_MUSIC_SLOT
    title: str = ""
    venue_name: str = ""
    description: str = ""
    local_date: str = ""
    local_time: str = ""
    active_from: str = ""
    active_until: str = ""
    image_url: str = ""
    ticket_url: str = ""
    cta_label: str = "Buy Tickets"
    priority: int = 0
    internal_notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AdminTonightMoveSponsorship(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: Optional[str] = None
    city_slug: str = "nashville"
    active: bool = False
    placement: str = TONIGHT_MOVE_SPONSORSHIP_PLACEMENT
    sponsor_name: str = ""
    sponsor_logo_url: str = ""
    sponsor_url: str = ""
    tagline: str = ""
    active_from: str = ""
    active_until: str = ""
    priority: int = 0
    internal_notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LeadCreate(BaseModel):
    business_id: str
    email: str
    message: str = ""


class SaveItineraryRequest(BaseModel):
    email: str
    city_slug: str = "nashville"
    vibe: str = ""
    source_itinerary_id: Optional[str] = None
    steps: List[dict] = Field(default_factory=list)
    locked_slots: List[str] = Field(default_factory=list)


# ------------- App -------------
app = FastAPI(title="You're Not Down")
api_router = APIRouter(prefix="/api")


async def run_startup_maintenance():
    global startup_maintenance_status
    if not MONGO_URL or not DB_NAME:
        startup_maintenance_status = "skipped-unconfigured"
        logger.warning("Skipping startup maintenance: MONGO_URL and DB_NAME must both be configured")
        return

    startup_maintenance_status = "running"
    logger.info("Starting Mongo startup maintenance for configured database %s", DB_NAME)
    for attempt in range(1, STARTUP_MAINTENANCE_ATTEMPTS + 1):
        try:
            await db.command("ping")
            business_count = await db.businesses.count_documents({})
            if business_count == 0 and not ALLOW_EMPTY_DB_BOOTSTRAP:
                startup_maintenance_status = "skipped-empty-database"
                logger.warning(
                    "Skipping startup maintenance for database %s with an empty business catalog. "
                    "Set ALLOW_EMPTY_DB_BOOTSTRAP=true only when intentional.",
                    DB_NAME,
                )
                return

            await _apply_startup_maintenance()
            startup_maintenance_status = "complete"
            logger.info("Mongo startup maintenance complete")
            return
        except Exception as exc:
            if attempt == STARTUP_MAINTENANCE_ATTEMPTS:
                startup_maintenance_status = "deferred"
                logger.warning("Mongo startup maintenance deferred after %s attempts: %s", attempt, exc)
                return
            logger.warning(
                "Mongo startup maintenance attempt %s/%s failed; retrying: %s",
                attempt,
                STARTUP_MAINTENANCE_ATTEMPTS,
                exc,
            )
            await asyncio.sleep(5)


async def _apply_startup_maintenance():
    await db.businesses.create_index("google_place_id", unique=True, sparse=True)
    await db.businesses.create_index("normalized_name_address", unique=True, sparse=True)
    await db.city_events.create_index([("city_slug", 1), ("local_date", 1)])
    await db.city_events.create_index([("source", 1), ("external_event_id", 1)], unique=True)

    # Seed cities
    for c in CITIES:
        await db.cities.update_one({"slug": c["slug"]}, {"$setOnInsert": c}, upsert=True)

    # --- Category migration (idempotent) ---
    # 1. Migrate businesses out of removed categories
    for old_slug, new_slug in CATEGORY_MIGRATIONS.items():
        await db.businesses.update_many(
            {"category_slug": old_slug},
            {"$set": {"category_slug": new_slug}},
        )
    # 2. Delete removed categories
    if REMOVED_CATEGORY_SLUGS:
        await db.categories.delete_many({"slug": {"$in": REMOVED_CATEGORY_SLUGS}})

    # 3. Upsert the canonical category set (always overwrite name/emoji/order to keep branding fresh)
    for cat in CATEGORIES:
        await db.categories.update_one(
            {"slug": cat["slug"]},
            {"$set": cat},
            upsert=True,
        )

    # Seed businesses if empty
    biz_count = await db.businesses.count_documents({})
    if biz_count == 0:
        for i, b in enumerate(BUSINESSES):
            cat = canonical_category_slug(b["category_slug"])
            doc = {
                "id": str(uuid.uuid4()),
                "name": b["name"],
                "description": b.get("description", ""),
                "image_url": b.get("image_url", ""),
                "image_path": None,
                "website": b.get("website", ""),
                "phone": b.get("phone", ""),
                "address": b.get("address", ""),
                "category_slug": cat,
                "city_slug": "nashville",
                "featured": b.get("featured", False),
                "sponsor_tier": "gold" if b.get("featured") else "none",
                "slots": default_slots_for_category(cat),
                "imported_status": "approved",
                "order": i,
                "created_at": now_iso(),
            }
            await db.businesses.insert_one(doc)
        logger.info(f"Seeded {len(BUSINESSES)} businesses")

    # --- Business field backfill (idempotent) ---
    # Backfill `sponsor_tier` from legacy `featured` flag
    await db.businesses.update_many(
        {"sponsor_tier": {"$exists": False}, "featured": True},
        {"$set": {"sponsor_tier": "gold"}},
    )
    await db.businesses.update_many(
        {"sponsor_tier": {"$exists": False}},
        {"$set": {"sponsor_tier": "none"}},
    )
    # Existing catalog rows predate imports and remain publicly approved.
    await db.businesses.update_many(
        {"imported_status": {"$exists": False}},
        {"$set": {"imported_status": "approved"}},
    )
    # Backfill missing or empty `slots` from the canonical category default.
    # This repairs rows created before legacy category seeds were canonicalized.
    async for biz in db.businesses.find(
        {"$or": [{"slots": {"$exists": False}}, {"slots": []}]},
        {"_id": 0, "id": 1, "category_slug": 1},
    ):
        default_slots = default_slots_for_category(biz.get("category_slug", ""))
        if default_slots:
            await db.businesses.update_one({"id": biz["id"]}, {"$set": {"slots": default_slots}})

    # Backfill `tags` for seeded businesses (idempotent — match by name, only if tags missing/empty)
    async for biz in db.businesses.find(
        {"$or": [{"tags": {"$exists": False}}, {"tags": []}]},
        {"_id": 0, "id": 1, "name": 1},
    ):
        tags = NAME_TO_TAGS.get(biz.get("name", ""))
        if tags:
            await db.businesses.update_one({"id": biz["id"]}, {"$set": {"tags": tags}})
        else:
            # Ensure field exists so the field is queryable later
            await db.businesses.update_one(
                {"id": biz["id"], "tags": {"$exists": False}},
                {"$set": {"tags": []}},
            )


@app.on_event("startup")
async def startup():
    global startup_maintenance_task
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as exc:
        logger.warning("Storage initialization deferred: %s", exc)

    startup_maintenance_task = asyncio.create_task(run_startup_maintenance())
    logger.info("Application startup complete; Mongo maintenance is running in the background")


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


# ------------- Itinerary engine -------------
import random


class ItineraryRequest(BaseModel):
    vibe: Optional[str] = None
    city: str = "nashville"
    exclude_ids: List[str] = Field(default_factory=list)
    exclude_event_ids: List[str] = Field(default_factory=list)
    live_music_event_mode: str = "normal"
    locked_steps: Dict[str, dict] = Field(default_factory=dict)


def _relevance_score(business: dict, vibe: Optional[str]) -> float:
    """Mood-aware relevance score for a single business.

    Returns max(0.05, 1 + sum_of_tag_weights). The 0.05 floor lets heavily-
    penalized businesses *technically* appear (so sponsor tiers still matter)
    but makes them ~100× less likely than a relevant non-sponsor.
    """
    if not vibe or vibe not in MOOD_WEIGHTS:
        return 1.0
    weights = MOOD_WEIGHTS[vibe]
    score = 1.0 + sum(weights.get(t, 0) for t in (business.get("tags") or []))
    return max(0.05, score)


def _weighted_pick(
    candidates: list,
    exclude_ids: set,
    vibe: Optional[str],
) -> Optional[dict]:
    """Pick one business using mood-relevance × sponsor-tier weighted random.

    If everything is excluded, relax the exclusion filter so the slot still fills."""
    pool = [b for b in candidates if b["id"] not in exclude_ids]
    if not pool:
        pool = candidates
    if not pool:
        return None
    weights = []
    for b in pool:
        relevance = _relevance_score(b, vibe)
        sponsor_mult = SPONSOR_MULTIPLIERS.get(b.get("sponsor_tier", "none"), 1)
        weights.append(relevance * sponsor_mult)
    return random.choices(pool, weights=weights, k=1)[0]


def _slot_meta(slot: str) -> dict:
    for label in SLOT_LABELS:
        if label["slot"] == slot:
            return label
    return {
        "slot": slot,
        "number": 0,
        "label": slot.replace("-", " ").title() if slot else "",
        "emoji": "✨",
    }


def _safe_locked_step(slot: str, snapshot: Optional[dict]) -> dict:
    meta = _slot_meta(slot)
    raw_step = snapshot if isinstance(snapshot, dict) else {}
    raw_business = raw_step.get("business")
    business = raw_business if isinstance(raw_business, dict) else {}
    safe_business = {
        "id": business.get("id", ""),
        "name": business.get("name", ""),
        "description": business.get("description", ""),
        "image_url": business.get("image_url", ""),
        "image_path": business.get("image_path"),
        "website": business.get("website", ""),
        "phone": business.get("phone", ""),
        "address": business.get("address", ""),
        "google_photo_names": business.get("google_photo_names") or [],
        "sponsor_tier": business.get("sponsor_tier", "none"),
        **business,
    }
    step = {
        "slot": slot or raw_step.get("slot", ""),
        "number": raw_step.get("number", meta["number"]),
        "label": raw_step.get("label", meta["label"]),
        "emoji": raw_step.get("emoji", meta["emoji"]),
        "business": safe_business,
    }
    if "relevance_score" in raw_step:
        step["relevance_score"] = raw_step.get("relevance_score")
    raw_event = raw_step.get("event")
    if isinstance(raw_event, dict):
        step["event"] = dict(raw_event)
    return step


def _safe_saved_itinerary_steps(steps: List[dict]) -> list[dict]:
    safe_steps = []
    for index, step in enumerate(steps or []):
        slot = ""
        if isinstance(step, dict):
            slot = step.get("slot", "")
        if not slot and index < len(SLOT_LABELS):
            slot = SLOT_LABELS[index]["slot"]
        safe_steps.append(_safe_locked_step(slot, step))
    return safe_steps


def _valid_email(value: str) -> bool:
    email = (value or "").strip()
    if not email or " " in email or "@" not in email:
        return False
    local_part, _, domain = email.partition("@")
    if not local_part or not domain or "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return False
    return True


def _email_delivery_result() -> dict:
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    resend_from_email = os.environ.get("RESEND_FROM_EMAIL", "").strip()
    if not resend_api_key or not resend_from_email:
        return {
            "delivery_status": "provider_unconfigured",
            "delivery_error": "",
            "email_provider": "",
            "provider_message_id": "",
            "sent_at": None,
        }
    return {
        "delivery_status": "pending",
        "delivery_error": "",
        "email_provider": "resend",
        "provider_message_id": "",
        "sent_at": None,
    }


def _saved_itinerary_email_subject(doc: dict) -> str:
    city = (doc.get("city_slug") or "tonight").replace("-", " ").title()
    return f"YourNotDown: Tonight's Move for {city}"


def _saved_itinerary_step_lines(step: dict) -> list[str]:
    business = step.get("business") or {}
    event = step.get("event") or {}
    lines = [
        f'{step.get("number", "")}. {step.get("label", "Step")} - {business.get("name", "Unknown spot")}'.strip(),
    ]
    if business.get("address"):
        lines.append(f'Address: {business["address"]}')
    if business.get("website"):
        lines.append(f'Website: {business["website"]}')
    if event.get("title"):
        lines.append(f'Event: {event["title"]}')
    if event.get("local_time"):
        lines.append(f'Time: {event["local_time"]}')
    if event.get("ticket_url"):
        lines.append(f'Tickets: {event["ticket_url"]}')
    return lines


def _saved_itinerary_email_content(doc: dict) -> tuple[str, str]:
    city = (doc.get("city_slug") or "nashville").replace("-", " ").title()
    vibe = doc.get("vibe", "")
    site_url = (
        os.environ.get("PUBLIC_SITE_URL", "").strip()
        or os.environ.get("FRONTEND_PUBLIC_URL", "").strip()
    )
    text_parts = [
        "YourNotDown / Tonight's Move",
        "",
        f"City: {city}",
        f"Vibe: {vibe}",
        "",
    ]
    html_parts = [
        "<html><body style=\"font-family:Arial,sans-serif;background:#0b0b0b;color:#ffffff;padding:24px;\">",
        "<div style=\"max-width:640px;margin:0 auto;\">",
        "<div style=\"font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:#c6ff00;\">YourNotDown</div>",
        "<h1 style=\"margin:12px 0 8px;font-size:32px;line-height:1;\">Tonight's Move</h1>",
        f"<p style=\"margin:0 0 16px;color:#cfcfcf;\">City: {city}<br />Vibe: {vibe}</p>",
    ]
    for step in doc.get("steps") or []:
        business = step.get("business") or {}
        event = step.get("event") or {}
        text_parts.extend(_saved_itinerary_step_lines(step))
        text_parts.append("")
        html_parts.append("<div style=\"border-top:1px solid rgba(255,255,255,0.12);padding-top:16px;margin-top:16px;\">")
        html_parts.append(
            f"<div style=\"font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#c6ff00;\">"
            f"{step.get('number', '')}. {step.get('label', 'Step')}</div>"
        )
        html_parts.append(f"<h2 style=\"margin:8px 0 8px;font-size:24px;\">{business.get('name', 'Unknown spot')}</h2>")
        if business.get("address"):
            html_parts.append(f"<p style=\"margin:0 0 8px;color:#cfcfcf;\">{business['address']}</p>")
        if business.get("website"):
            html_parts.append(
                f"<p style=\"margin:0 0 8px;\"><a style=\"color:#c6ff00;\" href=\"{business['website']}\">{business['website']}</a></p>"
            )
        if event.get("title"):
            html_parts.append(f"<p style=\"margin:8px 0 0;color:#ffffff;\">Event: {event['title']}</p>")
        if event.get("local_time"):
            html_parts.append(f"<p style=\"margin:4px 0 0;color:#cfcfcf;\">Time: {event['local_time']}</p>")
        if event.get("ticket_url"):
            html_parts.append(
                f"<p style=\"margin:4px 0 0;\"><a style=\"color:#c6ff00;\" href=\"{event['ticket_url']}\">Buy Tickets</a></p>"
            )
        html_parts.append("</div>")
    if site_url:
        text_parts.append(f"YourNotDown: {site_url}")
        html_parts.append(f"<p style=\"margin-top:24px;\"><a style=\"color:#c6ff00;\" href=\"{site_url}\">Open YourNotDown</a></p>")
    text_parts.append("Built with YourNotDown")
    html_parts.append("<p style=\"margin-top:24px;color:#cfcfcf;\">Built with YourNotDown</p>")
    html_parts.append("</div></body></html>")
    return "\n".join(text_parts), "".join(html_parts)


def _send_resend_email(doc: dict) -> dict:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_email = os.environ.get("RESEND_FROM_EMAIL", "").strip()
    reply_to = os.environ.get("RESEND_REPLY_TO", "").strip()
    if not api_key or not from_email:
        return _email_delivery_result()

    text_body, html_body = _saved_itinerary_email_content(doc)
    payload = {
        "from": from_email,
        "to": [doc["email"]],
        "subject": _saved_itinerary_email_subject(doc),
        "html": html_body,
        "text": text_body,
    }
    if reply_to:
        payload["reply_to"] = [reply_to]
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json() if response.content else {}
    return {
        "delivery_status": "sent",
        "delivery_error": "",
        "email_provider": "resend",
        "provider_message_id": data.get("id", ""),
        "sent_at": now_iso(),
    }


async def _today_city_events(city: str) -> list[dict]:
    try:
        event_date = local_today(city)
    except ValueError:
        return []
    rows = await db.city_events.find(
        {
            "city_slug": city,
            "local_date": event_date,
        },
        {"_id": 0},
    ).sort("starts_at", 1).to_list(1000)
    return eligible_city_events(rows, city, grace_minutes=EVENT_START_GRACE_MINUTES)


async def _public_businesses(
    city: str = "nashville",
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    limit: int = 200,
    require_slots: bool = False,
    event_rows: Optional[list[dict]] = None,
) -> list[dict]:
    q = {"city_slug": city, "imported_status": "approved"}
    if category and category != "surprise-me":
        q["category_slug"] = category
    if featured is not None:
        q["featured"] = featured
    if require_slots:
        q["slots"] = {"$ne": []}
    cursor = db.businesses.find(q, {"_id": 0}).sort([("featured", -1), ("order", 1)]).limit(limit)
    businesses = await cursor.to_list(limit)
    return eligible_public_businesses(businesses, event_rows if event_rows is not None else await _today_city_events(city))


async def _public_business(business_id: str) -> Optional[dict]:
    business = await db.businesses.find_one(
        {"id": business_id, "imported_status": "approved"},
        {"_id": 0},
    )
    if not business:
        return None
    event_rows = await _today_city_events(business.get("city_slug", "nashville"))
    eligible = eligible_public_businesses([business], event_rows)
    return eligible[0] if eligible else None


async def _active_featured_live_music_event(city: str) -> Optional[dict]:
    rows = await db.admin_featured_events.find(
        {"city_slug": city, "slot": FEATURED_LIVE_MUSIC_SLOT},
        {"_id": 0},
    ).sort([("priority", -1), ("updated_at", -1)]).to_list(200)
    return active_featured_live_music_event(rows, city)


async def _active_tonight_move_sponsorship(city: str) -> Optional[dict]:
    rows = await db.admin_sponsorships.find(
        {"city_slug": city, "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT},
        {"_id": 0},
    ).sort([("priority", -1), ("updated_at", -1)]).to_list(200)
    return active_tonight_move_sponsorship(rows, city)


@api_router.post("/itinerary/generate")
async def generate_itinerary(req: ItineraryRequest, request: Request):
    """Build a 4-step 'Tonight's Move' itinerary tuned to the user's mood."""
    event_rows = await _today_city_events(req.city)
    all_biz = await _public_businesses(req.city, limit=2000, require_slots=True, event_rows=event_rows)
    today_events_by_business = events_by_business_id(event_rows)
    eligible_music_events = eligible_ticketmaster_music_events(event_rows, all_biz)
    live_music_event_mode = normalize_live_music_event_mode(req.live_music_event_mode)
    featured_live_music = await _active_featured_live_music_event(req.city)
    tonight_move_sponsorship = await _active_tonight_move_sponsorship(req.city)

    by_slot: dict = {}
    for b in all_biz:
        for slot in b.get("slots", []):
            by_slot.setdefault(slot, []).append(b)

    exclude = set(req.exclude_ids)
    exclude_event_ids = set(req.exclude_event_ids)
    locked_steps_by_slot = {
        slot: _safe_locked_step(slot, step)
        for slot, step in (req.locked_steps or {}).items()
        if slot
    }
    chosen_ids: set = {
        business_id
        for business_id in [
            ((step.get("business") or {}).get("id"))
            for step in locked_steps_by_slot.values()
        ]
        if business_id
    }
    steps = []
    for label in SLOT_LABELS:
        locked_step = locked_steps_by_slot.get(label["slot"])
        if locked_step:
            steps.append(locked_step)
            continue
        candidates = by_slot.get(label["slot"], [])
        pick = None
        forced_event = None
        if label["slot"] == "entertainment":
            event_candidates = [business for business in candidates if business_supports_live_music_event(business)]
            if featured_live_music:
                pick = featured_live_music_business(featured_live_music)
                forced_event = featured_live_music_step_event(featured_live_music)
            elif live_music_event_mode in {"ticketmaster", "ticketmaster_preferred"}:
                pick, forced_event = itinerary_event_pick(
                    event_candidates,
                    eligible_music_events,
                    exclude | chosen_ids,
                    exclude_event_ids,
                )
            if not pick:
                pick = _weighted_pick(event_candidates or candidates, exclude | chosen_ids, req.vibe)
        elif not pick:
            pick = _weighted_pick(candidates, exclude | chosen_ids, req.vibe)
        if pick:
            chosen_ids.add(pick["id"])
            step = {
                "slot": label["slot"],
                "number": label["number"],
                "label": label["label"],
                "emoji": label["emoji"],
                "business": pick,
                "relevance_score": round(_relevance_score(pick, req.vibe), 2),
            }
            if forced_event:
                steps.append({**step, "event": forced_event})
            elif label["slot"] == "entertainment":
                steps.append(step)
            else:
                steps.append(attach_event_to_step(step, today_events_by_business))

    itin_id = str(uuid.uuid4())
    itinerary = {
        "id": itin_id,
        "vibe": req.vibe,
        "city": req.city,
        "steps": steps,
        "tonight_move_sponsorship": tonight_move_sponsorship,
        "generated_at": now_iso(),
    }

    # Persist itinerary + analytics events
    await db.itineraries.insert_one({
        **itinerary,
        "ip": request.client.host if request.client else None,
    })
    appearance_docs = []
    for step in steps:
        b = step["business"]
        appearance_docs.append({
            "id": str(uuid.uuid4()),
            "event_type": "business_appearance",
            "business_id": b["id"],
            "sponsor_tier": b.get("sponsor_tier", "none"),
            "city_slug": req.city,
            "vibe": req.vibe,
            "itinerary_id": itin_id,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": now_iso(),
        })
    if appearance_docs:
        await db.analytics_events.insert_many(appearance_docs)
    await db.analytics_events.insert_one({
        "id": str(uuid.uuid4()),
        "event_type": "itinerary_generated",
        "city_slug": req.city,
        "vibe": req.vibe,
        "itinerary_id": itin_id,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": now_iso(),
    })

    return itinerary


# ------------- Public endpoints -------------
@api_router.get("/health")
async def health():
    return {
        "status": "ok",
        "ts": now_iso(),
        "mongo_configured": bool(MONGO_URL and DB_NAME),
        "startup_maintenance": startup_maintenance_status,
    }


@api_router.get("/ready")
async def ready():
    if not MONGO_URL or not DB_NAME:
        return {"status": "degraded", "mongo": "unconfigured"}
    try:
        await asyncio.wait_for(db.command("ping"), timeout=2.0)
    except Exception as exc:
        logger.warning("Mongo readiness ping failed: %s", exc)
        return {"status": "degraded", "mongo": "down"}
    return {"status": "ready", "mongo": "up"}


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
    items = await _public_businesses(city, category=category, featured=featured, limit=limit)
    if category == "surprise-me":
        import random
        random.shuffle(items)
        items = items[:8]
    return items


@api_router.get("/businesses/{business_id}")
async def get_business(business_id: str):
    b = await _public_business(business_id)
    if not b:
        raise HTTPException(status_code=404, detail="Not found")
    return b


# ------------- City events -------------
@api_router.get("/events/today")
async def list_today_events(city: str = "nashville"):
    return await _today_city_events(city)


# ------------- Google Places photos (public proxy) -------------
@api_router.get("/google-places/photo")
async def google_places_photo(photo_name: Optional[str] = None, business_id: Optional[str] = None):
    if bool(photo_name) == bool(business_id):
        raise HTTPException(status_code=400, detail="Provide exactly one of photo_name or business_id")
    if photo_name:
        try:
            google_places_photo_media_url(photo_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        business = await db.businesses.find_one(
            {"google_photo_names": photo_name, "imported_status": "approved"},
            {"_id": 1},
        )
        if not business:
            raise HTTPException(status_code=404, detail="Google Places photo not found")
    else:
        business = await db.businesses.find_one(
            {"id": business_id, "imported_status": "approved"},
            {"_id": 0, "google_photo_names": 1},
        )
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        photo_names = business.get("google_photo_names") or []
        if not photo_names:
            raise HTTPException(status_code=404, detail="Business has no Google Places photos")
        photo_name = photo_names[0]
    upstream = None
    try:
        upstream = await run_in_threadpool(fetch_google_places_photo, photo_name)
        upstream.raise_for_status()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error("Google Places photo proxy is unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Google Places photo proxy is unavailable")
    except requests.RequestException as e:
        if upstream is not None:
            upstream.close()
        logger.warning(
            "Google Places photo request failed: %s",
            describe_google_places_request_error(e),
        )
        raise HTTPException(status_code=502, detail="Google Places photo request failed")
    return StreamingResponse(
        upstream.iter_content(chunk_size=64 * 1024),
        media_type=upstream.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
        background=BackgroundTask(upstream.close),
    )


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
        "vibe": event.vibe,
        "itinerary_id": event.itinerary_id,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": now_iso(),
    }
    # Stamp sponsor tier on click events for easy reporting
    if event.business_id and event.event_type in {
        "business_click", "website_click", "phone_click", "directions_click",
    }:
        biz = await db.businesses.find_one({"id": event.business_id}, {"_id": 0, "sponsor_tier": 1})
        if biz:
            doc["sponsor_tier"] = biz.get("sponsor_tier", "none")
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


@api_router.post("/itinerary/save")
async def save_itinerary(payload: SaveItineraryRequest):
    email = (payload.email or "").strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email.")

    safe_steps = _safe_saved_itinerary_steps(payload.steps)
    safe_locked_slots = [
        slot for slot in payload.locked_slots
        if slot in {label["slot"] for label in SLOT_LABELS}
    ]
    delivery = _email_delivery_result()
    doc = {
        "id": str(uuid.uuid4()),
        "source_itinerary_id": payload.source_itinerary_id,
        "city_slug": payload.city_slug,
        "vibe": payload.vibe,
        "email": email,
        "steps": safe_steps,
        "locked_slots": safe_locked_slots,
        "delivery_channel": "email",
        "delivery_status": delivery["delivery_status"],
        "delivery_error": delivery["delivery_error"],
        "email_provider": delivery["email_provider"],
        "provider_message_id": delivery["provider_message_id"],
        "created_at": now_iso(),
        "sent_at": delivery["sent_at"],
    }
    await db.saved_itineraries.insert_one(doc)
    if doc["delivery_status"] != "provider_unconfigured":
        try:
            delivery = await run_in_threadpool(_send_resend_email, doc)
        except requests.RequestException as exc:
            delivery = {
                "delivery_status": "failed",
                "delivery_error": str(exc),
                "email_provider": "resend",
                "provider_message_id": "",
                "sent_at": None,
            }
        await db.saved_itineraries.update_one(
            {"id": doc["id"]},
            {"$set": {
                "delivery_status": delivery["delivery_status"],
                "delivery_error": delivery["delivery_error"],
                "email_provider": delivery["email_provider"],
                "provider_message_id": delivery["provider_message_id"],
                "sent_at": delivery["sent_at"],
            }},
        )
        doc.update(delivery)
    return {
        "ok": True,
        "id": doc["id"],
        "delivery_status": doc["delivery_status"],
        "delivery_error": doc["delivery_error"],
        "email_provider": doc["email_provider"],
        "provider_message_id": doc["provider_message_id"],
        "sent_at": doc["sent_at"],
    }


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
async def admin_list_businesses(imported_status: Optional[str] = None, user=Depends(require_admin)):
    if imported_status and imported_status not in VALID_IMPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid imported_status")
    query = {"imported_status": imported_status} if imported_status else {}
    items = await db.businesses.find(query, {"_id": 0}).sort([("order", 1)]).to_list(5000)
    return annotate_itinerary_buckets(items)


@api_router.get("/admin/featured-events/live-music")
async def admin_get_featured_live_music_event(city: str = "nashville", user=Depends(require_admin)):
    active = await _active_featured_live_music_event(city)
    if active:
        return active
    fallback = await db.admin_featured_events.find_one(
        {"city_slug": city, "slot": FEATURED_LIVE_MUSIC_SLOT},
        {"_id": 0},
        sort=[("updated_at", -1)],
    )
    return fallback or {}


@api_router.put("/admin/featured-events/live-music")
async def admin_save_featured_live_music_event(body: AdminFeaturedLiveMusicEvent, user=Depends(require_admin)):
    timestamp = now_iso()
    event_id = body.id or str(uuid.uuid4())
    record = {
        **body.model_dump(),
        "id": event_id,
        "slot": FEATURED_LIVE_MUSIC_SLOT,
        "updated_at": timestamp,
        "created_at": body.created_at or timestamp,
    }
    await db.admin_featured_events.update_one({"id": event_id}, {"$set": record}, upsert=True)
    return record


@api_router.delete("/admin/featured-events/live-music/{event_id}")
async def admin_delete_featured_live_music_event(event_id: str, user=Depends(require_admin)):
    result = await db.admin_featured_events.delete_one({"id": event_id, "slot": FEATURED_LIVE_MUSIC_SLOT})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api_router.get("/admin/sponsorships/tonight-move")
async def admin_get_tonight_move_sponsorship(city: str = "nashville", user=Depends(require_admin)):
    active = await _active_tonight_move_sponsorship(city)
    if active:
        return active
    fallback = await db.admin_sponsorships.find_one(
        {"city_slug": city, "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT},
        {"_id": 0},
        sort=[("updated_at", -1)],
    )
    return fallback or {}


@api_router.put("/admin/sponsorships/tonight-move")
async def admin_save_tonight_move_sponsorship(body: AdminTonightMoveSponsorship, user=Depends(require_admin)):
    timestamp = now_iso()
    sponsorship_id = body.id or str(uuid.uuid4())
    record = {
        **body.model_dump(),
        "id": sponsorship_id,
        "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
        "updated_at": timestamp,
        "created_at": body.created_at or timestamp,
    }
    await db.admin_sponsorships.update_one({"id": sponsorship_id}, {"$set": record}, upsert=True)
    return record


@api_router.delete("/admin/sponsorships/tonight-move/{sponsorship_id}")
async def admin_delete_tonight_move_sponsorship(sponsorship_id: str, user=Depends(require_admin)):
    result = await db.admin_sponsorships.delete_one(
        {"id": sponsorship_id, "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api_router.post("/admin/businesses")
async def admin_create_business(body: BusinessCreate, user=Depends(require_admin)):
    if body.sponsor_tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid sponsor_tier; must be one of {sorted(VALID_TIERS)}")
    if body.imported_status not in VALID_IMPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid imported_status")
    biz = Business(**body.model_dump())
    # Auto-sync legacy `featured` from sponsor_tier
    biz.featured = biz.sponsor_tier != "none"
    await db.businesses.insert_one(biz.model_dump())
    return biz.model_dump()


@api_router.patch("/admin/businesses/{business_id}")
async def admin_update_business(business_id: str, body: BusinessUpdate, user=Depends(require_admin)):
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if "sponsor_tier" in update and update["sponsor_tier"] not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid sponsor_tier; must be one of {sorted(VALID_TIERS)}")
    if "imported_status" in update and update["imported_status"] not in VALID_IMPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid imported_status")
    if "sponsor_tier" in update:
        update["featured"] = update["sponsor_tier"] != "none"
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


@api_router.post("/admin/businesses/import-review")
async def admin_bulk_import_review(payload: BulkImportReviewPayload, user=Depends(require_admin)):
    if payload.imported_status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Bulk review status must be approved or rejected")
    if not payload.ids:
        return {"ok": True, "count": 0}
    res = await db.businesses.update_many(
        {"id": {"$in": payload.ids}},
        {"$set": {"imported_status": payload.imported_status}},
    )
    return {"ok": True, "count": res.modified_count}


@api_router.post("/admin/events/ticketmaster-sync")
async def admin_ticketmaster_sync(payload: TicketmasterSyncPayload, user=Depends(require_admin)):
    try:
        validate_apply_confirmation(payload.apply, payload.confirm)
        supported_city_config(payload.city)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    businesses = await db.businesses.find(
        {"city_slug": payload.city, "imported_status": "approved"},
        {"_id": 0, "id": 1, "name": 1},
    ).to_list(5000)
    try:
        report = await run_in_threadpool(
            date_range_sync_report,
            TicketmasterClient(),
            businesses,
            payload.city,
            payload.days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.warning("Ticketmaster sync failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Ticketmaster sync failed")

    if not payload.apply:
        return api_sync_response(report)

    upserted = 0
    modified = 0
    for document in report["events"]:
        selector, update = event_upsert(document)
        result = await db.city_events.update_one(selector, update, upsert=True)
        upserted += int(result.upserted_id is not None)
        modified += result.modified_count
    cleanup_query = expiration_cleanup_query(payload.city)
    cleanup = await db.city_events.delete_many(cleanup_query)
    return api_sync_response(report, {
        "upserted": upserted,
        "modified": modified,
        "expired_deleted": cleanup.deleted_count,
        "expiration_cutoff": cleanup_query["local_date"]["$lt"],
    })


@api_router.get("/admin/businesses/import-summary")
async def admin_import_summary(user=Depends(require_admin)):
    rows = await db.businesses.aggregate([
        {"$group": {"_id": "$imported_status", "count": {"$sum": 1}}},
    ]).to_list(10)
    counts = {row["_id"] or "approved": row["count"] for row in rows}
    return {
        status: counts.get(status, 0)
        for status in ["pending", "approved", "rejected"]
    }


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


@api_router.get("/admin/tags")
async def admin_list_tags(user=Depends(require_admin)):
    """Canonical tag vocabulary the recommendation engine knows about."""
    return {"tags": list(VALID_TAGS)}


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
            "business_appearance": row.get("business_appearance", 0),
            "business_view": row.get("business_view", 0),
            "website_click": row.get("website_click", 0),
            "phone_click": row.get("phone_click", 0),
            "directions_click": row.get("directions_click", 0),
        })

    return {
        "business": biz,
        "totals": {
            "business_appearance": totals.get("business_appearance", 0),
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

    # attach business names + sponsor tier
    biz_ids = list(by_biz.keys())
    businesses = await db.businesses.find(
        {"id": {"$in": biz_ids}}, {"_id": 0, "id": 1, "name": 1, "sponsor_tier": 1}
    ).to_list(1000)
    name_map = {b["id"]: b["name"] for b in businesses}
    tier_map = {b["id"]: b.get("sponsor_tier", "none") for b in businesses}
    business_breakdown = [
        {
            "business_id": bid,
            "name": name_map.get(bid, "(deleted)"),
            "sponsor_tier": tier_map.get(bid, "none"),
            **counts,
        }
        for bid, counts in by_biz.items()
    ]
    business_breakdown.sort(
        key=lambda x: -(x.get("business_appearance", 0) + x.get("business_view", 0))
    )

    # Sponsor performance: aggregate appearances + clicks by tier
    sponsor_pipeline = [
        {"$match": {"sponsor_tier": {"$ne": None}}},
        {"$group": {
            "_id": {"tier": "$sponsor_tier", "event_type": "$event_type"},
            "count": {"$sum": 1},
        }},
    ]
    sp_rows = await db.analytics_events.aggregate(sponsor_pipeline).to_list(1000)
    by_tier: dict = {}
    for r in sp_rows:
        tier = r["_id"]["tier"] or "none"
        et = r["_id"]["event_type"]
        by_tier.setdefault(tier, {})[et] = r["count"]
    sponsor_performance = []
    for tier in ["platinum", "gold", "silver", "none"]:
        if tier in by_tier:
            sponsor_performance.append({"tier": tier, **by_tier[tier]})

    total_events = await db.analytics_events.count_documents({})

    return {
        "total_events": total_events,
        "by_event_type": summary,
        "by_category": [{"category_slug": r["_id"], "count": r["count"]} for r in cat_rows],
        "by_business": business_breakdown,
        "sponsor_performance": sponsor_performance,
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)
