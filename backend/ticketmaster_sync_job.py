#!/usr/bin/env python3
"""Railway-safe Ticketmaster sync job.

Default mode applies the sync because Railway cron execution is intentional.
Use --dry-run for manual verification without writing to Mongo.

Environment variables:
- MONGO_URL
- DB_NAME
- TICKETMASTER_API_KEY
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        return None

from ticketmaster_events import (
    CITY_CONFIG,
    TicketmasterClient,
    TicketmasterRateLimitError,
    apply_event_sync,
    date_range_sync_report,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

REQUIRED_ENV_VARS = ("MONGO_URL", "DB_NAME", "TICKETMASTER_API_KEY")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="nashville", choices=sorted(CITY_CONFIG))
    parser.add_argument("--days", type=int, default=2, help="Number of local dates to sync (default: 2)")
    parser.add_argument("--start-date", help="Start local date in YYYY-MM-DD format")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write to Mongo")
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def open_mongo_client(mongo_url: str):
    from pymongo import MongoClient

    return MongoClient(mongo_url)


def load_approved_businesses(database, city_slug: str) -> list[dict]:
    return list(database.businesses.find(
        {"city_slug": city_slug, "imported_status": "approved"},
        {"_id": 0, "id": 1, "name": 1},
    ))


def redact_secret_text(text: str, secrets: list[str]) -> str:
    sanitized = text or ""
    for secret in secrets:
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    sanitized = re.sub(r"([?&]apikey=)[^\s&]+", r"\1[REDACTED]", sanitized, flags=re.IGNORECASE)
    return " ".join(sanitized.split())[:300]


def print_summary(report: dict, apply_summary: dict | None = None, mode: str = "apply",
                  errors: list[str] | None = None, status: str | None = None,
                  extra_fields: dict[str, str | int] | None = None) -> None:
    print(f"status={status or ('ok' if not errors else 'error')}")
    print(f"mode={mode}")
    print(f"dates={','.join(report.get('dates') or [])}")
    print(f"fetched={report.get('fetched', 0)}")
    print(f"after_dedupe={report.get('after_dedupe', 0)}")
    print(f"matched={report.get('matched', 0)}")
    print(f"unmatched={report.get('unmatched', 0)}")
    print(f"upserted={(apply_summary or {}).get('upserted', 0)}")
    print(f"deleted_expired={(apply_summary or {}).get('expired_deleted', 0)}")
    for key, value in (extra_fields or {}).items():
        if value not in (None, ""):
            print(f"{key}={value}")
    if errors:
        print(f"errors={len(errors)}")
        for error in errors:
            print(f"error={error}", file=sys.stderr)
    else:
        print("errors=0")


def main() -> int:
    args = parse_args()
    if args.start_date:
        date.fromisoformat(args.start_date)

    secrets = [os.environ.get(name, "").strip() for name in REQUIRED_ENV_VARS]

    try:
        mongo_url = require_env("MONGO_URL")
        db_name = require_env("DB_NAME")
        api_key = require_env("TICKETMASTER_API_KEY")
        mongo_client = open_mongo_client(mongo_url)
    except Exception as exc:
        error = redact_secret_text(f"{type(exc).__name__}: {exc}", secrets)
        print("status=error")
        print("errors=1")
        print(f"error={error}", file=sys.stderr)
        return 1

    try:
        database = mongo_client[db_name]
        businesses = load_approved_businesses(database, args.city)
        report = date_range_sync_report(
            TicketmasterClient(api_key=api_key),
            businesses,
            city_slug=args.city,
            days=args.days,
            start_date=args.start_date,
        )
        if args.dry_run:
            print_summary(report, mode="dry-run")
            return 0

        apply_summary = apply_event_sync(database.city_events, report, args.city)
        print_summary(report, apply_summary=apply_summary, mode="apply")
        return 0
    except TicketmasterRateLimitError as exc:
        fallback_report = {"dates": []}
        print_summary(
            fallback_report,
            mode="dry-run" if args.dry_run else "apply",
            status="rate_limited",
            extra_fields={"retry_after": exc.retry_after},
        )
        return 0
    except Exception as exc:
        error = redact_secret_text(f"{type(exc).__name__}: {exc}", secrets)
        fallback_report = {"dates": []}
        print_summary(fallback_report, mode="dry-run" if args.dry_run else "apply", errors=[error])
        return 1
    finally:
        mongo_client.close()


if __name__ == "__main__":
    raise SystemExit(main())
