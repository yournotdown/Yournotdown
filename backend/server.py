"""You're Not Down — FastAPI backend."""
import asyncio
import hashlib
import os
import logging
import re
import secrets
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
    normalize_google_places_photo_width,
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
from saved_itinerary_email import (
    saved_itinerary_email_content,
    saved_itinerary_email_subject,
)
from business_owner_email import (
    business_owner_invite_email_content,
    business_owner_invite_email_subject,
)

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
ADMIN_SESSION_DAYS = 7
ADMIN_SESSION_COOKIE = "session_token"
BUSINESS_OWNER_INVITE_DAYS = 7
BUSINESS_OWNER_SESSION_DAYS = 30
BUSINESS_OWNER_SESSION_COOKIE = "business_owner_session"
RATE_LIMIT_ANALYTICS_TRACK_PER_IP = 300
RATE_LIMIT_ITINERARY_GENERATE_PER_IP = 60
RATE_LIMIT_ITINERARY_SAVE_PER_IP = 10
RATE_LIMIT_ITINERARY_SAVE_PER_EMAIL = 5
RATE_LIMIT_OWNER_INVITE_PER_ADMIN = 10
RATE_LIMIT_OWNER_INVITE_PER_IP = 10
RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_ADMIN = 30
RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_IP = 30
RATE_LIMIT_BUSINESS_CLAIM_PER_IP = 20
RATE_LIMIT_MINUTE_SECONDS = 60
RATE_LIMIT_HOUR_SECONDS = 60 * 60
# In-process only. Multi-instance deployments need a shared store such as Redis.
RATE_LIMIT_STATE: Dict[str, List[float]] = {}


