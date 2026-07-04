#!/usr/bin/env python3
"""Backfill Google photo data for approved businesses still using Emergent image URLs.

Default mode is dry-run. Use --apply to write updates.

Environment variables:
- DEST_MONGO_URL
- DEST_DB
- GOOGLE_PLACES_API_KEY
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1"
DEFAULT_COLLECTION = "businesses"
DEFAULT_SLEEP_SECONDS = 0.2
FIELD_MASK = "id,displayName,photos"
REFRESHED_AT_FIELD = "google_photo_names_refreshed_at"
EMERGENT_IMAGE_SUBSTRING = "static.prod-images.emergentagent.com"
REQUIRED_ENV_VARS = ("DEST_MONGO_URL", "DEST_DB", "GOOGLE_PLACES_API_KEY")
SOURCE_JSON_PATH = Path(__file__).resolve().parent / "nashville_imports_only.json"

SAFE_SOURCE_NAME_BY_TARGET_NAME = {
    "Attaboy": "Attaboy",
    "The Patterson House": "The Patterson House",
    "Old Glory": "Old Glory",
    "Exit/In": "EXIT/IN",
    "The Basement East": "The Basement East",
    "Ryman Auditorium": "Ryman Auditorium",
    "Skull's Rainbow Room": "Skull's Rainbow Room",
}
UNTOUCHED_BUSINESSES = ("Bastion", "The Bluebird Cafe", "Santa's Pub")


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
        help="Actually update matched business records in Mongo",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"Delay between Google calls (default: {DEFAULT_SLEEP_SECONDS})",
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
    photo_names = [photo.get("name") for photo in photos if isinstance(photo, dict) and photo.get("name")]
    display_name = str((payload.get("displayName") or {}).get("text") or "")
    return photo_names, display_name


def load_source_place_ids() -> dict[str, str]:
    try:
        rows = json.loads(SOURCE_JSON_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Source JSON not found: {SOURCE_JSON_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in source file: {SOURCE_JSON_PATH}") from exc

    if not isinstance(rows, list):
        raise RuntimeError(f"Expected a JSON array in {SOURCE_JSON_PATH}")

    by_name = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        place_id = str(row.get("google_place_id") or "").strip()
        if name and place_id:
            by_name[name] = place_id

    source_place_ids: dict[str, str] = {}
    missing_sources = []
    for target_name, source_name in SAFE_SOURCE_NAME_BY_TARGET_NAME.items():
        place_id = by_name.get(source_name, "")
        if not place_id:
            missing_sources.append(f"{target_name}<-{source_name}")
            continue
        source_place_ids[target_name] = place_id

    if missing_sources:
        joined = ", ".join(missing_sources)
        raise RuntimeError(f"Missing google_place_id in source JSON for: {joined}")

    return source_place_ids


def stringify_business_id(business: dict) -> str:
    return str(business.get("id") or business.get("_id"))


def build_conflict_summary_rows(rows: list[dict]) -> list[str]:
    summary = []
    for row in rows:
        summary.append(
            f"id={stringify_business_id(row)} name={str(row.get('name') or '').strip()!r}"
        )
    return summary


def main() -> int:
    args = parse_args()
    for env_name in REQUIRED_ENV_VARS:
        require_env(env_name)

    if args.sleep_seconds < 0:
        raise RuntimeError("--sleep-seconds must be >= 0")

    dest_url = require_env("DEST_MONGO_URL")
    dest_db_name = require_env("DEST_DB")
    api_key = require_env("GOOGLE_PLACES_API_KEY")
    source_place_ids = load_source_place_ids()

    client = MongoClient(dest_url)
    try:
        collection = client[dest_db_name][args.collection]
        query = {
            "imported_status": "approved",
            "image_url": {"$regex": EMERGENT_IMAGE_SUBSTRING},
        }
        projection = {
            "_id": 1,
            "id": 1,
            "name": 1,
            "image_url": 1,
            "google_place_id": 1,
            "google_photo_names": 1,
        }
        emergent_records = list(collection.find(query, projection).sort("name", 1))

        matched_records = []
        unmatched_records = []
        for business in emergent_records:
            name = str(business.get("name") or "").strip()
            if name in source_place_ids:
                matched_records.append(business)
            else:
                unmatched_records.append(business)

        mode = "apply" if args.apply else "dry-run"
        print(f"mode={mode}")
        print(f"collection={args.collection}")
        print(f"source_json={SOURCE_JSON_PATH.name}")
        print(f"total_emergent_image_url_records_found={len(emergent_records)}")
        print(f"matched_safe_records_count={len(matched_records)}")
        print(f"unmatched_records_count={len(unmatched_records)}")
        print("matched_safe_record_names=" + ", ".join(sorted(str(row.get("name") or "") for row in matched_records)))
        print("unmatched_record_names=" + ", ".join(sorted(str(row.get("name") or "") for row in unmatched_records)))
        print(
            "WARNING: intentionally left untouched: "
            + ", ".join(UNTOUCHED_BUSINESSES)
        )

        matched_source_place_ids = sorted(
            {source_place_ids[str(row.get("name") or "").strip()] for row in matched_records}
        )
        conflict_projection = {
            "_id": 1,
            "id": 1,
            "name": 1,
            "google_place_id": 1,
        }
        existing_google_backed_rows = list(
            collection.find(
                {"google_place_id": {"$in": matched_source_place_ids}},
                conflict_projection,
            )
        )
        existing_rows_by_place_id: dict[str, list[dict]] = {}
        for row in existing_google_backed_rows:
            place_id = str(row.get("google_place_id") or "").strip()
            if not place_id:
                continue
            existing_rows_by_place_id.setdefault(place_id, []).append(row)

        updated = 0
        skipped = 0
        failures = 0

        for business in matched_records:
            business_id = stringify_business_id(business)
            business_name = str(business.get("name") or "").strip()
            source_place_id = source_place_ids[business_name]
            existing_place_id = str(business.get("google_place_id") or "").strip()
            duplicate_conflict_rows = [
                row
                for row in existing_rows_by_place_id.get(source_place_id, [])
                if row.get("_id") != business.get("_id")
            ]
            duplicate_conflict_summaries = build_conflict_summary_rows(duplicate_conflict_rows)
            should_skip_google_place_id = bool(duplicate_conflict_rows)

            try:
                fresh_photo_names, display_name = fetch_fresh_photo_names(source_place_id, api_key)
            except requests.RequestException as exc:
                failures += 1
                print(
                    f"error name={business_name!r} id={business_id} "
                    f"place_id={source_place_id} type={exc.__class__.__name__}",
                    file=sys.stderr,
                )
                if args.sleep_seconds:
                    time.sleep(args.sleep_seconds)
                continue
            except RuntimeError as exc:
                failures += 1
                print(
                    f"error name={business_name!r} id={business_id} "
                    f"place_id={source_place_id} {exc}",
                    file=sys.stderr,
                )
                if args.sleep_seconds:
                    time.sleep(args.sleep_seconds)
                continue

            found_fresh_photos = bool(fresh_photo_names)
            image_url_will_be_cleared = bool(business.get("image_url"))
            google_photo_names_will_be_updated = found_fresh_photos and (
                fresh_photo_names != (business.get("google_photo_names") or [])
            )
            update_fields = {
                "google_photo_names": fresh_photo_names,
                REFRESHED_AT_FIELD: now_iso(),
                "image_url": "",
            }
            if should_skip_google_place_id:
                update_fields["google_photo_source_place_id"] = source_place_id
            else:
                update_fields["google_place_id"] = source_place_id

            if not found_fresh_photos:
                skipped += 1
                print(
                    f"skip name={business_name!r} id={business_id} "
                    f"fresh_photos_found=no reason=no_fresh_photos "
                    f"duplicate_google_place_id_conflicts={duplicate_conflict_summaries} "
                    f"google_place_id_will_be_skipped={'yes' if should_skip_google_place_id else 'no'} "
                    f"google_photo_names_will_be_updated=no "
                    f"image_url_will_be_cleared=no"
                )
                if args.sleep_seconds:
                    time.sleep(args.sleep_seconds)
                continue

            print(
                f"plan name={business_name!r} id={business_id} "
                f"place_id={source_place_id} fresh_photos_found=yes "
                f"fresh_photo_count={len(fresh_photo_names)} "
                f"display_name={display_name!r} "
                f"duplicate_google_place_id_conflicts={duplicate_conflict_summaries} "
                f"google_place_id_will_be_skipped={'yes' if should_skip_google_place_id else 'no'} "
                f"google_photo_names_will_be_updated={'yes' if google_photo_names_will_be_updated else 'no'} "
                f"image_url_will_be_cleared={'yes' if image_url_will_be_cleared else 'no'} "
                f"would_update_fields={list(update_fields.keys())}"
            )

            if args.apply:
                try:
                    update_result = collection.update_one(
                        {"_id": business["_id"]},
                        {"$set": update_fields},
                    )
                except DuplicateKeyError:
                    if should_skip_google_place_id or existing_place_id == source_place_id:
                        raise
                    should_skip_google_place_id = True
                    update_fields.pop("google_place_id", None)
                    update_fields["google_photo_source_place_id"] = source_place_id
                    print(
                        f"conflict name={business_name!r} id={business_id} "
                        "google_place_id_write_conflict_detected=yes "
                        "retrying_without_google_place_id=yes"
                    )
                    update_result = collection.update_one(
                        {"_id": business["_id"]},
                        {"$set": update_fields},
                    )
                if update_result.modified_count:
                    updated += 1
                    print(f"updated name={business_name!r} id={business_id}")
                else:
                    skipped += 1
                    print(f"skipped name={business_name!r} id={business_id} reason=no_change")
            else:
                updated += 1

            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

        print(f"records_ready_to_update={updated}" if not args.apply else f"records_updated={updated}")
        print(f"records_skipped={skipped}")
        print(f"errors={failures}")
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
