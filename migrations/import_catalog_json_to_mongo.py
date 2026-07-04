#!/usr/bin/env python3
"""Import catalog JSON exports into a destination Mongo database.

Default mode is dry-run. Use --apply to perform inserts.

Environment variables:
- DEST_MONGO_URL
- DEST_DB
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

from bson import json_util
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

SUPPORTED_COLLECTIONS = ("categories", "cities", "businesses", "city_events")
DEFAULT_COLLECTIONS = ("categories", "cities", "businesses")
DEFAULT_EXPORT_DIR = Path(__file__).resolve().parent / "emergent_export"
REQUIRED_ENV_VARS = ("DEST_MONGO_URL", "DEST_DB")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export-dir",
        default=str(DEFAULT_EXPORT_DIR),
        help="Directory containing exported collection JSON files",
    )
    parser.add_argument(
        "--collections",
        default=",".join(DEFAULT_COLLECTIONS),
        help="Comma-separated collections to import",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to the destination database",
    )
    parser.add_argument(
        "--allow-non-empty",
        action="store_true",
        help="Permit inserts into non-empty destination collections",
    )
    return parser.parse_args()


def parse_collections(value: str) -> list[str]:
    collections: list[str] = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if item not in SUPPORTED_COLLECTIONS:
            valid = ", ".join(SUPPORTED_COLLECTIONS)
            raise RuntimeError(f"Unsupported collection '{item}'. Valid values: {valid}")
        if item not in collections:
            collections.append(item)
    if not collections:
        raise RuntimeError("At least one collection must be requested")
    return collections


def load_documents(export_dir: Path, collection_name: str) -> list[dict]:
    json_path = export_dir / f"{collection_name}.json"
    if not json_path.exists():
        raise RuntimeError(f"Missing export file: {json_path}")

    try:
        payload = json_util.loads(json_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON in {json_path}") from exc

    if not isinstance(payload, list):
        raise RuntimeError(f"{json_path} must contain a JSON list")

    documents: list[dict] = []
    for index, document in enumerate(payload):
        if not isinstance(document, dict):
            raise RuntimeError(f"{json_path} record {index} is not an object")
        documents.append(document)
    return documents


def count_documents(db, collection_name: str) -> int:
    return db[collection_name].count_documents({})


def dry_run(dest_db, export_dir: Path, collections: Iterable[str]) -> int:
    print("mode=dry-run")
    for collection_name in collections:
        documents = load_documents(export_dir, collection_name)
        dest_count = count_documents(dest_db, collection_name)
        print(
            f"collection={collection_name} "
            f"file_count={len(documents)} "
            f"dest_count={dest_count}"
        )
    print("No writes were made.")
    return 0


def insert_collection(dest_db, export_dir: Path, collection_name: str) -> dict[str, int]:
    collection = dest_db[collection_name]
    documents = load_documents(export_dir, collection_name)
    inserted = 0
    skipped = 0
    errors = 0

    for document in documents:
        try:
            collection.insert_one(document)
            inserted += 1
        except DuplicateKeyError:
            skipped += 1
            doc_id = document.get("_id", "<missing>")
            print(
                f"skip collection={collection_name} _id={doc_id!r} reason=duplicate_key",
                file=sys.stderr,
            )
        except PyMongoError as exc:
            errors += 1
            doc_id = document.get("_id", "<missing>")
            print(
                f"error collection={collection_name} _id={doc_id!r} type={exc.__class__.__name__}",
                file=sys.stderr,
            )

    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
    }


def apply_import(dest_db, export_dir: Path, collections: Iterable[str], allow_non_empty: bool) -> int:
    print("mode=apply")

    for collection_name in collections:
        documents = load_documents(export_dir, collection_name)
        dest_count = count_documents(dest_db, collection_name)
        print(
            f"collection={collection_name} "
            f"file_count={len(documents)} "
            f"dest_count={dest_count}"
        )
        if dest_count > 0 and not allow_non_empty:
            raise RuntimeError(
                f"Destination collection '{collection_name}' is non-empty; "
                "re-run with --allow-non-empty to permit inserts without deletes"
            )

    totals = {"inserted": 0, "skipped": 0, "errors": 0}

    for collection_name in collections:
        result = insert_collection(dest_db, export_dir, collection_name)
        totals["inserted"] += result["inserted"]
        totals["skipped"] += result["skipped"]
        totals["errors"] += result["errors"]
        print(
            f"collection={collection_name} "
            f"inserted={result['inserted']} "
            f"skipped={result['skipped']} "
            f"errors={result['errors']}"
        )

    print(
        f"summary inserted={totals['inserted']} "
        f"skipped={totals['skipped']} "
        f"errors={totals['errors']}"
    )
    return 0 if totals["errors"] == 0 else 1


def main() -> int:
    args = parse_args()
    collections = parse_collections(args.collections)
    export_dir = Path(args.export_dir).expanduser().resolve()

    for env_name in REQUIRED_ENV_VARS:
        require_env(env_name)
    dest_url = require_env("DEST_MONGO_URL")
    dest_db_name = require_env("DEST_DB")

    dest_client = MongoClient(dest_url)
    try:
        dest_db = dest_client[dest_db_name]
        if args.apply:
            return apply_import(dest_db, export_dir, collections, args.allow_non_empty)
        return dry_run(dest_db, export_dir, collections)
    finally:
        dest_client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
