#!/usr/bin/env python3
"""Export catalog data from the production API into local JSON files.

Read-only behavior:
- Only performs HTTP GET requests.
- Never writes to Mongo.
- Never mutates production data.

Default API base:
- https://yournotdown.com/api

Environment variables:
- API_BASE_URL: optional override for the API base URL
- ADMIN_SESSION_TOKEN: optional bearer token for admin-only read endpoints

Notes:
- `categories` and `cities` use public endpoints.
- `businesses` uses `/admin/businesses` when `ADMIN_SESSION_TOKEN` is set so the
  export can include the full collection. Without that token, it falls back to
  the public `/businesses` endpoint per city, which only returns approved
  businesses.
- `city_events` is exported from the public `/events/today` endpoint for each
  city because no full read endpoint for the entire `city_events` collection was
  found in the local backend code.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable

import requests

DEFAULT_API_BASE = "https://yournotdown.com/api"
DEFAULT_COLLECTIONS = ("categories", "cities", "businesses", "city_events")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "emergent_export"
TIMEOUT_SECONDS = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collections",
        default=",".join(DEFAULT_COLLECTIONS),
        help="Comma-separated collections to export",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write exported JSON files into",
    )
    return parser.parse_args()


def parse_collections(value: str) -> list[str]:
    collections: list[str] = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if item not in DEFAULT_COLLECTIONS:
            valid = ", ".join(DEFAULT_COLLECTIONS)
            raise RuntimeError(f"Unsupported collection '{item}'. Valid values: {valid}")
        if item not in collections:
            collections.append(item)
    if not collections:
        raise RuntimeError("At least one collection must be requested")
    return collections


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    admin_session_token = os.environ.get("ADMIN_SESSION_TOKEN", "").strip()
    if admin_session_token:
        session.headers["Authorization"] = f"Bearer {admin_session_token}"
    return session


def get_json(
    session: requests.Session,
    api_base_url: str,
    path: str,
    *,
    params: dict | None = None,
) -> object:
    url = f"{api_base_url.rstrip('/')}/{path.lstrip('/')}"
    response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"GET {response.url} failed with {response.status_code}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"GET {response.url} did not return valid JSON") from exc


def ensure_list(name: str, value: object) -> list[dict]:
    if not isinstance(value, list):
        raise RuntimeError(f"Expected list payload for {name}, got {type(value).__name__}")
    for item in value:
        if not isinstance(item, dict):
            raise RuntimeError(f"Expected {name} items to be objects")
    return value


def export_categories(session: requests.Session, api_base_url: str) -> list[dict]:
    payload = get_json(session, api_base_url, "/categories")
    return ensure_list("categories", payload)


def export_cities(session: requests.Session, api_base_url: str) -> list[dict]:
    payload = get_json(session, api_base_url, "/cities")
    return ensure_list("cities", payload)


def export_businesses(session: requests.Session, api_base_url: str) -> list[dict]:
    admin_session_token = os.environ.get("ADMIN_SESSION_TOKEN", "").strip()
    if admin_session_token:
        payload = get_json(session, api_base_url, "/admin/businesses")
        return ensure_list("businesses", payload)

    cities = export_cities(session, api_base_url)
    businesses_by_id: dict[str, dict] = {}
    for city in cities:
        city_slug = city.get("slug")
        if not city_slug:
            continue
        payload = get_json(
            session,
            api_base_url,
            "/businesses",
            params={"city": city_slug, "limit": 5000},
        )
        for business in ensure_list("businesses", payload):
            business_id = str(business.get("id") or "")
            if business_id:
                businesses_by_id[business_id] = business

    print(
        "warning: businesses exported via public endpoints only; "
        "set ADMIN_SESSION_TOKEN to use /admin/businesses for a full export",
        file=sys.stderr,
    )
    return sorted(businesses_by_id.values(), key=lambda item: (item.get("city_slug", ""), item.get("order", 0), item.get("id", "")))


def export_city_events(session: requests.Session, api_base_url: str) -> list[dict]:
    cities = export_cities(session, api_base_url)
    events: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for city in cities:
        city_slug = city.get("slug")
        if not city_slug:
            continue
        payload = get_json(session, api_base_url, "/events/today", params={"city": city_slug})
        for event in ensure_list("city_events", payload):
            dedupe_key = (
                str(event.get("city_slug") or city_slug),
                str(event.get("source") or ""),
                str(event.get("external_event_id") or event.get("id") or ""),
            )
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            events.append(event)

    print(
        "warning: city_events exported from /events/today by city; "
        "no full read endpoint for the entire collection was found in local code",
        file=sys.stderr,
    )
    return sorted(events, key=lambda item: (item.get("city_slug", ""), item.get("local_date", ""), item.get("starts_at", ""), item.get("external_event_id", "")))


EXPORTERS: dict[str, Callable[[requests.Session, str], list[dict]]] = {
    "categories": export_categories,
    "cities": export_cities,
    "businesses": export_businesses,
    "city_events": export_city_events,
}


def write_json(output_dir: Path, collection_name: str, rows: list[dict]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{collection_name}.json"
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()
    collections = parse_collections(args.collections)
    output_dir = Path(args.output_dir).expanduser().resolve()
    api_base_url = os.environ.get("API_BASE_URL", DEFAULT_API_BASE).strip() or DEFAULT_API_BASE

    session = build_session()
    try:
        for collection_name in collections:
            rows = EXPORTERS[collection_name](session, api_base_url)
            output_path = write_json(output_dir, collection_name, rows)
            print(f"saved {collection_name} count={len(rows)} path={output_path}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
