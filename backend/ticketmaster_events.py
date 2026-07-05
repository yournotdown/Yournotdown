"""Dry-run-first Ticketmaster Discovery API sync helpers."""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import time
import unicodedata
import uuid
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib import parse, request
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        return None


load_dotenv(Path(__file__).with_name(".env"))

TICKETMASTER_EVENTS_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
TICKETMASTER_SOURCE = "ticketmaster"
CITY_CONFIG = {
    "nashville": {"ticketmaster_city": "Nashville", "timezone": "America/Chicago"},
}
VENUE_ALIASES = {
    "3rd and lindsley": "3rd & Lindsley",
    "ole red nashville": "Ole Red",
}
EXCLUDED_EVENT_STATUSES = {"cancelled", "canceled", "offsale"}
DEFAULT_EVENT_START_GRACE_MINUTES = max(0, int(os.environ.get("EVENT_START_GRACE_MINUTES", "60")))
MUSIC_CLASSIFICATION_SEGMENT = "music"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def city_timezone(city_slug: str) -> ZoneInfo:
    config = supported_city_config(city_slug)
    return ZoneInfo(config["timezone"])


def supported_city_config(city_slug: str) -> dict:
    config = CITY_CONFIG.get(city_slug)
    if not config:
        raise ValueError(f"Unsupported city slug: {city_slug}")
    return config