# ------------- Models -------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cors_allowed_origins() -> List[str]:
    origins = {
        "https://www.yournotdown.com",
        "https://yournotdown.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
    for value in (
        os.environ.get("PUBLIC_SITE_URL", "").strip(),
        os.environ.get("FRONTEND_PUBLIC_URL", "").strip(),
    ):
        if value:
            origins.add(value.rstrip("/"))
    return sorted(origins)


def _client_ip(request: Optional[Request]) -> str:
    if not request:
        return ""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        for part in forwarded_for.split(","):
            candidate = part.strip()
            if candidate:
                return candidate
    if request.client and request.client.host:
        return request.client.host
    return ""


def _rate_limit_subject(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return "unknown"
    return _hash_token(normalized)


def _should_bypass_rate_limit(request: Optional[Request]) -> bool:
    ip = _client_ip(request)
    return ip in {"127.0.0.1", "::1", "localhost"}


def _consume_rate_limit(
    key: str,
    *,
    limit: int,
    window_seconds: int,
    now_ts: Optional[float] = None,
    state: Optional[Dict[str, List[float]]] = None,
) -> tuple[bool, int]:
    if limit <= 0 or window_seconds <= 0:
        return True, 0
    store = state if state is not None else RATE_LIMIT_STATE
    current_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    cutoff = current_ts - window_seconds
    hits = [ts for ts in store.get(key, []) if ts > cutoff]
    if len(hits) >= limit:
        store[key] = hits
        retry_after = max(1, int(window_seconds - (current_ts - hits[0])) + 1)
        return False, retry_after
    hits.append(current_ts)
    store[key] = hits
    return True, 0


def _rate_limit_error(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later.",
        headers={"Retry-After": str(max(1, int(retry_after or 1)))},
    )


def _require_rate_limit_key(
    bucket_name: str,
    subject: str,
    *,
    limit: int,
    window_seconds: int,
    now_ts: Optional[float] = None,
) -> None:
    bucket_key = f"{bucket_name}:{_rate_limit_subject(subject)}"
    allowed, retry_after = _consume_rate_limit(
        bucket_key,
        limit=limit,
        window_seconds=window_seconds,
        now_ts=now_ts,
    )
    if not allowed:
        raise _rate_limit_error(retry_after)


def _require_ip_rate_limit(
    bucket_name: str,
    request: Optional[Request],
    *,
    limit: int,
    window_seconds: int,
    now_ts: Optional[float] = None,
) -> None:
    if _should_bypass_rate_limit(request):
        return
    _require_rate_limit_key(
        bucket_name,
        _client_ip(request) or "unknown",
        limit=limit,
        window_seconds=window_seconds,
        now_ts=now_ts,
    )


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
    visitor_id: Optional[str] = None
    qr_slug: Optional[str] = None
    business_id: Optional[str] = None
    category_slug: Optional[str] = None
    slot: Optional[str] = None
    city_slug: Optional[str] = None
    vibe: Optional[str] = None
    itinerary_id: Optional[str] = None
    saved_itinerary_id: Optional[str] = None
    source_itinerary_id: Optional[str] = None
    source_surface: Optional[str] = None
    event_id: Optional[str] = None
    event_source: Optional[str] = None


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
    visitor_id: Optional[str] = None
    qr_slug: Optional[str] = None
    city_slug: str = "nashville"
    vibe: str = ""
    source_itinerary_id: Optional[str] = None
    steps: List[dict] = Field(default_factory=list)
    locked_slots: List[str] = Field(default_factory=list)
    marketing_opt_in: bool = False


class BusinessOwnerInviteCreate(BaseModel):
    email: str


class BusinessOwnerClaimRequest(BaseModel):
    token: str


class HotelQrCodeCreate(BaseModel):
    name: str
    city_slug: str = "nashville"
    hotel_name: str = ""
    location_label: str = ""
    notes: str = ""


class HotelQrCodeUpdate(BaseModel):
    name: Optional[str] = None
    city_slug: Optional[str] = None
    hotel_name: Optional[str] = None
    location_label: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


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
    await db.businesses.create_index([("id", 1)])
    await db.businesses.create_index([("city_slug", 1), ("imported_status", 1), ("featured", -1), ("order", 1)])
    await db.businesses.create_index([("city_slug", 1), ("imported_status", 1), ("category_slug", 1), ("featured", -1), ("order", 1)])
    await db.businesses.create_index([("city_slug", 1), ("imported_status", 1), ("sponsor_tier", 1)])

    await db.city_events.create_index([("city_slug", 1), ("local_date", 1)])
    await db.city_events.create_index([("source", 1), ("external_event_id", 1)], unique=True)
    await db.city_events.create_index([("city_slug", 1), ("source", 1), ("local_date", 1)])
    await db.city_events.create_index([("venue_business_id", 1), ("local_date", 1)])

    await db.analytics_events.create_index([("event_type", 1), ("timestamp", -1)])
    await db.analytics_events.create_index([("business_id", 1), ("timestamp", -1)])
    await db.analytics_events.create_index([("city_slug", 1), ("timestamp", -1)])
    await db.analytics_events.create_index([("vibe", 1), ("timestamp", -1)])
    await db.analytics_events.create_index([("slot", 1), ("timestamp", -1)])
    await db.analytics_events.create_index([("qr_slug", 1), ("timestamp", -1)])
    await db.analytics_events.create_index([("visitor_id", 1), ("timestamp", -1)])

    await db.itineraries.create_index([("id", 1)])
    await db.itineraries.create_index([("city", 1), ("vibe", 1), ("generated_at", -1)])

    await db.saved_itineraries.create_index([("email", 1), ("created_at", -1)])
    await db.saved_itineraries.create_index([("visitor_id", 1), ("created_at", -1)])
    await db.saved_itineraries.create_index([("qr_slug", 1), ("created_at", -1)])
    await db.saved_itineraries.create_index([("source_itinerary_id", 1)])

    await db.audience_contacts.create_index("email_normalized", unique=True)
    await db.audience_contacts.create_index([("visitor_id", 1)])
    await db.audience_contacts.create_index([("marketing_opt_in", 1), ("last_saved_at", -1)])
    await db.audience_contacts.create_index([("last_saved_at", -1)])

    await db.visitor_profiles.create_index("visitor_id", unique=True)
    await db.visitor_profiles.create_index([("email_normalized", 1)])
    await db.visitor_profiles.create_index([("last_seen_at", -1)])
    await db.visitor_profiles.create_index([("saved_itinerary_count", 1)])

    await db.hotel_qr_codes.create_index("slug", unique=True)
    await db.hotel_qr_codes.create_index([("id", 1)])
    await db.hotel_qr_codes.create_index([("city_slug", 1), ("active", 1), ("created_at", -1)])

    await db.business_owner_invites.create_index([("token_hash", 1)])
    await db.business_owner_invites.create_index([("business_id", 1), ("status", 1), ("created_at", -1)])
    await db.business_owner_invites.create_index([("business_id", 1), ("email", 1), ("status", 1)])
    await db.business_owner_invites.create_index([("expires_at", 1)])

    await db.business_owners.create_index([("owner_id", 1)])
    await db.business_owners.create_index([("business_id", 1), ("status", 1)])
    await db.business_owners.create_index([("business_id", 1), ("email", 1)])

    await db.business_owner_sessions.create_index([("session_token_hash", 1)])
    await db.business_owner_sessions.create_index([("owner_id", 1), ("revoked_at", 1)])
    await db.business_owner_sessions.create_index([("business_id", 1), ("revoked_at", 1)])
    await db.business_owner_sessions.create_index([("expires_at", 1)])

    await db.user_sessions.create_index([("session_token_hash", 1)])
    await db.user_sessions.create_index([("user_id", 1), ("expires_at", 1)])
    await db.user_sessions.create_index([("expires_at", 1)])

    await db.admin_featured_events.create_index([("city_slug", 1), ("slot", 1), ("priority", -1), ("updated_at", -1)])
    await db.admin_sponsorships.create_index([("city_slug", 1), ("placement", 1), ("priority", -1), ("updated_at", -1)])

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

    token_hash = _hash_token(token)
    sess = await db.user_sessions.find_one({"session_token_hash": token_hash}, {"_id": 0})
    if not sess:
        legacy_sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
        if legacy_sess:
            sess = legacy_sess
            await db.user_sessions.update_one(
                {"user_id": legacy_sess["user_id"], "session_token": token},
                {
                    "$set": {
                        "session_token_hash": token_hash,
                        "updated_at": now_iso(),
                    },
                    "$unset": {
                        "session_token": "",
                    },
                },
            )
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.user_sessions.delete_many({
            "$or": [
                {"session_token_hash": token_hash},
                {"session_token": token},
            ]
        })
        raise HTTPException(status_code=401, detail="Session expired")

    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    await db.user_sessions.update_many(
        {
            "$or": [
                {"session_token_hash": token_hash},
                {"session_token": token},
            ]
        },
        {"$set": {"last_seen_at": now_iso()}},
    )
    return user


async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_current_business_owner(
    request: Request,
    business_owner_session: Optional[str] = Cookie(None),
):
    token = business_owner_session
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = _hash_token(token)
    session = await db.business_owner_sessions.find_one({"session_token_hash": token_hash}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    if session.get("revoked_at"):
        raise HTTPException(status_code=401, detail="Session revoked")

    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    owner = await db.business_owners.find_one({"owner_id": session["owner_id"]}, {"_id": 0})
    if not owner or owner.get("status") != "active":
        raise HTTPException(status_code=403, detail="Owner access revoked")

    business = await db.businesses.find_one({"id": owner["business_id"]}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    await db.business_owner_sessions.update_one(
        {"session_id": session["session_id"]},
        {"$set": {"last_seen_at": now_iso()}},
    )
    return {"owner": owner, "business": business, "session": session}


# ------------- Itinerary engine -------------
import random


class ItineraryRequest(BaseModel):
    vibe: Optional[str] = None
    city: str = "nashville"
    exclude_ids: List[str] = Field(default_factory=list)
    exclude_ids_by_slot: Dict[str, List[str]] = Field(default_factory=dict)
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
    historical_exclude_ids: Optional[set] = None,
) -> Optional[dict]:
    """Pick one business using mood-relevance × sponsor-tier weighted random.

    Keep hard excludes in place, but relax slot-history excludes if needed so the
    slot can still fill after a reroll session exhausts the local pool."""
    pool = [b for b in candidates if b["id"] not in exclude_ids]
    historical_exclude_ids = historical_exclude_ids or set()
    if historical_exclude_ids:
        filtered_pool = [b for b in pool if b["id"] not in historical_exclude_ids]
        if filtered_pool:
            pool = filtered_pool
    if not pool:
        pool = [b for b in candidates if b["id"] not in exclude_ids]
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


def _hash_token(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _new_owner_token() -> str:
    return secrets.token_urlsafe(32)


def _business_owner_claim_url(token: str) -> str:
    base = (
        os.environ.get("PUBLIC_SITE_URL", "").strip()
        or os.environ.get("FRONTEND_PUBLIC_URL", "").strip()
        or "https://www.yournotdown.com"
    ).rstrip("/")
    return f"{base}/business/claim/{token}"


def _owner_invite_delivery_result() -> dict:
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


def _owner_invite_safe(invite: Optional[dict]) -> Optional[dict]:
    if not invite:
        return None
    return {
        "id": invite.get("id"),
        "business_id": invite.get("business_id"),
        "email": invite.get("email", ""),
        "status": invite.get("status", ""),
        "sent_at": invite.get("sent_at"),
        "expires_at": invite.get("expires_at"),
        "accepted_at": invite.get("accepted_at"),
        "revoked_at": invite.get("revoked_at"),
        "created_at": invite.get("created_at"),
        "delivery_status": invite.get("delivery_status", ""),
        "delivery_error": invite.get("delivery_error", ""),
        "email_provider": invite.get("email_provider", ""),
    }


def _owner_safe(owner: Optional[dict], business: Optional[dict] = None) -> Optional[dict]:
    if not owner:
        return None
    payload = {
        "owner_id": owner.get("owner_id"),
        "business_id": owner.get("business_id"),
        "email": owner.get("email", ""),
        "status": owner.get("status", "active"),
        "invite_id": owner.get("invite_id"),
        "created_at": owner.get("created_at"),
        "last_login_at": owner.get("last_login_at"),
    }
    if business:
        payload["business"] = {
            "id": business.get("id"),
            "name": business.get("name", ""),
            "city_slug": business.get("city_slug", ""),
            "sponsor_tier": business.get("sponsor_tier", "none"),
        }
    return payload


async def _owner_access_summary(business_id: str) -> dict:
    latest_invite = await db.business_owner_invites.find(
        {"business_id": business_id, "status": "pending"},
        {"_id": 0},
    ).sort([("created_at", -1)]).to_list(1)
    owner = await db.business_owners.find_one({"business_id": business_id, "status": "active"}, {"_id": 0})
    invite = latest_invite[0] if latest_invite else None
    return {
        "business_id": business_id,
        "invite": _owner_invite_safe(invite),
        "owner": _owner_safe(owner),
        "portal_access_active": bool(owner and owner.get("status") == "active"),
    }


BUSINESS_SCOPED_EVENT_TYPES = {
    "business_appearance",
    "business_view",
    "business_click",
    "website_click",
    "phone_click",
    "directions_click",
    "ticket_click",
    "step_locked",
    "saved_itinerary_business",
}

LEADERBOARD_METRIC_EVENT_KEYS = [
    "business_appearance",
    "business_view",
    "step_locked",
    "saved_itinerary_business",
    "website_click",
    "directions_click",
    "ticket_click",
    "phone_click",
]

LEADERBOARD_SLOTS = ["dinner", "drinks", "entertainment", "late-night"]
ADMIN_ANALYTICS_SLOT_LEADERBOARD_LIMIT = 10
ADMIN_ANALYTICS_LEADERBOARD_LIMIT = 25
ADMIN_ANALYTICS_BUSINESS_BREAKDOWN_LIMIT = 250
ADMIN_ANALYTICS_BUSINESS_TIMELINE_LIMIT = 2000
ADMIN_AUDIENCE_DEFAULT_LIMIT = 100
ADMIN_AUDIENCE_MAX_LIMIT = 200
ADMIN_HOTEL_QR_DEFAULT_LIMIT = 100
ADMIN_HOTEL_QR_MAX_LIMIT = 250


def _normalize_analytics_days(days: str) -> Optional[int]:
    value = (days or "30").strip().lower()
    if value == "all":
        return None
    if value not in {"7", "30", "90"}:
        raise HTTPException(status_code=400, detail="days must be one of 7, 30, 90, all")
    return int(value)


def _analytics_since(days: str) -> Optional[str]:
    normalized_days = _normalize_analytics_days(days)
    if normalized_days is None:
        return None
    return (datetime.now(timezone.utc) - timedelta(days=normalized_days)).isoformat()


def _analytics_match_query(*, days: str = "30", city_slug: Optional[str] = None,
                           vibe: Optional[str] = None) -> dict:
    query = {}
    since = _analytics_since(days)
    if since:
        query["timestamp"] = {"$gte": since}
    if city_slug:
        query["city_slug"] = city_slug
    if vibe:
        query["vibe"] = vibe
    return query


async def _homepage_visit_usage_metrics(*, days: str = "30", city_slug: Optional[str] = None) -> dict:
    match = _analytics_match_query(days=days, city_slug=city_slug)
    match["event_type"] = "homepage_visit"
    rows = await db.analytics_events.aggregate([
        {"$match": match},
        {
            "$facet": {
                "visits": [
                    {"$count": "count"},
                ],
                "visitors": [
                    {"$match": {"visitor_id": {"$nin": [None, ""]}}},
                    {"$group": {"_id": "$visitor_id", "visit_count": {"$sum": 1}}},
                    {
                        "$group": {
                            "_id": None,
                            "unique_visitors": {"$sum": 1},
                            "returning_visitors": {
                                "$sum": {
                                    "$cond": [
                                        {"$gt": ["$visit_count", 1]},
                                        1,
                                        0,
                                    ]
                                }
                            },
                        }
                    },
                ],
            }
        },
    ]).to_list(1)
    usage = rows[0] if rows else {}
    visit_row = (usage.get("visits") or [{}])[0]
    visitor_row = (usage.get("visitors") or [{}])[0]
    total_visits = int(visit_row.get("count", 0))
    unique_visitors = int(visitor_row.get("unique_visitors", 0))
    returning_visitors = int(visitor_row.get("returning_visitors", 0))
    returning_visitor_rate = round(returning_visitors / unique_visitors, 4) if unique_visitors else 0
    return {
        "total_visits": total_visits,
        "unique_visitors": unique_visitors,
        "returning_visitors": returning_visitors,
        "returning_visitor_rate": returning_visitor_rate,
    }


def _normalize_pagination(limit: int, offset: int, *, default_limit: int, max_limit: int) -> tuple[int, int]:
    safe_limit = max(1, min(int(limit or default_limit), max_limit))
    safe_offset = max(0, int(offset or 0))
    return safe_limit, safe_offset


def _event_count_group_fields(event_type_field: str = "$event_type") -> dict:
    return {
        event_key: {
            "$sum": {
                "$cond": [
                    {"$eq": [event_type_field, event_key]},
                    1,
                    0,
                ]
            }
        }
        for event_key in LEADERBOARD_METRIC_EVENT_KEYS
    }


def _metric_aliases(counts: dict) -> dict:
    total_click_through = (
        counts.get("website_click", 0)
        + counts.get("directions_click", 0)
        + counts.get("ticket_click", 0)
        + counts.get("phone_click", 0)
    )
    total_engagement = sum(counts.get(key, 0) for key in LEADERBOARD_METRIC_EVENT_KEYS)
    return {
        "appearances": counts.get("business_appearance", 0),
        "business_views": counts.get("business_view", 0),
        "locked_in": counts.get("step_locked", 0),
        "saved_in_final_move": counts.get("saved_itinerary_business", 0),
        "website_clicks": counts.get("website_click", 0),
        "directions_clicks": counts.get("directions_click", 0),
        "ticket_clicks": counts.get("ticket_click", 0),
        "phone_clicks": counts.get("phone_click", 0),
        "total_click_through": total_click_through,
        "total_engagement": total_engagement,
        "engagement_rate": round(total_engagement / counts.get("business_appearance", 0), 4)
        if counts.get("business_appearance", 0)
        else 0,
    }


def _leaderboard_row(business_id: str, counts: dict, *, name: str, sponsor_tier: str) -> dict:
    return {
        "business_id": business_id,
        "name": name or business_id or "(unknown)",
        "sponsor_tier": sponsor_tier or "none",
        **counts,
        **_metric_aliases(counts),
    }


def _business_event_doc(
    event_type: str,
    business: Optional[dict],
    *,
    visitor_id: str = "",
    qr_slug: str = "",
    slot: str = "",
    category_slug: str = "",
    city_slug: str = "",
    vibe: str = "",
    itinerary_id: Optional[str] = None,
    saved_itinerary_id: Optional[str] = None,
    source_itinerary_id: Optional[str] = None,
    source_surface: str = "",
    event_id: str = "",
    event_source: str = "",
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    payload_business = business if isinstance(business, dict) else {}
    return {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "visitor_id": _normalize_visitor_id(visitor_id) or None,
        "qr_slug": _normalize_qr_slug(qr_slug) or None,
        "business_id": payload_business.get("id"),
        "category_slug": category_slug or payload_business.get("category_slug"),
        "slot": slot,
        "city_slug": city_slug or payload_business.get("city_slug"),
        "vibe": vibe,
        "itinerary_id": itinerary_id,
        "saved_itinerary_id": saved_itinerary_id,
        "source_itinerary_id": source_itinerary_id,
        "source_surface": source_surface or None,
        "event_id": event_id or None,
        "event_source": event_source or None,
        "sponsor_tier": payload_business.get("sponsor_tier", "none"),
        "ip": ip,
        "user_agent": user_agent,
        "timestamp": now_iso(),
    }


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


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _normalize_visitor_id(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_qr_slug(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9-]+", "", (value or "").strip().lower())


def _slugify_qr_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "hotel-qr"


async def _unique_hotel_qr_slug(base_slug: str, *, exclude_id: Optional[str] = None) -> str:
    slug = _slugify_qr_name(base_slug)
    if exclude_id:
        existing = await db.hotel_qr_codes.find_one(
            {"slug": slug, "id": {"$ne": exclude_id}},
            {"_id": 0, "id": 1},
        )
    else:
        existing = await db.hotel_qr_codes.find_one({"slug": slug}, {"_id": 0, "id": 1})
    if not existing:
        return slug
    suffix = 2
    while True:
        candidate = f"{slug}-{suffix}"
        if exclude_id:
            existing = await db.hotel_qr_codes.find_one(
                {"slug": candidate, "id": {"$ne": exclude_id}},
                {"_id": 0, "id": 1},
            )
        else:
            existing = await db.hotel_qr_codes.find_one({"slug": candidate}, {"_id": 0, "id": 1})
        if not existing:
            return candidate
        suffix += 1


def _hotel_qr_destination_url(city_slug: str, qr_slug: str) -> str:
    base = (
        os.environ.get("PUBLIC_SITE_URL", "").strip()
        or os.environ.get("FRONTEND_PUBLIC_URL", "").strip()
        or "https://www.yournotdown.com"
    ).rstrip("/")
    return f"{base}?qr={qr_slug}"


def _hotel_qr_response(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    payload = {
        "id": doc.get("id", ""),
        "name": doc.get("name", ""),
        "slug": doc.get("slug", ""),
        "city_slug": doc.get("city_slug", ""),
        "destination_url": doc.get("destination_url", ""),
        "hotel_name": doc.get("hotel_name", ""),
        "location_label": doc.get("location_label", ""),
        "notes": doc.get("notes", ""),
        "active": bool(doc.get("active", True)),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "created_by_user_id": doc.get("created_by_user_id", ""),
    }
    if "analytics" in doc and isinstance(doc.get("analytics"), dict):
        payload["analytics"] = {
            "scans": int(doc["analytics"].get("scans", 0)),
            "unique_visitors": int(doc["analytics"].get("unique_visitors", 0)),
            "tonight_move_views": int(doc["analytics"].get("tonight_move_views", 0)),
            "lock_clicks": int(doc["analytics"].get("lock_clicks", 0)),
            "saved_moves": int(doc["analytics"].get("saved_moves", 0)),
            "email_captures": int(doc["analytics"].get("email_captures", 0)),
            "marketing_opt_ins": int(doc["analytics"].get("marketing_opt_ins", 0)),
            "conversion_rate": float(doc["analytics"].get("conversion_rate", 0)),
        }
    return payload


async def _upsert_visitor_profile(
    *,
    visitor_id: str,
    city_slug: str = "",
    vibe: str = "",
    saved_itinerary_id: Optional[str] = None,
    email_normalized: str = "",
    qr_slug: str = "",
    increment_saved_itinerary: bool = False,
) -> Optional[dict]:
    visitor_id = _normalize_visitor_id(visitor_id)
    if not visitor_id:
        return None

    now = now_iso()
    existing = await db.visitor_profiles.find_one({"visitor_id": visitor_id}, {"_id": 0})

    if existing:
        updated = {
            **existing,
            "last_seen_at": now,
            "last_city_slug": city_slug or existing.get("last_city_slug", ""),
            "last_vibe": vibe or existing.get("last_vibe", ""),
            "event_count": int(existing.get("event_count", 0)) + 1,
            "saved_itinerary_count": int(existing.get("saved_itinerary_count", 0)) + (1 if increment_saved_itinerary else 0),
            "last_saved_itinerary_id": saved_itinerary_id or existing.get("last_saved_itinerary_id"),
            "email_normalized": email_normalized or existing.get("email_normalized", ""),
            "last_qr_slug": qr_slug or existing.get("last_qr_slug", ""),
            "updated_at": now,
        }
        if increment_saved_itinerary and not existing.get("first_saved_itinerary_id"):
            updated["first_saved_itinerary_id"] = saved_itinerary_id
        if email_normalized and not existing.get("first_email_captured_at"):
            updated["first_email_captured_at"] = now
        if qr_slug and not existing.get("first_qr_slug"):
            updated["first_qr_slug"] = qr_slug
        await db.visitor_profiles.update_one(
            {"visitor_id": visitor_id},
            {"$set": {
                "last_seen_at": updated["last_seen_at"],
                "last_city_slug": updated["last_city_slug"],
                "last_vibe": updated["last_vibe"],
                "event_count": updated["event_count"],
                "saved_itinerary_count": updated["saved_itinerary_count"],
                "last_saved_itinerary_id": updated["last_saved_itinerary_id"],
                "email_normalized": updated["email_normalized"],
                "last_qr_slug": updated["last_qr_slug"],
                "updated_at": updated["updated_at"],
                "first_saved_itinerary_id": updated.get("first_saved_itinerary_id", existing.get("first_saved_itinerary_id")),
                "first_email_captured_at": updated.get("first_email_captured_at", existing.get("first_email_captured_at")),
                "first_qr_slug": updated.get("first_qr_slug", existing.get("first_qr_slug")),
            }},
        )
        return updated

    created = {
        "id": str(uuid.uuid4()),
        "visitor_id": visitor_id,
        "first_seen_at": now,
        "last_seen_at": now,
        "first_city_slug": city_slug,
        "last_city_slug": city_slug,
        "first_vibe": vibe,
        "last_vibe": vibe,
        "event_count": 1,
        "saved_itinerary_count": 1 if increment_saved_itinerary else 0,
        "first_saved_itinerary_id": saved_itinerary_id if increment_saved_itinerary else None,
        "last_saved_itinerary_id": saved_itinerary_id if increment_saved_itinerary else None,
        "first_email_captured_at": now if email_normalized else None,
        "email_normalized": email_normalized,
        "first_qr_slug": qr_slug or "",
        "last_qr_slug": qr_slug or "",
        "created_at": now,
        "updated_at": now,
    }
    await db.visitor_profiles.insert_one(created)
    return created


async def _upsert_audience_contact(
    *,
    email: str,
    visitor_id: str = "",
    qr_slug: str = "",
    city_slug: str,
    vibe: str,
    marketing_opt_in: bool,
    saved_itinerary_id: str,
    locked_slots: List[str],
) -> dict:
    email_normalized = _normalize_email(email)
    now = now_iso()
    existing = await db.audience_contacts.find_one({"email_normalized": email_normalized}, {"_id": 0})

    if existing:
        next_marketing_opt_in = bool(existing.get("marketing_opt_in")) or bool(marketing_opt_in)
        marketing_opt_in_at = existing.get("marketing_opt_in_at")
        if not marketing_opt_in_at and marketing_opt_in:
            marketing_opt_in_at = now
        updated = {
            **existing,
            "email": email_normalized,
            "email_normalized": email_normalized,
            "visitor_id": visitor_id or existing.get("visitor_id", ""),
            "last_qr_slug": qr_slug or existing.get("last_qr_slug", ""),
            "marketing_opt_in": next_marketing_opt_in,
            "marketing_opt_in_at": marketing_opt_in_at,
            "source": "save_tonights_move",
            "city_slug": city_slug,
            "last_vibe": vibe,
            "last_saved_itinerary_id": saved_itinerary_id,
            "saved_itinerary_count": int(existing.get("saved_itinerary_count", 0)) + 1,
            "locked_slots": locked_slots,
            "last_saved_at": now,
            "updated_at": now,
        }
        if qr_slug and not existing.get("first_qr_slug"):
            updated["first_qr_slug"] = qr_slug
        await db.audience_contacts.update_one(
            {"email_normalized": email_normalized},
            {"$set": {
                "email": updated["email"],
                "email_normalized": updated["email_normalized"],
                "visitor_id": updated["visitor_id"],
                "last_qr_slug": updated["last_qr_slug"],
                "marketing_opt_in": updated["marketing_opt_in"],
                "marketing_opt_in_at": updated["marketing_opt_in_at"],
                "source": updated["source"],
                "city_slug": updated["city_slug"],
                "last_vibe": updated["last_vibe"],
                "last_saved_itinerary_id": updated["last_saved_itinerary_id"],
                "saved_itinerary_count": updated["saved_itinerary_count"],
                "locked_slots": updated["locked_slots"],
                "last_saved_at": updated["last_saved_at"],
                "updated_at": updated["updated_at"],
                "first_qr_slug": updated.get("first_qr_slug", existing.get("first_qr_slug")),
            }},
        )
        return updated

    created = {
        "id": str(uuid.uuid4()),
        "email": email_normalized,
        "email_normalized": email_normalized,
        "visitor_id": visitor_id,
        "first_qr_slug": qr_slug or "",
        "last_qr_slug": qr_slug or "",
        "marketing_opt_in": bool(marketing_opt_in),
        "marketing_opt_in_at": now if marketing_opt_in else None,
        "source": "save_tonights_move",
        "city_slug": city_slug,
        "first_vibe": vibe,
        "last_vibe": vibe,
        "first_saved_itinerary_id": saved_itinerary_id,
        "last_saved_itinerary_id": saved_itinerary_id,
        "saved_itinerary_count": 1,
        "locked_slots": locked_slots,
        "last_saved_at": now,
        "created_at": now,
        "updated_at": now,
        "unsubscribed_at": None,
    }
    await db.audience_contacts.insert_one(created)
    return created


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
    return saved_itinerary_email_subject(doc)


def _saved_itinerary_email_content(doc: dict) -> tuple[str, str]:
    return saved_itinerary_email_content(doc)


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


def _send_business_owner_invite_email(doc: dict, claim_url: str, business_name: str) -> dict:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_email = os.environ.get("RESEND_FROM_EMAIL", "").strip()
    reply_to = os.environ.get("RESEND_REPLY_TO", "").strip()
    text_body, html_body = business_owner_invite_email_content({
        "business_name": business_name,
        "claim_url": claim_url,
        "expires_at": doc.get("expires_at"),
    })
    payload = {
        "from": from_email,
        "to": [doc["email"]],
        "subject": business_owner_invite_email_subject({"business_name": business_name}),
        "text": text_body,
        "html": html_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
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
    limit = max(1, min(int(limit or 200), 2000))
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
    _require_ip_rate_limit(
        "itinerary_generate_ip",
        request,
        limit=RATE_LIMIT_ITINERARY_GENERATE_PER_IP,
        window_seconds=RATE_LIMIT_MINUTE_SECONDS,
    )
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
    exclude_ids_by_slot = {
        slot: {
            business_id
            for business_id in (ids or [])
            if business_id
        }
        for slot, ids in (req.exclude_ids_by_slot or {}).items()
        if slot
    }
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
        slot_history_excludes = exclude_ids_by_slot.get(label["slot"], set())
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
                    exclude | chosen_ids | slot_history_excludes,
                    exclude_event_ids,
                )
            if not pick:
                pick = _weighted_pick(
                    event_candidates or candidates,
                    exclude | chosen_ids,
                    req.vibe,
                    slot_history_excludes,
                )
        elif not pick:
            pick = _weighted_pick(
                candidates,
                exclude | chosen_ids,
                req.vibe,
                slot_history_excludes,
            )
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
        appearance_docs.append(_business_event_doc(
            "business_appearance",
            b,
            slot=step.get("slot", ""),
            category_slug=b.get("category_slug", ""),
            city_slug=req.city,
            vibe=req.vibe,
            itinerary_id=itin_id,
            source_surface="tonight_page",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        ))
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
    limit = max(1, min(int(limit or 200), 500))
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
async def google_places_photo(
    photo_name: Optional[str] = None,
    business_id: Optional[str] = None,
    max_width: Optional[int] = None,
):
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
    safe_max_width = normalize_google_places_photo_width(max_width)
    try:
        upstream = await run_in_threadpool(fetch_google_places_photo, photo_name, safe_max_width)
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
        headers={"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"},
        background=BackgroundTask(upstream.close),
    )


# ------------- File serving (public) -------------
@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = get_object(path)
    except requests.HTTPError as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    return FastResponse(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"},
    )


# ------------- Analytics -------------
@api_router.post("/analytics/track")
async def track_event(event: AnalyticsEvent, request: Request):
    _require_ip_rate_limit(
        "analytics_track_ip",
        request,
        limit=RATE_LIMIT_ANALYTICS_TRACK_PER_IP,
        window_seconds=RATE_LIMIT_MINUTE_SECONDS,
    )
    doc = {
        "id": str(uuid.uuid4()),
        "event_type": event.event_type,
        "visitor_id": _normalize_visitor_id(event.visitor_id) or None,
        "qr_slug": _normalize_qr_slug(event.qr_slug) or None,
        "business_id": event.business_id,
        "category_slug": event.category_slug,
        "slot": event.slot,
        "city_slug": event.city_slug,
        "vibe": event.vibe,
        "itinerary_id": event.itinerary_id,
        "saved_itinerary_id": event.saved_itinerary_id,
        "source_itinerary_id": event.source_itinerary_id,
        "source_surface": event.source_surface,
        "event_id": event.event_id,
        "event_source": event.event_source,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": now_iso(),
    }
    if event.business_id and event.event_type in BUSINESS_SCOPED_EVENT_TYPES:
        biz = await db.businesses.find_one({"id": event.business_id}, {"_id": 0, "sponsor_tier": 1})
        if biz:
            doc["sponsor_tier"] = biz.get("sponsor_tier", "none")
    await db.analytics_events.insert_one(doc)
    await _upsert_visitor_profile(
        visitor_id=event.visitor_id or "",
        qr_slug=_normalize_qr_slug(event.qr_slug),
        city_slug=event.city_slug or "",
        vibe=event.vibe or "",
    )
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
async def save_itinerary(payload: SaveItineraryRequest, request: Request):
    _require_ip_rate_limit(
        "itinerary_save_ip",
        request,
        limit=RATE_LIMIT_ITINERARY_SAVE_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    email = (payload.email or "").strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email.")
    _require_rate_limit_key(
        "itinerary_save_email",
        email,
        limit=RATE_LIMIT_ITINERARY_SAVE_PER_EMAIL,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    visitor_id = _normalize_visitor_id(payload.visitor_id)
    qr_slug = _normalize_qr_slug(payload.qr_slug)

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
        "visitor_id": visitor_id or None,
        "qr_slug": qr_slug or None,
        "marketing_opt_in": bool(payload.marketing_opt_in),
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
    await _upsert_audience_contact(
        email=email,
        visitor_id=visitor_id,
        qr_slug=qr_slug,
        city_slug=doc["city_slug"],
        vibe=doc["vibe"],
        marketing_opt_in=bool(payload.marketing_opt_in),
        saved_itinerary_id=doc["id"],
        locked_slots=safe_locked_slots,
    )
    await _upsert_visitor_profile(
        visitor_id=visitor_id,
        qr_slug=qr_slug,
        city_slug=doc["city_slug"],
        vibe=doc["vibe"],
        saved_itinerary_id=doc["id"],
        email_normalized=email,
        increment_saved_itinerary=True,
    )
    saved_step_events = [
        _business_event_doc(
            "saved_itinerary_business",
            step.get("business"),
            visitor_id=visitor_id,
            qr_slug=qr_slug,
            slot=step.get("slot", ""),
            category_slug=(step.get("business") or {}).get("category_slug", ""),
            city_slug=doc["city_slug"],
            vibe=doc["vibe"],
            itinerary_id=doc["source_itinerary_id"],
            saved_itinerary_id=doc["id"],
            source_itinerary_id=doc["source_itinerary_id"],
            source_surface="save_itinerary",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        for step in safe_steps
        if (step.get("business") or {}).get("id")
    ]
    if saved_step_events:
        try:
            await db.analytics_events.insert_many(saved_step_events)
        except Exception as exc:
            logger.warning("saved_itinerary_business analytics write failed: %s", exc)
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


@api_router.get("/admin/audience")
async def admin_audience(
    q: str = "",
    filter: str = "all",
    limit: int = ADMIN_AUDIENCE_DEFAULT_LIMIT,
    offset: int = 0,
    user=Depends(require_admin),
):
    if filter not in {"all", "opted_in", "not_opted_in"}:
        raise HTTPException(status_code=400, detail="Invalid filter")
    limit, offset = _normalize_pagination(
        limit,
        offset,
        default_limit=ADMIN_AUDIENCE_DEFAULT_LIMIT,
        max_limit=ADMIN_AUDIENCE_MAX_LIMIT,
    )

    query = {}
    if filter == "opted_in":
        query["marketing_opt_in"] = True
    elif filter == "not_opted_in":
        query["marketing_opt_in"] = {"$ne": True}
    if q.strip():
        query["email_normalized"] = {"$regex": re.escape(q.strip().lower())}

    rows = await db.audience_contacts.find(query, {"_id": 0}).sort([("last_saved_at", -1)]).skip(offset).limit(limit).to_list(limit)
    visitor_ids = [row.get("visitor_id") for row in rows if row.get("visitor_id")]
    visitor_profiles = []
    if visitor_ids:
        visitor_profiles = await db.visitor_profiles.find(
            {"visitor_id": {"$in": visitor_ids}},
            {"_id": 0},
        ).to_list(limit)
    visitor_profiles_by_id = {
        profile.get("visitor_id"): profile
        for profile in visitor_profiles
        if profile.get("visitor_id")
    }
    now = datetime.now(timezone.utc)
    total_contacts = await db.audience_contacts.count_documents(query)
    totals_pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": None,
                "marketing_opted_in_contacts": {
                    "$sum": {"$cond": [{"$eq": ["$marketing_opt_in", True]}, 1, 0]}
                },
                "total_saved_itineraries": {
                    "$sum": {"$ifNull": ["$saved_itinerary_count", 0]}
                },
                "repeat_savers": {
                    "$sum": {
                        "$cond": [
                            {"$gt": [{"$ifNull": ["$saved_itinerary_count", 0]}, 1]},
                            1,
                            0,
                        ]
                    }
                },
                "recent_captures": {
                    "$sum": {
                        "$cond": [
                            {
                                "$gte": [
                                    "$last_saved_at",
                                    (now - timedelta(days=7)).isoformat(),
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        },
    ]
    totals_row = await db.audience_contacts.aggregate(totals_pipeline).to_list(1)
    totals_doc = totals_row[0] if totals_row else {}
    marketing_opted_in_contacts = int(totals_doc.get("marketing_opted_in_contacts", 0))
    non_marketing_contacts = max(total_contacts - marketing_opted_in_contacts, 0)
    total_saved_itineraries = int(totals_doc.get("total_saved_itineraries", 0))
    total_anonymous_visitors = await db.visitor_profiles.count_documents({})
    new_visitors = await db.visitor_profiles.count_documents({"event_count": {"$lte": 1}})
    returning_visitors = max(total_anonymous_visitors - new_visitors, 0)
    returning_visitor_rate = round(returning_visitors / total_anonymous_visitors, 4) if total_anonymous_visitors else 0
    repeat_savers = int(totals_doc.get("repeat_savers", 0))
    repeat_saver_rate = round(repeat_savers / total_contacts, 4) if total_contacts else 0
    recent_captures = int(totals_doc.get("recent_captures", 0))
    payload_rows = [
        {
            "id": row.get("id"),
            "email": row.get("email", ""),
            "visitor_id": row.get("visitor_id", ""),
            "visitor_status": (
                "returning"
                if int((visitor_profiles_by_id.get(row.get("visitor_id")) or {}).get("event_count", 0)) > 1
                else "new"
            ) if row.get("visitor_id") else "unknown",
            "marketing_opt_in": bool(row.get("marketing_opt_in")),
            "city_slug": row.get("city_slug", ""),
            "last_vibe": row.get("last_vibe", ""),
            "saved_itinerary_count": int(row.get("saved_itinerary_count", 0)),
            "last_saved_at": row.get("last_saved_at"),
            "source": row.get("source", "save_tonights_move"),
        }
        for row in rows
    ]
    return {
        "totals": {
            "total_contacts": total_contacts,
            "total_anonymous_visitors": total_anonymous_visitors,
            "new_visitors": new_visitors,
            "returning_visitors": returning_visitors,
            "returning_visitor_rate": returning_visitor_rate,
            "marketing_opted_in_contacts": marketing_opted_in_contacts,
            "non_marketing_contacts": non_marketing_contacts,
            "total_saved_itineraries": total_saved_itineraries,
            "repeat_savers": repeat_savers,
            "repeat_saver_rate": repeat_saver_rate,
            "recent_captures": recent_captures,
        },
        "rows": payload_rows,
        "meta": {
            "limit": limit,
            "offset": offset,
            "total_rows": total_contacts,
            "has_more": offset + len(payload_rows) < total_contacts,
            "next_offset": offset + len(payload_rows) if offset + len(payload_rows) < total_contacts else None,
            "prev_offset": max(offset - limit, 0) if offset > 0 else None,
        },
    }


@api_router.get("/admin/hotel-qr")
async def admin_list_hotel_qr_codes(
    days: str = "30",
    limit: int = ADMIN_HOTEL_QR_DEFAULT_LIMIT,
    offset: int = 0,
    user=Depends(require_admin),
):
    limit, offset = _normalize_pagination(
        limit,
        offset,
        default_limit=ADMIN_HOTEL_QR_DEFAULT_LIMIT,
        max_limit=ADMIN_HOTEL_QR_MAX_LIMIT,
    )
    since = _analytics_since(days)
    rows = await db.hotel_qr_codes.find({}, {"_id": 0}).sort([("created_at", -1)]).skip(offset).limit(limit).to_list(limit)
    total_rows = await db.hotel_qr_codes.count_documents({})
    slugs = [row.get("slug") for row in rows if row.get("slug")]
    analytics_docs = []
    saved_docs = []
    if slugs:
        analytics_query = {"qr_slug": {"$in": slugs}}
        if since:
            analytics_query["timestamp"] = {"$gte": since}
        analytics_docs = await db.analytics_events.find(
            analytics_query,
            {"_id": 0, "qr_slug": 1, "event_type": 1, "visitor_id": 1},
        ).to_list(10000)
        saved_query = {"qr_slug": {"$in": slugs}}
        if since:
            saved_query["created_at"] = {"$gte": since}
        saved_docs = await db.saved_itineraries.find(
            saved_query,
            {"_id": 0, "qr_slug": 1, "email": 1, "marketing_opt_in": 1},
        ).to_list(5000)

    analytics_by_slug: Dict[str, dict] = {}
    for slug in slugs:
        analytics_by_slug[slug] = {
            "scans": 0,
            "visitor_ids": set(),
            "tonight_move_views": 0,
            "lock_clicks": 0,
            "saved_moves": 0,
            "emails": set(),
            "marketing_emails": set(),
        }

    for doc in analytics_docs:
        slug = doc.get("qr_slug")
        if slug not in analytics_by_slug:
            continue
        bucket = analytics_by_slug[slug]
        if doc.get("event_type") == "hotel_qr_scan":
            bucket["scans"] += 1
        if doc.get("event_type") == "itinerary_view":
            bucket["tonight_move_views"] += 1
        if doc.get("event_type") == "step_locked":
            bucket["lock_clicks"] += 1
        if doc.get("visitor_id"):
            bucket["visitor_ids"].add(doc["visitor_id"])

    for doc in saved_docs:
        slug = doc.get("qr_slug")
        if slug not in analytics_by_slug:
            continue
        bucket = analytics_by_slug[slug]
        bucket["saved_moves"] += 1
        if doc.get("email"):
            bucket["emails"].add(doc["email"])
            if doc.get("marketing_opt_in"):
                bucket["marketing_emails"].add(doc["email"])

    payload_rows = []
    for row in rows:
        stats = analytics_by_slug.get(row.get("slug"), {})
        scans = stats.get("scans", 0)
        saved_moves = stats.get("saved_moves", 0)
        payload_rows.append(_hotel_qr_response({
            **row,
            "analytics": {
                "scans": scans,
                "unique_visitors": len(stats.get("visitor_ids", set())),
                "tonight_move_views": stats.get("tonight_move_views", 0),
                "lock_clicks": stats.get("lock_clicks", 0),
                "saved_moves": saved_moves,
                "email_captures": len(stats.get("emails", set())),
                "marketing_opt_ins": len(stats.get("marketing_emails", set())),
                "conversion_rate": round(saved_moves / scans, 4) if scans else 0,
            },
        }))
    return {
        "rows": payload_rows,
        "meta": {
            "days": "all" if _normalize_analytics_days(days) is None else str(_normalize_analytics_days(days)),
            "limit": limit,
            "offset": offset,
            "total_rows": total_rows,
            "has_more": offset + len(payload_rows) < total_rows,
            "next_offset": offset + len(payload_rows) if offset + len(payload_rows) < total_rows else None,
            "prev_offset": max(offset - limit, 0) if offset > 0 else None,
        },
    }


@api_router.post("/admin/hotel-qr")
async def admin_create_hotel_qr_code(body: HotelQrCodeCreate, request: Request, user=Depends(require_admin)):
    _require_rate_limit_key(
        "admin_hotel_qr_write_user",
        user["user_id"],
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_ADMIN,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    _require_ip_rate_limit(
        "admin_hotel_qr_write_ip",
        request,
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    slug = await _unique_hotel_qr_slug(body.name)
    now = now_iso()
    doc = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "slug": slug,
        "city_slug": body.city_slug or "nashville",
        "destination_url": _hotel_qr_destination_url(body.city_slug or "nashville", slug),
        "hotel_name": body.hotel_name.strip(),
        "location_label": body.location_label.strip(),
        "notes": body.notes.strip(),
        "active": True,
        "created_at": now,
        "updated_at": now,
        "created_by_user_id": user["user_id"],
    }
    await db.hotel_qr_codes.insert_one(doc)
    return _hotel_qr_response(doc)


@api_router.patch("/admin/hotel-qr/{qr_id}")
async def admin_update_hotel_qr_code(qr_id: str, body: HotelQrCodeUpdate, request: Request, user=Depends(require_admin)):
    _require_rate_limit_key(
        "admin_hotel_qr_write_user",
        user["user_id"],
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_ADMIN,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    _require_ip_rate_limit(
        "admin_hotel_qr_write_ip",
        request,
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    existing = await db.hotel_qr_codes.find_one({"id": qr_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Hotel QR not found")
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if "name" in update:
        update["name"] = update["name"].strip()
        if not update["name"]:
            raise HTTPException(status_code=400, detail="Name is required")
        update["slug"] = await _unique_hotel_qr_slug(update["name"], exclude_id=qr_id)
    for key in ("hotel_name", "location_label", "notes"):
        if key in update:
            update[key] = (update[key] or "").strip()
    city_slug = update.get("city_slug", existing.get("city_slug", "nashville"))
    slug = update.get("slug", existing.get("slug"))
    update["destination_url"] = _hotel_qr_destination_url(city_slug, slug)
    update["updated_at"] = now_iso()
    await db.hotel_qr_codes.update_one({"id": qr_id}, {"$set": update})
    return _hotel_qr_response(await db.hotel_qr_codes.find_one({"id": qr_id}, {"_id": 0}))


@api_router.post("/admin/hotel-qr/{qr_id}/deactivate")
async def admin_deactivate_hotel_qr_code(qr_id: str, request: Request, user=Depends(require_admin)):
    _require_rate_limit_key(
        "admin_hotel_qr_write_user",
        user["user_id"],
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_ADMIN,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    _require_ip_rate_limit(
        "admin_hotel_qr_write_ip",
        request,
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    result = await db.hotel_qr_codes.update_one(
        {"id": qr_id},
        {"$set": {"active": False, "updated_at": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Hotel QR not found")
    return _hotel_qr_response(await db.hotel_qr_codes.find_one({"id": qr_id}, {"_id": 0}))


@api_router.delete("/admin/hotel-qr/{qr_id}")
async def admin_delete_hotel_qr_code(qr_id: str, request: Request, user=Depends(require_admin)):
    _require_rate_limit_key(
        "admin_hotel_qr_write_user",
        user["user_id"],
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_ADMIN,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    _require_ip_rate_limit(
        "admin_hotel_qr_write_ip",
        request,
        limit=RATE_LIMIT_HOTEL_QR_ADMIN_WRITES_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    existing = await db.hotel_qr_codes.find_one({"id": qr_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Hotel QR not found")
    await db.hotel_qr_codes.delete_one({"id": qr_id})
    return {
        "ok": True,
        "deleted": _hotel_qr_response(existing),
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

    expires_at = datetime.now(timezone.utc) + timedelta(days=ADMIN_SESSION_DAYS)
    await db.user_sessions.insert_one({
        "session_id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_token_hash": _hash_token(session_token),
        "expires_at": expires_at.isoformat(),
        "created_at": now_iso(),
        "last_seen_at": now_iso(),
    })

    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=session_token,
        max_age=ADMIN_SESSION_DAYS * 24 * 60 * 60,
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
        await db.user_sessions.delete_many({
            "$or": [
                {"session_token_hash": _hash_token(session_token)},
                {"session_token": session_token},
            ]
        })
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/", secure=True, samesite="none")
    return {"ok": True}


@api_router.post("/business/claim")
async def business_claim(payload: BusinessOwnerClaimRequest, response: Response, request: Request):
    _require_ip_rate_limit(
        "business_claim_ip",
        request,
        limit=RATE_LIMIT_BUSINESS_CLAIM_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    raw_token = (payload.token or "").strip()
    if not raw_token:
        raise HTTPException(status_code=400, detail="Invalid or expired invite.")
    invite = await db.business_owner_invites.find_one({"token_hash": _hash_token(raw_token)}, {"_id": 0})
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite.")
    if invite.get("status") == "revoked":
        raise HTTPException(status_code=400, detail="This invite is no longer active.")
    if invite.get("status") == "accepted":
        raise HTTPException(status_code=400, detail="This invite has already been used.")

    expires_at_raw = invite.get("expires_at")
    expires_at = datetime.fromisoformat(expires_at_raw) if expires_at_raw else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        await db.business_owner_invites.update_one(
            {"id": invite["id"]},
            {"$set": {"status": "expired"}},
        )
        raise HTTPException(status_code=400, detail="This invite has expired.")
    if invite.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Invalid or expired invite.")

    business = await db.businesses.find_one({"id": invite["business_id"]}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    owner = await db.business_owners.find_one(
        {"business_id": invite["business_id"], "email": invite["email"]},
        {"_id": 0},
    )
    owner_id = owner.get("owner_id") if owner else f"owner_{uuid.uuid4().hex[:12]}"
    owner_doc = {
        "owner_id": owner_id,
        "business_id": invite["business_id"],
        "email": invite["email"],
        "status": "active",
        "invite_id": invite["id"],
        "created_at": owner.get("created_at") if owner else now_iso(),
        "last_login_at": now_iso(),
    }
    if owner:
        await db.business_owners.update_one(
            {"owner_id": owner_id},
            {"$set": {
                "status": "active",
                "invite_id": invite["id"],
                "last_login_at": owner_doc["last_login_at"],
            }},
        )
    else:
        await db.business_owners.insert_one(owner_doc)

    await db.business_owner_invites.update_one(
        {"id": invite["id"]},
        {"$set": {"status": "accepted", "accepted_at": now_iso()}},
    )

    session_token = _new_owner_token()
    session_doc = {
        "session_id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "business_id": invite["business_id"],
        "session_token_hash": _hash_token(session_token),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=BUSINESS_OWNER_SESSION_DAYS)).isoformat(),
        "created_at": now_iso(),
        "last_seen_at": now_iso(),
        "revoked_at": None,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    await db.business_owner_sessions.insert_one(session_doc)
    response.set_cookie(
        key=BUSINESS_OWNER_SESSION_COOKIE,
        value=session_token,
        max_age=BUSINESS_OWNER_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return {
        "ok": True,
        "owner": _owner_safe(owner_doc, business),
    }


@api_router.get("/business/me")
async def business_me(owner_ctx=Depends(get_current_business_owner)):
    return _owner_safe(owner_ctx["owner"], owner_ctx["business"])


@api_router.get("/business/analytics")
async def business_analytics(owner_ctx=Depends(get_current_business_owner)):
    business_id = owner_ctx["owner"]["business_id"]
    pipeline = [
        {"$match": {"business_id": business_id}},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
    ]
    rows = await db.analytics_events.aggregate(pipeline).to_list(100)
    counts = {row["_id"]: row["count"] for row in rows}
    return {
        "business_id": business_id,
        **_metric_aliases(counts),
    }


# ------------- Admin: businesses -------------
@api_router.get("/admin/businesses")
async def admin_list_businesses(imported_status: Optional[str] = None, user=Depends(require_admin)):
    if imported_status and imported_status not in VALID_IMPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid imported_status")
    query = {"imported_status": imported_status} if imported_status else {}
    items = await db.businesses.find(query, {"_id": 0}).sort([("order", 1)]).to_list(5000)
    return annotate_itinerary_buckets(items)


@api_router.get("/admin/businesses/{business_id}/owner-access")
async def admin_business_owner_access(business_id: str, user=Depends(require_admin)):
    business = await db.businesses.find_one({"id": business_id}, {"_id": 0, "id": 1})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return await _owner_access_summary(business_id)


@api_router.post("/admin/businesses/{business_id}/owner-invite")
async def admin_business_owner_invite(business_id: str, payload: BusinessOwnerInviteCreate, request: Request, user=Depends(require_admin)):
    _require_rate_limit_key(
        "admin_owner_invite_user",
        user["user_id"],
        limit=RATE_LIMIT_OWNER_INVITE_PER_ADMIN,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    _require_ip_rate_limit(
        "admin_owner_invite_ip",
        request,
        limit=RATE_LIMIT_OWNER_INVITE_PER_IP,
        window_seconds=RATE_LIMIT_HOUR_SECONDS,
    )
    business = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    email = (payload.email or "").strip().lower()
    if not _valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email.")

    now = datetime.now(timezone.utc)
    raw_token = _new_owner_token()
    invite_id = str(uuid.uuid4())
    doc = {
        "id": invite_id,
        "business_id": business_id,
        "email": email,
        "token_hash": _hash_token(raw_token),
        "status": "pending",
        "sent_at": None,
        "expires_at": (now + timedelta(days=BUSINESS_OWNER_INVITE_DAYS)).isoformat(),
        "accepted_at": None,
        "revoked_at": None,
        "created_by_user_id": user["user_id"],
        "created_at": now_iso(),
        "delivery_status": "",
        "delivery_error": "",
        "email_provider": "",
        "provider_message_id": "",
    }
    await db.business_owner_invites.update_many(
        {"business_id": business_id, "email": email, "status": "pending"},
        {"$set": {"status": "revoked", "revoked_at": now_iso()}},
    )
    delivery = _owner_invite_delivery_result()
    doc.update({
        "delivery_status": delivery["delivery_status"],
        "delivery_error": delivery["delivery_error"],
        "email_provider": delivery["email_provider"],
        "provider_message_id": delivery["provider_message_id"],
        "sent_at": delivery["sent_at"],
    })
    await db.business_owner_invites.insert_one(doc)

    if doc["delivery_status"] != "provider_unconfigured":
        claim_url = _business_owner_claim_url(raw_token)
        try:
            delivery = await run_in_threadpool(_send_business_owner_invite_email, doc, claim_url, business.get("name", ""))
        except requests.RequestException as exc:
            delivery = {
                "delivery_status": "failed",
                "delivery_error": str(exc),
                "email_provider": "resend",
                "provider_message_id": "",
                "sent_at": None,
            }
        await db.business_owner_invites.update_one(
            {"id": invite_id},
            {"$set": {
                "delivery_status": delivery["delivery_status"],
                "delivery_error": delivery["delivery_error"],
                "email_provider": delivery["email_provider"],
                "provider_message_id": delivery["provider_message_id"],
                "sent_at": delivery["sent_at"],
            }},
        )
        doc.update(delivery)

    summary = await _owner_access_summary(business_id)
    return {
        "ok": True,
        "invite": summary["invite"],
        "owner": summary["owner"],
        "portal_access_active": summary["portal_access_active"],
    }


@api_router.post("/admin/businesses/{business_id}/owner-access/revoke")
async def admin_revoke_business_owner_access(business_id: str, user=Depends(require_admin)):
    business = await db.businesses.find_one({"id": business_id}, {"_id": 0, "id": 1})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    revoked_at = now_iso()
    await db.business_owner_invites.update_many(
        {"business_id": business_id, "status": "pending"},
        {"$set": {"status": "revoked", "revoked_at": revoked_at}},
    )
    await db.business_owners.update_many(
        {"business_id": business_id, "status": "active"},
        {"$set": {"status": "revoked", "revoked_at": revoked_at}},
    )
    await db.business_owner_sessions.update_many(
        {"business_id": business_id, "revoked_at": None},
        {"$set": {"revoked_at": revoked_at}},
    )
    summary = await _owner_access_summary(business_id)
    return {"ok": True, **summary}


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
async def admin_business_analytics(business_id: str, days: str = "30", user=Depends(require_admin)):
    biz = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    since = _analytics_since(days)
    totals_match = {"business_id": business_id}
    if since:
        totals_match["timestamp"] = {"$gte": since}

    # Totals per event type (bounded by selected window by default)
    pipeline = [
        {"$match": totals_match},
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
    ]
    rows = await db.analytics_events.aggregate(pipeline).to_list(100)
    totals = {r["_id"]: r["count"] for r in rows}

    # Daily timeline for the selected range
    tl_pipeline = [
        {"$match": totals_match},
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
    tl_rows = await db.analytics_events.aggregate(tl_pipeline).to_list(ADMIN_ANALYTICS_BUSINESS_TIMELINE_LIMIT)

    # Build {day: {event_type: count}}
    by_day: dict = {}
    for r in tl_rows:
        day = r["_id"]["day"]
        et = r["_id"]["event_type"]
        by_day.setdefault(day, {})[et] = r["count"]

    timeline = []
    normalized_days = _normalize_analytics_days(days)
    if normalized_days is None:
        timeline_days = sorted(by_day.keys())
    else:
        today = datetime.now(timezone.utc).date()
        timeline_days = [
            (today - timedelta(days=i)).isoformat()
            for i in range(normalized_days - 1, -1, -1)
        ]
    for d in timeline_days:
        row = by_day.get(d, {})
        timeline.append({
            "day": d,
            "business_appearance": row.get("business_appearance", 0),
            "business_view": row.get("business_view", 0),
            "step_locked": row.get("step_locked", 0),
            "saved_itinerary_business": row.get("saved_itinerary_business", 0),
            "website_click": row.get("website_click", 0),
            "phone_click": row.get("phone_click", 0),
            "directions_click": row.get("directions_click", 0),
            "ticket_click": row.get("ticket_click", 0),
            "total_engagement": _metric_aliases(row)["total_engagement"],
        })
    metric_totals = _metric_aliases(totals)

    return {
        "business": biz,
        "filters": {
            "days": "all" if normalized_days is None else str(normalized_days),
        },
        "totals": {
            "business_appearance": totals.get("business_appearance", 0),
            "business_view": totals.get("business_view", 0),
            "step_locked": totals.get("step_locked", 0),
            "saved_itinerary_business": totals.get("saved_itinerary_business", 0),
            "website_click": totals.get("website_click", 0),
            "phone_click": totals.get("phone_click", 0),
            "directions_click": totals.get("directions_click", 0),
            "ticket_click": totals.get("ticket_click", 0),
            **metric_totals,
        },
        "timeline": timeline,
    }


@api_router.get("/admin/analytics/summary")
async def admin_analytics_summary(
    days: str = "30",
    city_slug: Optional[str] = None,
    vibe: Optional[str] = None,
    slot: Optional[str] = None,
    user=Depends(require_admin),
):
    slot_filter = (slot or "").strip().lower() or None
    if slot_filter == "all":
        slot_filter = None
    if slot_filter and slot_filter not in LEADERBOARD_SLOTS:
        raise HTTPException(status_code=400, detail="slot must be one of dinner, drinks, entertainment, late-night")
    vibe_filter = (vibe or "").strip() or None
    if vibe_filter == "all":
        vibe_filter = None
    base_match = _analytics_match_query(days=days, city_slug=city_slug, vibe=vibe_filter)

    pipeline = []
    if base_match:
        pipeline.append({"$match": base_match})
    pipeline += [
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
    ]
    rows = await db.analytics_events.aggregate(pipeline).to_list(100)
    summary = {r["_id"]: r["count"] for r in rows}

    # per-category
    cat_pipeline = []
    if base_match:
        cat_pipeline.append({"$match": base_match})
    cat_pipeline += [
        {"$match": {"event_type": "category_click"}},
        {"$group": {"_id": "$category_slug", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cat_rows = await db.analytics_events.aggregate(cat_pipeline).to_list(100)

    # per-business
    biz_match = {**base_match, "business_id": {"$ne": None}}
    if slot_filter:
        biz_match["slot"] = slot_filter
    biz_pipeline = [
        {"$match": biz_match},
        {"$group": {"_id": "$business_id", **_event_count_group_fields()}},
    ]
    biz_rows = await db.analytics_events.aggregate(biz_pipeline).to_list(ADMIN_ANALYTICS_BUSINESS_BREAKDOWN_LIMIT * 8)
    slot_pipeline = [
        {"$match": {**base_match, "business_id": {"$ne": None}, "slot": {"$in": LEADERBOARD_SLOTS}}},
        {"$group": {"_id": {"business_id": "$business_id", "slot": "$slot"}, **_event_count_group_fields()}},
    ]
    slot_rows = await db.analytics_events.aggregate(slot_pipeline).to_list(ADMIN_ANALYTICS_BUSINESS_BREAKDOWN_LIMIT * len(LEADERBOARD_SLOTS) * 2)
    vibe_pipeline = [
        {"$match": {**base_match, "business_id": {"$ne": None}, "vibe": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$vibe", **_event_count_group_fields()}},
    ]
    vibe_rows = await db.analytics_events.aggregate(vibe_pipeline).to_list(250)
    by_biz = {}
    for r in biz_rows:
        bid = r["_id"]
        by_biz[bid] = {
            key: int(r.get(key, 0))
            for key in LEADERBOARD_METRIC_EVENT_KEYS
        }
    by_slot_business: dict = {slot_name: {} for slot_name in LEADERBOARD_SLOTS}
    for r in slot_rows:
        bid = r["_id"]["business_id"]
        slot_name = r["_id"].get("slot")
        if slot_name not in by_slot_business:
            continue
        by_slot_business[slot_name][bid] = {
            key: int(r.get(key, 0))
            for key in LEADERBOARD_METRIC_EVENT_KEYS
        }
    by_vibe: dict = {}
    for r in vibe_rows:
        vibe_name = r["_id"] or "unknown"
        by_vibe[vibe_name] = {
            key: int(r.get(key, 0))
            for key in LEADERBOARD_METRIC_EVENT_KEYS
        }

    # attach business names + sponsor tier
    biz_ids = list(by_biz.keys())
    businesses = await db.businesses.find(
        {"id": {"$in": biz_ids}}, {"_id": 0, "id": 1, "name": 1, "sponsor_tier": 1}
    ).to_list(1000)
    name_map = {b["id"]: b["name"] for b in businesses}
    tier_map = {b["id"]: b.get("sponsor_tier", "none") for b in businesses}
    all_business_breakdown = [
        _leaderboard_row(
            bid,
            counts,
            name=name_map.get(bid, bid or "(deleted)"),
            sponsor_tier=tier_map.get(bid, "none"),
        )
        for bid, counts in by_biz.items()
    ]
    all_business_breakdown.sort(key=lambda row: (-row.get("total_engagement", 0), -row.get("appearances", 0), row.get("name", "")))
    business_breakdown = all_business_breakdown[:ADMIN_ANALYTICS_BUSINESS_BREAKDOWN_LIMIT]
    totals_source = {}
    for row in all_business_breakdown:
        for key in LEADERBOARD_METRIC_EVENT_KEYS:
            totals_source[key] = totals_source.get(key, 0) + row.get(key, 0)
    usage_totals = await _homepage_visit_usage_metrics(days=days, city_slug=city_slug)
    totals = {
        **_metric_aliases(totals_source),
        **usage_totals,
    }

    sponsor_rollup: dict = {}
    for row in all_business_breakdown:
        tier = row.get("sponsor_tier") or "none"
        counts = sponsor_rollup.setdefault(tier, {})
        for key in LEADERBOARD_METRIC_EVENT_KEYS:
            counts[key] = counts.get(key, 0) + row.get(key, 0)
    sponsor_performance = []
    for tier in ["platinum", "gold", "silver", "none"]:
        if tier in sponsor_rollup:
            sponsor_performance.append({
                "tier": tier,
                **sponsor_rollup[tier],
                **_metric_aliases(sponsor_rollup[tier]),
            })

    total_events = await db.analytics_events.count_documents(base_match)
    slot_leaderboards = {
        slot_name: sorted(
            [
                _leaderboard_row(
                    bid,
                    counts,
                    name=name_map.get(bid, bid or "(deleted)"),
                    sponsor_tier=tier_map.get(bid, "none"),
                )
                for bid, counts in slot_counts.items()
            ],
            key=lambda row: (-row.get("total_engagement", 0), -row.get("appearances", 0), row.get("name", "")),
        )[:ADMIN_ANALYTICS_SLOT_LEADERBOARD_LIMIT]
        for slot_name, slot_counts in by_slot_business.items()
    }
    vibe_breakdown = sorted(
        [
            {
                "vibe": vibe_name,
                **counts,
                **_metric_aliases(counts),
            }
            for vibe_name, counts in by_vibe.items()
        ],
        key=lambda row: (-row.get("total_engagement", 0), row.get("vibe", "")),
    )
    top_businesses_by_total_engagement = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("total_engagement", 0), -row.get("business_appearance", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_locked_in_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("locked_in", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_saved_in_final_move_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("saved_in_final_move", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_website_click_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("website_clicks", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_directions_click_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("directions_clicks", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_ticket_click_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("ticket_clicks", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_phone_click_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("phone_clicks", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_click_through_businesses = sorted(
        all_business_breakdown,
        key=lambda row: (-row.get("total_click_through", 0), -row.get("total_engagement", 0), row.get("name", "")),
    )[:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]
    top_sponsor_businesses = [row for row in top_businesses_by_total_engagement if row.get("sponsor_tier") != "none"][:ADMIN_ANALYTICS_LEADERBOARD_LIMIT]

    return {
        "total_events": total_events,
        "filters": {
            "days": "all" if _normalize_analytics_days(days) is None else str(_normalize_analytics_days(days)),
            "city_slug": city_slug or "",
            "vibe": vibe_filter or "",
            "slot": slot_filter or "",
        },
        "limits": {
            "slot_leaderboards": ADMIN_ANALYTICS_SLOT_LEADERBOARD_LIMIT,
            "leaderboards": ADMIN_ANALYTICS_LEADERBOARD_LIMIT,
            "business_breakdown": ADMIN_ANALYTICS_BUSINESS_BREAKDOWN_LIMIT,
        },
        "by_event_type": summary,
        "totals": totals,
        "by_category": [{"category_slug": r["_id"], "count": r["count"]} for r in cat_rows],
        "by_business": business_breakdown,
        "sponsor_performance": sponsor_performance,
        "slot_leaderboards": slot_leaderboards,
        "vibe_breakdown": vibe_breakdown,
        "top_businesses_by_total_engagement": top_businesses_by_total_engagement,
        "top_locked_in_businesses": top_locked_in_businesses,
        "top_saved_in_final_move_businesses": top_saved_in_final_move_businesses,
        "top_website_click_businesses": top_website_click_businesses,
        "top_directions_click_businesses": top_directions_click_businesses,
        "top_ticket_click_businesses": top_ticket_click_businesses,
        "top_phone_click_businesses": top_phone_click_businesses,
        "top_click_through_businesses": top_click_through_businesses,
        "top_sponsor_businesses": top_sponsor_businesses,
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
