"""Helpers for Tonight's Move page-level sponsorship."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from ticketmaster_events import city_timezone

TONIGHT_MOVE_SPONSORSHIP_PLACEMENT = "tonight_move"


def parse_city_datetime(value: str, city_slug: str) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=city_timezone(city_slug))
    return parsed


def sponsorship_is_active(record: dict, city_slug: str, now: Optional[datetime] = None) -> bool:
    if not record.get("active"):
        return False
    if record.get("placement") != TONIGHT_MOVE_SPONSORSHIP_PLACEMENT:
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
    return True


def active_tonight_move_sponsorship(records: Iterable[dict], city_slug: str,
                                    now: Optional[datetime] = None) -> Optional[dict]:
    active = [record for record in records if sponsorship_is_active(record, city_slug, now=now)]
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