def local_today(city_slug: str, now: Optional[datetime] = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(city_timezone(city_slug)).date().isoformat()


def utc_city_day_window(city_slug: str, local_date: str) -> tuple[str, str]:
    local_day = date.fromisoformat(local_date)
    zone = city_timezone(city_slug)
    start = datetime.combine(local_day, datetime_time.min, tzinfo=zone)
    end = start + timedelta(days=1)
    return (
        start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def normalize_venue_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return re.sub(r"^the ", "", normalized)


def canonical_venue_name(value: str) -> str:
    return VENUE_ALIASES.get(normalize_venue_name(value), value)


def businesses_by_normalized_venue(businesses: Iterable[dict]) -> dict[str, dict]:
    return {
        normalize_venue_name(business.get("name", "")): business
        for business in businesses
        if business.get("id") and normalize_venue_name(business.get("name", ""))
    }


def match_business_for_venue(venue_name: str, businesses: Iterable[dict]) -> Optional[dict]:
    return businesses_by_normalized_venue(businesses).get(normalize_venue_name(venue_name))


def event_is_on_local_date(event: dict, local_date: str) -> bool:
    return event.get("dates", {}).get("start", {}).get("localDate") == local_date


def events_by_business_id(events: Iterable[dict]) -> dict[str, dict]:
    by_business = {}
    for event in sorted(events, key=lambda row: (row.get("starts_at") or "", row.get("local_time") or "")):
        business_id = event.get("venue_business_id")
        if business_id and business_id not in by_business:
            by_business[business_id] = event
    return by_business


def businesses_by_id(businesses: Iterable[dict]) -> dict[str, dict]:
    return {
        business.get("id"): business
        for business in businesses
        if business.get("id")
    }


def attach_event_to_step(step: dict, events: dict[str, dict]) -> dict:
    if step.get("slot") not in {"entertainment", "late-night"}:
        return step
    business_id = (step.get("business") or {}).get("id")
    event = events.get(business_id)
    return {**step, "event": event} if event else step


def attach_events_to_businesses(businesses: Iterable[dict], events: Iterable[dict]) -> list[dict]:
    by_business = events_by_business_id(events)
    attached = []
    for business in businesses:
        event = by_business.get(business.get("id"))
        attached.append({**business, "event": event} if event else dict(business))
    return attached


def eligible_public_businesses(businesses: Iterable[dict], events: Iterable[dict]) -> list[dict]:
    return attach_events_to_businesses(businesses, events)


def normalized_event_status(value: str) -> str:
    return (value or "").strip().lower()


def event_has_excluded_status(event: dict) -> bool:
    return normalized_event_status(event.get("status", "")) in EXCLUDED_EVENT_STATUSES


def event_is_eligible(event: dict, city_slug: str, now: Optional[datetime] = None,
                      grace_minutes: int = DEFAULT_EVENT_START_GRACE_MINUTES) -> bool:
    if event_has_excluded_status(event):
        return False

    local_date = event.get("local_date")
    if not local_date:
        return False

    current = now or datetime.now(timezone.utc)
    today = local_today(city_slug, now=current)
    if local_date > today:
        return True
    if local_date < today:
        return False

    local_time = event.get("local_time")
    if not local_time:
        return True

    try:
        start_local = datetime.combine(
            date.fromisoformat(local_date),
            datetime_time.fromisoformat(local_time),
            tzinfo=city_timezone(city_slug),
        )
    except ValueError:
        return True

    grace_delta = timedelta(minutes=max(0, grace_minutes))
    return current.astimezone(city_timezone(city_slug)) <= start_local + grace_delta


def eligible_city_events(events: Iterable[dict], city_slug: str, now: Optional[datetime] = None,
                         grace_minutes: int = DEFAULT_EVENT_START_GRACE_MINUTES) -> list[dict]:
    return [
        event for event in events
        if event_is_eligible(event, city_slug, now=now, grace_minutes=grace_minutes)
    ]


def event_classification_segment(event: dict) -> str:
    return normalized_event_status(event.get("classification_segment", ""))


def event_classification_genre(event: dict) -> str:
    return normalized_event_status(event.get("classification_genre", ""))


def event_classification_subgenre(event: dict) -> str:
    return normalized_event_status(event.get("classification_subgenre", ""))


def business_supports_live_music_event(business: dict) -> bool:
    slots = set(business.get("slots") or [])
    tags = set(business.get("tags") or [])
    return (
        business.get("category_slug") == "live-music"
        or "live_music" in tags
        or "concerts" in tags
        or ("entertainment" in slots and "live_music" in tags)
    )


def event_is_ticketmaster_music(event: dict, business: Optional[dict] = None) -> bool:
    if normalized_event_status(event.get("source", "")) != TICKETMASTER_SOURCE:
        return False

    segment = event_classification_segment(event)
    if segment:
        return segment == MUSIC_CLASSIFICATION_SEGMENT

    return bool(business and business_supports_live_music_event(business))


def eligible_ticketmaster_music_events(events: Iterable[dict], businesses: Iterable[dict]) -> list[dict]:
    business_lookup = businesses_by_id(businesses)
    return [
        dict(event)
        for event in sorted(events, key=lambda row: (row.get("starts_at") or "", row.get("local_time") or "", row.get("title") or ""))
        if event_is_ticketmaster_music(event, business_lookup.get(event.get("venue_business_id")))
    ]


def itinerary_event_pick(candidates: Iterable[dict], events: Iterable[dict], exclude_business_ids: set[str],
                         exclude_event_ids: set[str]) -> tuple[Optional[dict], Optional[dict]]:
    candidate_list = list(candidates)
    event_lookup = events_by_business_id(events)
    for business in candidate_list:
        event = event_lookup.get(business.get("id"))
        if not event:
            continue
        event_id = event.get("external_event_id") or event.get("id")
        if business.get("id") in exclude_business_ids or event_id in exclude_event_ids:
            continue
        return business, event
    return None, None


def primary_classification(event: dict) -> dict:
    classifications = event.get("classifications") or []
    return classifications[0] if classifications else {}


def ticketmaster_event_document(event: dict, city_slug: str, businesses: Iterable[dict],
                                synced_at: Optional[str] = None) -> dict:
    embedded = event.get("_embedded") or {}
    venue = ((embedded.get("venues") or [{}])[0]) or {}
    venue_name = canonical_venue_name(venue.get("name", ""))
    start = event.get("dates", {}).get("start", {}) or {}
    classification = primary_classification(event)
    matched_business = match_business_for_venue(venue_name, businesses)
    timestamp = synced_at or now_iso()
    return {
        "id": str(uuid.uuid4()),
        "city_slug": city_slug,
        "venue_name": venue_name,
        "venue_business_id": matched_business.get("id") if matched_business else None,
        "external_event_id": event.get("id", ""),
        "source": TICKETMASTER_SOURCE,
        "title": event.get("name", ""),
        "performers": [
            attraction["name"]
            for attraction in embedded.get("attractions") or []
            if attraction.get("name")
        ],
        "starts_at": start.get("dateTime"),
        "local_date": start.get("localDate"),
        "local_time": start.get("localTime"),
        "ticket_url": event.get("url", ""),
        "image_url": select_event_image(event.get("images") or []),
        "status": (event.get("dates", {}).get("status") or {}).get("code", ""),
        "classification_segment": ((classification.get("segment") or {}).get("name")) or "",
        "classification_genre": ((classification.get("genre") or {}).get("name")) or "",
        "classification_subgenre": ((classification.get("subGenre") or {}).get("name")) or "",
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def normalized_ticket_url(value: str) -> str:
    if not value:
        return ""
    parts = parse.urlsplit(value)
    return parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def deduplicate_event_documents(documents: Iterable[dict]) -> list[dict]:
    unique = []
    seen_external_ids = set()
    seen_ticket_urls = set()
    for document in documents:
        external_key = (document.get("source"), document.get("external_event_id"))
        ticket_url = normalized_ticket_url(document.get("ticket_url", ""))
        if external_key in seen_external_ids or (ticket_url and ticket_url in seen_ticket_urls):
            continue
        seen_external_ids.add(external_key)
        if ticket_url:
            seen_ticket_urls.add(ticket_url)
        unique.append(document)
    return unique


def select_event_image(images: Iterable[dict]) -> str:
    candidates = [image for image in images if image.get("url")]
    if not candidates:
        return ""
    landscape = [image for image in candidates if image.get("ratio") == "16_9"]
    return max(landscape or candidates, key=lambda image: image.get("width") or 0)["url"]


class TicketmasterClient:
    def __init__(self, api_key: Optional[str] = None, opener=None, max_attempts: int = 3,
                 retry_delay_seconds: float = 0.25, request_timeout_seconds: float = 10,
                 sleeper=None):
        self.api_key = api_key or os.environ.get("TICKETMASTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("TICKETMASTER_API_KEY must be set")
        self.opener = opener or request.urlopen
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.sleeper = sleeper or time.sleep

    def events_for_date(self, city_slug: str, local_date: str) -> list[dict]:
        config = supported_city_config(city_slug)
        start_date_time, end_date_time = utc_city_day_window(city_slug, local_date)
        query = parse.urlencode({
            "apikey": self.api_key,
            "city": config["ticketmaster_city"],
            "countryCode": "US",
            "startDateTime": start_date_time,
            "endDateTime": end_date_time,
            "includeTBA": "no",
            "includeTBD": "no",
            "size": 200,
            "sort": "date,asc",
        })
        payload = self._get_json(f"{TICKETMASTER_EVENTS_URL}?{query}")
        return (payload.get("_embedded") or {}).get("events") or []

    def _get_json(self, url: str) -> dict:
        for attempt in range(self.max_attempts):
            try:
                with self.opener(url, timeout=self.request_timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if exc.code != 504 or attempt + 1 == self.max_attempts:
                    raise
            except (TimeoutError, socket.timeout):
                if attempt + 1 == self.max_attempts:
                    raise
            except URLError as exc:
                if not isinstance(exc.reason, (TimeoutError, socket.timeout)) or attempt + 1 == self.max_attempts:
                    raise
            self.sleeper(self.retry_delay_seconds)
        raise RuntimeError("Ticketmaster retry loop exhausted")


def dry_run_sync(client: TicketmasterClient, businesses: Iterable[dict], city_slug: str = "nashville",
                 local_date: Optional[str] = None) -> dict:
    sync_date = local_date or local_today(city_slug)
    business_rows = list(businesses)
    synced_at = now_iso()
    fetched_documents = [
        ticketmaster_event_document(event, city_slug, business_rows, synced_at=synced_at)
        for event in client.events_for_date(city_slug, sync_date)
        if event_is_on_local_date(event, sync_date)
    ]
    documents = deduplicate_event_documents(fetched_documents)
    return {
        "mode": "dry-run",
        "city_slug": city_slug,
        "local_date": sync_date,
        "businesses_loaded": len(business_rows),
        "fetched": len(fetched_documents),
        "deduplicated": len(documents),
        "duplicates_removed": len(fetched_documents) - len(documents),
        "matched": sum(bool(document["venue_business_id"]) for document in documents),
        "unmatched": sum(not document["venue_business_id"] for document in documents),
        "events": documents,
    }


def date_range_sync_report(client: TicketmasterClient, businesses: Iterable[dict], city_slug: str = "nashville",
                           days: int = 2, start_date: Optional[str] = None) -> dict:
    if not 1 <= days <= 7:
        raise ValueError("days must be between 1 and 7")
    first_date = date.fromisoformat(start_date or local_today(city_slug))
    business_rows = list(businesses)
    reports = [
        dry_run_sync(client, business_rows, city_slug, (first_date + timedelta(days=offset)).isoformat())
        for offset in range(days)
    ]
    fetched = sum(report["fetched"] for report in reports)
    documents = deduplicate_event_documents(
        document
        for report in reports
        for document in report["events"]
    )
    return {
        "mode": "dry-run",
        "city_slug": city_slug,
        "dates": [report["local_date"] for report in reports],
        "fetched": fetched,
        "after_dedupe": len(documents),
        "duplicates_removed": fetched - len(documents),
        "would_upsert": len(documents),
        "matched": sum(bool(document["venue_business_id"]) for document in documents),
        "unmatched": sum(not document["venue_business_id"] for document in documents),
        "events": documents,
    }


def event_upsert(document: dict) -> tuple[dict, dict]:
    mutable_fields = {key: value for key, value in document.items() if key not in {"id", "created_at"}}
    return (
        {"source": document["source"], "external_event_id": document["external_event_id"]},
        {
            "$set": mutable_fields,
            "$setOnInsert": {"id": document["id"], "created_at": document["created_at"]},
        },
    )


def expiration_cleanup_query(city_slug: str, now: Optional[datetime] = None) -> dict:
    return {
        "source": TICKETMASTER_SOURCE,
        "city_slug": city_slug,
        "local_date": {"$lt": local_today(city_slug, now=now)},
    }


def api_sync_response(report: dict, apply_summary: Optional[dict] = None) -> dict:
    response = {
        "success": True,
        "mode": "apply" if apply_summary is not None else "dry-run",
        "dates": report["dates"],
        "fetched": report["fetched"],
        "after_dedupe": report["after_dedupe"],
        "would_upsert": report["would_upsert"],
        "duplicates_removed": report["duplicates_removed"],
        "matched": report["matched"],
        "unmatched": report["unmatched"],
        "sample_events": report["events"][:20],
    }
    if apply_summary is None:
        return response
    return {
        **response,
        "upserted": apply_summary["upserted"],
        "updated": apply_summary["modified"],
        "removed": apply_summary["expired_deleted"],
        "expiration_cutoff": apply_summary["expiration_cutoff"],
    }


def validate_apply_confirmation(apply: bool, confirm: Optional[str]) -> None:
    if apply and confirm != "APPROVE":
        raise ValueError("Apply requires confirm=APPROVE")


def apply_event_sync(collection, report: dict, city_slug: str, now: Optional[datetime] = None) -> dict:
    upserted = 0
    modified = 0
    for document in report["events"]:
        selector, update = event_upsert(document)
        result = collection.update_one(
            selector,
            update,
            upsert=True,
        )
        upserted += int(result.upserted_id is not None)
        modified += result.modified_count
    cleanup_query = expiration_cleanup_query(city_slug, now=now)
    cleanup = collection.delete_many(cleanup_query)
    return {
        "upserted": upserted,
        "modified": modified,
        "expired_deleted": cleanup.deleted_count,
        "expiration_cutoff": cleanup_query["local_date"]["$lt"],
    }


def mongo_collections():
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL and DB_NAME must be set when --apply is used")
    from pymongo import MongoClient

    client = MongoClient(mongo_url)
    database = client[db_name]
    return client, database.businesses, database.city_events


def require_apply_approval(input_fn=input) -> None:
    approval = input_fn("Type APPROVE to write Ticketmaster events to Mongo: ")
    if approval != "APPROVE":
        raise RuntimeError("Apply cancelled: approval text did not match APPROVE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="nashville", choices=sorted(CITY_CONFIG))
    parser.add_argument("--date", help="Local event date in YYYY-MM-DD format")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and report events without writing to Mongo")
    parser.add_argument("--apply", action="store_true", help="Upsert events and remove expired Ticketmaster rows")
    args = parser.parse_args()
    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply cannot be used together")
    if args.date:
        date.fromisoformat(args.date)
    if not args.apply:
        print(json.dumps(dry_run_sync(TicketmasterClient(), [], args.city, args.date), indent=2))
        return

    require_apply_approval()
    mongo_client, business_collection, event_collection = mongo_collections()
    try:
        businesses = list(business_collection.find(
            {"imported_status": "approved"},
            {"_id": 0, "id": 1, "name": 1},
        ))
        report = dry_run_sync(TicketmasterClient(), businesses, args.city, args.date)
        report["mode"] = "apply"
        report["apply"] = apply_event_sync(event_collection, report, args.city)
        print(json.dumps(report, indent=2))
    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()
