"""Validated Google Places photo proxy helpers."""
import os
import re
from urllib.parse import quote

import requests

GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1"
GOOGLE_PLACES_PHOTO_MAX_WIDTH = 1200
PHOTO_NAME_PATTERN = re.compile(r"^places/[A-Za-z0-9_-]+/photos/[A-Za-z0-9_-]+$")


def google_places_photo_media_url(photo_name: str) -> str:
    """Build an unkeyed Google Places media URL for a validated photo resource."""
    if not PHOTO_NAME_PATTERN.fullmatch(photo_name):
        raise ValueError("Invalid Google Places photo name")
    return f"{GOOGLE_PLACES_API_URL}/{quote(photo_name, safe='/')}/media"


def fetch_google_places_photo(photo_name: str):
    """Fetch a Google Places photo while keeping the API key on the backend."""
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY is not configured")
    return requests.get(
        google_places_photo_media_url(photo_name),
        params={"maxWidthPx": GOOGLE_PLACES_PHOTO_MAX_WIDTH, "key": api_key},
        stream=True,
        timeout=15,
    )
