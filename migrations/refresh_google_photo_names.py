#!/usr/bin/env python3
"""Refresh Google Places photo resource names for imported businesses.

Default mode is dry-run. Use --apply to write updates.

Environment variables:
- DEST_MONGO_URL
- DEST_DB
- GOOGLE_PLACES_API_KEY
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError

GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1"
DEFAULT_COLLECTION = "businesses"
DEFAULT_SLEEP_SECONDS = 0.2
DEFAULT_SAMPLE_LIMIT = 5
FIELD_MASK = "id,displayName,photos"
REFRESHED_AT_FIELD = "google_photo_names_refreshed_at"
REQUIRED_ENV_VARS = ("DEST_MONGO_URL", "DEST_DB", "GOOGLE_PLACES_API_KEY")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Mongo collection to scan (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update google_photo_names in Mongo",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of businesses to scan after filtering",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Delay between Google calls (default: {DEFAULT_SLEEP_SECONDS})",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=DEFAULT_SAMPLE_LIMIT,
        help=f"Dry-run sample count (default: {DEFAULT_SAMPLE_LIMIT})",
    )
    return parser.parse_args()


def sanitize_error_text(text: str) -> str:
    return " ".join((text or "").split())[:200]


def extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if message:
                return sanitize_error_text(str(message))
        if error_payload:
            return sanitize_error_text(str(error_payload))
    return sanitize_error_text(response.text or response.reason or "Unknown error")


def fetch_fresh_photo_names(place_id: str, api_key: str) -> tuple[list[str], str]:
    response = requests.get(
        f"{GOOGLE_PLACES_API_URL}/places/{place_id}",
        headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK},
        timeout=15,
    )
    if response.status_code >= 400:
        detail = extract_error_detail(response)
        raise RuntimeError(f"status={response.status_code} detail={detail}")
    payload = response.json()
    photos = payload.get("photos") or []
    names = [photo.get("name") for photo in photos if isinstance(photo, dict) and photo.get("name")]
    return names, str((payload.get("displayName") or {}).get("text") or "")


def format_sample(business_id: str, place_id: str, business_name: str, photo_names: list[str]) -> str:
    sample_names = photo_names[:2]
    return (
        f"id={business_id} "
        f"place_id={place_id} "
        f"name={business_name!r} "
        f"fresh_photo_count={len(photo_names)} "
        f"sample_names={sample_names}"
    )


def main() -> int:
    args = parse_args()
    for env_name in REQUIRED_ENV_VARS:
        require_env(env_name)

    dest_url = require_env("DEST_MONGO_URL")
    dest_db_name = require_env("DEST_DB")
    api_key = require_env("GOOGLE_PLACES_API_KEY")

    if args.limit < 0:
        raise RuntimeError("--limit must be >= 0")
    if args.sleep_seconds < 0:
        raise RuntimeError("--sleep-seconds must be >= 0")
    if args.sample_limit < 0:
        raise RuntimeError("--sample-limit must be >= 0")

    client = MongoClient(dest_url)
    try:
        collection = client[dest_db_name][args.collection]
        query = {"google_place_id": {"$exists": True, "$nin": [None, ""]}}
        projection = {"_id": 1, "id": 1, "name": 1, "google_place_id": 1, "google_photo_names": 1}
        cursor = collection.find(query, projection).sort("id", 1)
        if args.limit:
            cursor = cursor.limit(args.limit)

        scanned = 0
        with_place_id = 0
        with_fresh_photos = 0
        updated = 0
        unchanged = 0
        failures = 0
        samples: list[str] = []

        mode = "apply" if args.apply else "dry-run"
        print(f"mode={mode}")
        print(f"collection={args.collection}")

        for business in cursor:
            scanned += 1
            place_id = str(business.get("google_place_id") or "").strip()
            if not place_id:
                continue
            with_place_id += 1

            try:
                fresh_photo_names, display_name = fetch_fresh_photo_names(place_id, api_key)
            except requests.RequestException as exc:
                failures += 1
                print(
                    f"failure id={business.get('id')!r} place_id={place_id} "
                    f"type={exc.__class__.__name__}",
                    file=sys.stderr,
                )
            except RuntimeError as exc:
                failures += 1
                print(
                    f"failure id={business.get('id')!r} place_id={place_id} {exc}",
                    file=sys.stderr,
                )
            else:
                if fresh_photo_names:
                    with_fresh_photos += 1
                    if len(samples) < args.sample_limit:
                        samples.append(
                            format_sample(
                                str(business.get("id") or business.get("_id")),
                                place_id,
                                display_name or str(business.get("name") or ""),
                                fresh_photo_names,
                            )
                        )

                existing_photo_names = business.get("google_photo_names") or []
                if fresh_photo_names != existing_photo_names:
                    if args.apply:
                        update_result = collection.update_one(
                            {"_id": business["_id"]},
                            {
                                "$set": {
                                    "google_photo_names": fresh_photo_names,
                                    REFRESHED_AT_FIELD: now_iso(),
                                }
                            },
                        )
                        updated += update_result.modified_count
                    else:
                        updated += 1
                else:
                    unchanged += 1

            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

        print(f"businesses_scanned={scanned}")
        print(f"businesses_with_google_place_id={with_place_id}")
        print(f"businesses_with_fresh_photos={with_fresh_photos}")
        print(f"businesses_needing_update={updated}")
        print(f"businesses_unchanged={unchanged}")
        print(f"failures={failures}")
        if samples:
            print("sample_fresh_photo_names:")
            for sample in samples:
                print(sample)
        if not args.apply:
            print("No writes were made.")
        return 0 if failures == 0 else 1
    except PyMongoError as exc:
        raise RuntimeError(f"Mongo error: {exc.__class__.__name__}") from exc
    finally:
        client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
