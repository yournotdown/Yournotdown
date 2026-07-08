"""Validated Google Places photo proxy helpers."""
import os
import re
from urllib.parse import parse_qsl
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import requests

GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1"
GOOGLE_PLACES_PHOTO_MAX_WIDTH = 1200
GOOGLE_PLACES_PHOTO_MIN_WIDTH = 240
PHOTO_NAME_PATTERN = re.compile(r"^places/[A-Za-z0-9_-]+/photos/[A-Za-z0-9_-]+$")


def google_places_photo_media_url(photo_name: str) -> str:
    """Build an unkeyed Google Places media URL for a validated photo resource."""
    if not PHOTO_NAME_PATTERN.fullmatch(photo_name):
        raise ValueError("Invalid Google Places photo name")
    return f"{GOOGLE_PLACES_API_URL}/{quote(photo_name, safe='/')}/media"


def normalize_google_places_photo_width(max_width_px=None) -> int:
    """Clamp requested Google photo widths to a safe backend-served range."""
    if max_width_px in (None, ""):
        return GOOGLE_PLACES_PHOTO_MAX_WIDTH
    try:
        width = int(max_width_px)
    except (TypeError, ValueError):
        return GOOGLE_PLACES_PHOTO_MAX_WIDTH
    return max(GOOGLE_PLACES_PHOTO_MIN_WIDTH, min(width, GOOGLE_PLACES_PHOTO_MAX_WIDTH))


def fetch_google_places_photo(photo_name: str, max_width_px=None):
    """Fetch a Google Places photo while keeping the API key on the backend."""
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY is not configured")
    return requests.get(
        google_places_photo_media_url(photo_name),
        params={"maxWidthPx": normalize_google_places_photo_width(max_width_px), "key": api_key},
        stream=True,
        timeout=15,
    )


def redact_google_api_key(url: str) -> str:
    """Redact Google API key query params from a URL before logging."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    redacted_query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() == "key":
            redacted_query.append((key, "[REDACTED]"))
        else:
            redacted_query.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(redacted_query)))


def describe_google_places_request_error(error: requests.RequestException) -> str:
    """Return a sanitized one-line summary for Google Places request failures."""
    response = getattr(error, "response", None)
    request = getattr(error, "request", None)
    status_code = getattr(response, "status_code", None)
    method = getattr(request, "method", None) or "GET"
    url = redact_google_api_key(getattr(request, "url", "") or "")

    detail = ""
    if response is not None:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            error_payload = payload.get("error")
            if isinstance(error_payload, dict):
                detail = str(error_payload.get("message") or "").strip()
            elif error_payload:
                detail = str(error_payload).strip()
        if not detail:
            detail = (response.text or "").strip().replace("\n", " ")[:200]

    parts = []
    if status_code is not None:
        parts.append(f"status={status_code}")
    parts.append(f"method={method}")
    if url:
        parts.append(f"url={url}")
    if detail:
        parts.append(f"detail={detail}")
    return " ".join(parts) if parts else error.__class__.__name__
