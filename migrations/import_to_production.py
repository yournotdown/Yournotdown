#!/usr/bin/env python3
"""Import Nashville businesses into PRODUCTION Mongo.

USAGE (run inside the production container/pod, NOT here):

    # Step 1 — dry run, verify what would change
    python3 import_to_production.py --dry-run

    # Step 2 — only after confirming the dry-run looks right
    python3 import_to_production.py --apply

The script reads MONGO_URL + DB_NAME from the production env (NEVER pass them
on the CLI). It upserts the 91 Google-imported businesses by `google_place_id`
(the natural dedupe key for that batch). It does NOT touch the 30 seed
businesses (production already has its own seed via backend startup).

Safety guarantees:
  • Default mode is --dry-run (prints what would change, writes nothing)
  • Upserts only — never deletes
  • Dedupes on `google_place_id`, so re-running is idempotent
  • Validates each doc has required fields before insert
  • Reports counts after the run
"""
import argparse
import json
import os
import sys
from pathlib import Path

from pymongo import MongoClient, ReplaceOne

JSON_PATH = Path(__file__).parent / "nashville_imports_only.json"
REQUIRED_FIELDS = ("id", "name", "city_slug", "google_place_id", "slots", "imported_status")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Actually write to Mongo. Default is dry-run (no writes).")
    ap.add_argument("--dry-run", action="store_true", help="(default) — preview only")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        sys.exit("FATAL: MONGO_URL and DB_NAME must be set in the production env.")

    if not JSON_PATH.exists():
        sys.exit(f"FATAL: {JSON_PATH} not found. Copy it into the prod container first.")

    with open(JSON_PATH) as f:
        docs = json.load(f)
    print(f"loaded {len(docs)} docs from {JSON_PATH.name}")

    # Validate
    bad = []
    for d in docs:
        for k in REQUIRED_FIELDS:
            if not d.get(k):
                bad.append((d.get("name", "?"), k))
                break
    if bad:
        sys.exit(f"FATAL: {len(bad)} docs missing required fields. First: {bad[:3]}")
    print(f"validated: all {len(docs)} docs have required fields")

    db = MongoClient(mongo_url)[db_name]

    # Pre-state
    before_total = db.businesses.count_documents({})
    before_with_gpid = db.businesses.count_documents({"google_place_id": {"$exists": True}})
    print(f"\nBEFORE: total={before_total}, with_google_place_id={before_with_gpid}")

    # Plan upserts
    ops, will_insert, will_update = [], 0, 0
    incoming_gpids = {d["google_place_id"] for d in docs}
    existing_gpids = {d["google_place_id"] for d in db.businesses.find(
        {"google_place_id": {"$in": list(incoming_gpids)}},
        {"_id": 0, "google_place_id": 1},
    )}
    for d in docs:
        if d["google_place_id"] in existing_gpids:
            will_update += 1
        else:
            will_insert += 1
        ops.append(ReplaceOne({"google_place_id": d["google_place_id"]}, d, upsert=True))

    print(f"\nPLAN: insert {will_insert}, update {will_update} (total {len(ops)} upserts)")

    if not apply:
        print("\n--- DRY RUN — no writes made. Re-run with --apply to commit. ---")
        return

    result = db.businesses.bulk_write(ops, ordered=False)
    print(f"\nRESULT: upserted={result.upserted_count}, modified={result.modified_count}, matched={result.matched_count}")

    after_total = db.businesses.count_documents({})
    after_with_gpid = db.businesses.count_documents({"google_place_id": {"$exists": True}})
    print(f"AFTER:  total={after_total}, with_google_place_id={after_with_gpid}")
    print(f"DELTA:  total +{after_total - before_total}, imports +{after_with_gpid - before_with_gpid}")
    print("\n✓ Done. Nothing deleted. Re-run is idempotent.")


if __name__ == "__main__":
    main()
