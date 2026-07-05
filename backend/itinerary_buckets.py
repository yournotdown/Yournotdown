"""Pure helpers for mapping business slots to admin-facing itinerary buckets."""
from __future__ import annotations

from typing import Iterable


SLOT_TO_ITINERARY_BUCKET = {
    "dinner": "dinner",
    "drinks": "drinks",
    "entertainment": "live_music",
    "late-night": "late_night",
}


def itinerary_buckets_for_business(business: dict) -> list[str]:
    buckets: list[str] = []
    for slot in business.get("slots") or []:
        bucket = SLOT_TO_ITINERARY_BUCKET.get(slot)
        if bucket and bucket not in buckets:
            buckets.append(bucket)
    return buckets


def annotate_itinerary_buckets(businesses: Iterable[dict]) -> list[dict]:
    return [
        {**business, "itinerary_buckets": itinerary_buckets_for_business(business)}
        for business in businesses
    ]
