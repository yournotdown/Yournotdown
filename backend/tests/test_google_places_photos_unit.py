"""Unit tests for the backend-only Google Places photo proxy."""
import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "yournotdown_test")

import server  # noqa: E402
from google_places_photos import (  # noqa: E402
    GOOGLE_PLACES_PHOTO_MAX_WIDTH,
    describe_google_places_request_error,
    fetch_google_places_photo,
    google_places_photo_media_url,
    redact_google_api_key,
)

PHOTO_NAME = "places/ChIJ_example-123/photos/photo_reference-456"


def test_google_places_photo_media_url_is_validated_and_unkeyed():
    url = google_places_photo_media_url(PHOTO_NAME)
    assert url == f"https://places.googleapis.com/v1/{PHOTO_NAME}/media"
    assert "key=" not in url


@pytest.mark.parametrize("photo_name", [
    "https://example.com/image.jpg",
    "places/example/photos/reference/extra",
    "../places/example/photos/reference",
])
def test_google_places_photo_media_url_rejects_untrusted_paths(photo_name):
    with pytest.raises(ValueError, match="Invalid Google Places photo name"):
        google_places_photo_media_url(photo_name)


def test_fetch_google_places_photo_sends_key_only_to_google(monkeypatch):
    get = Mock(return_value=Mock())
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "backend-secret")
    monkeypatch.setattr("google_places_photos.requests.get", get)

    fetch_google_places_photo(PHOTO_NAME)

    get.assert_called_once_with(
        f"https://places.googleapis.com/v1/{PHOTO_NAME}/media",
        params={"maxWidthPx": GOOGLE_PLACES_PHOTO_MAX_WIDTH, "key": "backend-secret"},
        stream=True,
        timeout=15,
    )


def test_fetch_google_places_photo_requires_backend_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_PLACES_API_KEY is not configured"):
        fetch_google_places_photo(PHOTO_NAME)


def test_redact_google_api_key_masks_key_param():
    url = "https://places.googleapis.com/v1/places/example/media?maxWidthPx=1200&key=secret-key"
    assert redact_google_api_key(url) == (
        "https://places.googleapis.com/v1/places/example/media?maxWidthPx=1200&key=%5BREDACTED%5D"
    )


def test_describe_google_places_request_error_redacts_key_and_uses_api_message():
    response = Mock()
    response.status_code = 400
    response.json.return_value = {"error": {"message": "Invalid photo name"}}
    response.text = '{"error":{"message":"Invalid photo name"}}'
    request = Mock()
    request.method = "GET"
    request.url = (
        "https://places.googleapis.com/v1/places/example/media"
        "?maxWidthPx=1200&key=backend-secret"
    )
    error = requests.HTTPError("boom", response=response, request=request)

    summary = describe_google_places_request_error(error)

    assert "status=400" in summary
    assert "Invalid photo name" in summary
    assert "backend-secret" not in summary
    assert "key=%5BREDACTED%5D" in summary


def test_photo_proxy_streams_bytes_without_exposing_key(monkeypatch):
    upstream = Mock()
    upstream.headers = {"content-type": "image/webp"}
    upstream.iter_content.return_value = iter([b"photo-", b"bytes"])
    monkeypatch.setattr(server, "fetch_google_places_photo", Mock(return_value=upstream))
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(businesses=_FakeBusinesses({"_id": "mongo-id"})),
    )

    response = asyncio.run(server.google_places_photo(photo_name=PHOTO_NAME))
    body = asyncio.run(_read_body(response))

    assert body == b"photo-bytes"
    assert response.media_type == "image/webp"
    assert "location" not in response.headers
    assert "key=" not in str(response.headers)


def test_photo_proxy_can_resolve_first_photo_by_business_id(monkeypatch):
    upstream = Mock()
    upstream.headers = {"content-type": "image/jpeg"}
    upstream.iter_content.return_value = iter([b"image"])
    fetch = Mock(return_value=upstream)
    monkeypatch.setattr(server, "fetch_google_places_photo", fetch)
    monkeypatch.setattr(
        server,
        "db",
        SimpleNamespace(businesses=_FakeBusinesses({"google_photo_names": [PHOTO_NAME, "unused"]})),
    )

    response = asyncio.run(server.google_places_photo(business_id="business-123"))
    body = asyncio.run(_read_body(response))

    assert body == b"image"
    fetch.assert_called_once_with(PHOTO_NAME)


async def _read_body(response):
    return b"".join([chunk async for chunk in response.body_iterator])


class _FakeBusinesses:
    def __init__(self, business):
        self.business = business

    async def find_one(self, query, projection):
        if "google_photo_names" in query:
            assert query == {"google_photo_names": PHOTO_NAME, "imported_status": "approved"}
            assert projection == {"_id": 1}
        else:
            assert query == {"id": "business-123", "imported_status": "approved"}
            assert projection == {"_id": 0, "google_photo_names": 1}
        return self.business
