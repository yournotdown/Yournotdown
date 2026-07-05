"""Helpers for admin-featured live music events in Tonight's Move."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable, Optional

from ticketmaster_events import city_timezone, event_is_eligible, local_today

FEATURED_LIVE_MUSIC_SLOT = "live_music"
LIVE_MUSIC_EVENT_MODE_NORMAL = "normal"
LIVE_MUSIC_EVENT_MODE_TICKETMASTER = "ticketmaster"
LIVE_MUSIC_EVENT_MODE_TICKETMASTER_PREFERRED = "ticketmaster_preferred"
LIVE_MUSIC_EVENT_MODES = {
    LIVE_MUSIC_EVENT_MODE_NORMAL,
    LIVE_MUSIC_EVENT_MODE_TICKETMASTER,
    LIVE_MUSIC_EVENT_MODE_TICKETMASTER_PREFERRED,
}


def parse_city_datetime(value: str, city_slug: str) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=city_timezone(city_slug))
    return parsed


def featured_event_is_active(record: dict, city_slug: str, now: Optional[datetime] = None) -> bool:
    if not record.get("active"):
        return False
    if record.get("slot") != FEATURED_LIVE_MUSIC_SLOT:
        return False
    if record.get("city_slug") != city_slug:
        return False

    current = now or datetime.now(timezone.utc)
    active_from = parse_city_datetime(record.get("active_from", ""), city_slug)
    active_until = parse_city_datetime(record.get("active_until", ""), city_slug)
    if active_from and current < active_from.astimezone(timezone.utc):
        return False
    if active_until and current > active_until.astimezone(timezone.utc):
        return False

    local_date = record.get("local_date")
    if local_date:
        if local_date != local_today(city_slug, now=current):
            return False
        return event_is_eligible(
            {
                "local_date": local_date,
                "local_time": record.get("local_time"),
                "status": "",
            },
            city_slug,
            now=current,
        )
    return True


def active_featured_live_music_event(records: Iterable[dict], city_slug: str,
                                     now: Optional[datetime] = None) -> Optional[dict]:
    active = [
        record
        for record in records
        if featured_event_is_active(record, city_slug, now=now)
    ]
    if not active:
        return None
    return sorted(
        active,
        key=lambda record: (
            record.get("priority") or 0,
            record.get("updated_at") or "",
            record.get("created_at") or "",
        ),
        reverse=True,
    )[0]


def featured_live_music_business(record: dict) -> dict:
    business_id = record.get("venue_business_id") or f"featured-live-music-{record.get('id') or uuid.uuid4()}"
    return {
        "id": business_id,
        "name": record.get("venue_name") or record.get("title") or "Live Music",
        "description": record.get("description") or record.get("internal_notes") or "",
        "image_url": record.get("image_url", ""),
        "image_path": None,
        "website": record.get("ticket_url", ""),
        "phone": "",
        "address": "",
        "category_slug": "live-music",
        "city_slug": record.get("city_slug", "nashville"),
        "featured": True,
        "sponsor_tier": "none",
        "slots": ["entertainment"],
        "tags": ["live_music"],
    }


def featured_live_music_step_event(record: dict) -> dict:
    ticket_url = record.get("ticket_url") or record.get("booking_url") or record.get("purchase_url") or ""
    return {
        "id": record.get("id", ""),
        "external_event_id": record.get("id", ""),
        "source": "admin_featured_event",
        "title": record.get("title", ""),
        "venue_name": record.get("venue_name", ""),
        "local_date": record.get("local_date"),
        "local_time": record.get("local_time"),
        "ticket_url": ticket_url,
        "booking_url": ticket_url,
        "purchase_url": ticket_url,
        "image_url": record.get("image_url", ""),
        "description": record.get("description", ""),
        "cta_label": record.get("cta_label") or "Buy Tickets",
    }


def normalize_live_music_event_mode(value: str) -> str:
    mode = (value or LIVE_MUSIC_EVENT_MODE_NORMAL).strip().lower()
    return mode if mode in LIVE_MUSIC_EVENT_MODES else LIVE_MUSIC_EVENT_MODE_NORMAL
