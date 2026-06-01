"""Dependency-free tests for Ticketmaster event sync helpers."""
import json
import os
import socket
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC_DIR = BACKEND_DIR.parent / "frontend" / "src"
sys.path.insert(0, str(BACKEND_DIR))

from ticketmaster_events import (  # noqa: E402
    TicketmasterClient,
    apply_event_sync,
    attach_event_to_step,
    canonical_venue_name,
    deduplicate_event_documents,
    dry_run_sync,
    event_is_on_local_date,
    events_by_business_id,
    match_business_for_venue,
    normalize_venue_name,
    require_apply_approval,
    ticketmaster_event_document,
    utc_city_day_window,
)


def event(**overrides):
    row = {
        "id": "event-123",
        "name": "Nashville Predators vs. Example",
        "url": "https://www.ticketmaster.com/event-123",
        "source": {"name": "ticketmaster"},
        "dates": {
            "start": {
                "localDate": "2026-06-01",
                "localTime": "19:00:00",
                "dateTime": "2026-06-02T00:00:00Z",
            },
            "status": {"code": "onsale"},
        },
        "images": [
            {"url": "https://example.com/small.jpg", "width": 320, "ratio": "4_3"},
            {"url": "https://example.com/hero.jpg", "width": 1024, "ratio": "16_9"},
        ],
        "_embedded": {
            "venues": [{"name": "Bridgestone Arena"}],
            "attractions": [{"name": "Nashville Predators"}, {"name": "Example"}],
        },
    }
    row.update(overrides)
    return row


class TestMatching(unittest.TestCase):
    def test_normalizes_venue_names(self):
        self.assertEqual(normalize_venue_name("The Basement East"), "basement east")
        self.assertEqual(normalize_venue_name("Exit/In"), "exit in")

    def test_matches_existing_business_by_normalized_venue_name(self):
        business = {"id": "business-123", "name": "The Basement East"}
        self.assertEqual(match_business_for_venue("Basement East", [business]), business)

    def test_canonicalizes_3rd_and_lindsley_alias(self):
        self.assertEqual(canonical_venue_name("3rd and Lindsley"), "3rd & Lindsley")

    def test_document_maps_ticketmaster_fields_and_match(self):
        document = ticketmaster_event_document(
            event(source={"name": "ticketweb"}),
            "nashville",
            [{"id": "bridgestone", "name": "Bridgestone Arena"}],
            synced_at="2026-06-01T12:00:00+00:00",
        )
        self.assertEqual(document["venue_business_id"], "bridgestone")
        self.assertEqual(document["source"], "ticketmaster")
        self.assertEqual(document["performers"], ["Nashville Predators", "Example"])
        self.assertEqual(document["local_date"], "2026-06-01")
        self.assertEqual(document["local_time"], "19:00:00")
        self.assertEqual(document["image_url"], "https://example.com/hero.jpg")
        self.assertEqual(document["updated_at"], "2026-06-01T12:00:00+00:00")

    def test_document_stores_canonical_venue_alias(self):
        document = ticketmaster_event_document(
            event(_embedded={"venues": [{"name": "3rd and Lindsley"}]}),
            "nashville",
            [],
        )
        self.assertEqual(document["venue_name"], "3rd & Lindsley")


class TestDeduplication(unittest.TestCase):
    def test_deduplicates_by_source_and_external_event_id(self):
        document = ticketmaster_event_document(event(), "nashville", [])
        self.assertEqual(deduplicate_event_documents([document, {**document}]), [document])

    def test_deduplicates_feed_variants_with_same_ticket_url(self):
        first = ticketmaster_event_document(event(id="first"), "nashville", [])
        second = ticketmaster_event_document(event(id="second"), "nashville", [])
        self.assertEqual(deduplicate_event_documents([first, second]), [first])


class TestDates(unittest.TestCase):
    def test_filters_by_ticketmaster_local_date(self):
        self.assertTrue(event_is_on_local_date(event(), "2026-06-01"))
        self.assertFalse(event_is_on_local_date(event(), "2026-06-02"))

    def test_first_event_for_business_is_earliest(self):
        early = {"venue_business_id": "venue", "starts_at": "2026-06-02T00:00:00Z", "title": "Early"}
        late = {"venue_business_id": "venue", "starts_at": "2026-06-02T03:00:00Z", "title": "Late"}
        self.assertEqual(events_by_business_id([late, early])["venue"]["title"], "Early")

    def test_converts_nashville_city_day_to_utc_window(self):
        self.assertEqual(
            utc_city_day_window("nashville", "2026-06-01"),
            ("2026-06-01T05:00:00Z", "2026-06-02T05:00:00Z"),
        )
        self.assertEqual(
            utc_city_day_window("nashville", "2026-12-01"),
            ("2026-12-01T06:00:00Z", "2026-12-02T06:00:00Z"),
        )


class TestItineraryAttachment(unittest.TestCase):
    def test_attaches_event_to_entertainment_step(self):
        step = {"slot": "entertainment", "business": {"id": "venue"}}
        attached = attach_event_to_step(step, {"venue": {"title": "Show"}})
        self.assertEqual(attached["event"]["title"], "Show")

    def test_keeps_existing_recommendation_when_no_event_matches(self):
        step = {"slot": "late-night", "business": {"id": "venue"}}
        self.assertEqual(attach_event_to_step(step, {}), step)

    def test_does_not_attach_event_to_dinner_step(self):
        step = {"slot": "dinner", "business": {"id": "venue"}}
        self.assertEqual(attach_event_to_step(step, {"venue": {"title": "Show"}}), step)


class TestClient(unittest.TestCase):
    def test_requires_backend_api_key(self):
        previous = os.environ.pop("TICKETMASTER_API_KEY", None)
        try:
            with self.assertRaisesRegex(RuntimeError, "TICKETMASTER_API_KEY must be set"):
                TicketmasterClient()
        finally:
            if previous is not None:
                os.environ["TICKETMASTER_API_KEY"] = previous

    def test_sends_api_key_only_in_backend_ticketmaster_request(self):
        opener = FakeOpener({"_embedded": {"events": [event()]}})
        client = TicketmasterClient(api_key="backend-secret", opener=opener)
        rows = client.events_for_date("nashville", "2026-06-01")
        query = parse_qs(urlparse(opener.url).query)
        self.assertEqual(len(rows), 1)
        self.assertEqual(query["apikey"], ["backend-secret"])
        self.assertEqual(query["city"], ["Nashville"])
        self.assertEqual(query["startDateTime"], ["2026-06-01T05:00:00Z"])
        self.assertEqual(query["endDateTime"], ["2026-06-02T05:00:00Z"])
        self.assertEqual(query["size"], ["200"])
        self.assertEqual(query["sort"], ["date,asc"])
        self.assertNotIn("localStartDateTime", query)
        self.assertEqual(opener.timeout, 10)

    def test_retries_504_then_returns_events(self):
        opener = SequenceOpener([
            HTTPError("https://example.com", 504, "Gateway Time-out", None, None),
            {"_embedded": {"events": [event()]}},
        ])
        sleeps = []
        client = TicketmasterClient(
            api_key="backend-secret",
            opener=opener,
            retry_delay_seconds=0.01,
            sleeper=sleeps.append,
        )
        self.assertEqual(len(client.events_for_date("nashville", "2026-06-01")), 1)
        self.assertEqual(opener.calls, 2)
        self.assertEqual(sleeps, [0.01])

    def test_retries_timeout_then_returns_events(self):
        opener = SequenceOpener([
            socket.timeout("read timed out"),
            {"_embedded": {"events": [event()]}},
        ])
        client = TicketmasterClient(api_key="backend-secret", opener=opener, sleeper=lambda _: None)
        self.assertEqual(len(client.events_for_date("nashville", "2026-06-01")), 1)
        self.assertEqual(opener.calls, 2)

    def test_stops_after_bounded_retries(self):
        opener = SequenceOpener([socket.timeout("read timed out")] * 3)
        client = TicketmasterClient(api_key="backend-secret", opener=opener, sleeper=lambda _: None)
        with self.assertRaises(socket.timeout):
            client.events_for_date("nashville", "2026-06-01")
        self.assertEqual(opener.calls, 3)

    def test_frontend_source_does_not_reference_ticketmaster_api_key(self):
        frontend_source = "\n".join(
            path.read_text()
            for path in FRONTEND_SRC_DIR.rglob("*")
            if path.suffix in {".js", ".jsx"}
        )
        self.assertNotIn("TICKETMASTER_API_KEY", frontend_source)

    def test_dry_run_reports_matches_without_writing_or_leaking_key(self):
        client = FakeClient([event()])
        report = dry_run_sync(
            client,
            [{"id": "bridgestone", "name": "Bridgestone Arena"}],
            local_date="2026-06-01",
        )
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["matched"], 1)
        self.assertEqual(report["unmatched"], 0)
        self.assertNotIn("apikey", json.dumps(report).lower())
        self.assertNotIn("backend-secret", json.dumps(report))


class TestApply(unittest.TestCase):
    def test_requires_exact_typed_approval(self):
        require_apply_approval(input_fn=lambda _: "APPROVE")
        with self.assertRaisesRegex(RuntimeError, "Apply cancelled"):
            require_apply_approval(input_fn=lambda _: "approve")

    def test_upserts_by_source_and_external_id_then_removes_expired_events(self):
        document = ticketmaster_event_document(
            event(),
            "nashville",
            [],
            synced_at="2026-06-01T12:00:00+00:00",
        )
        collection = FakeCollection()
        result = apply_event_sync(
            collection,
            {"events": [document]},
            "nashville",
            now=datetime(2026, 6, 1, 12, tzinfo=timezone.utc),
        )
        query, update, upsert = collection.updates[0]
        self.assertEqual(query, {"source": "ticketmaster", "external_event_id": "event-123"})
        self.assertTrue(upsert)
        self.assertEqual(update["$set"]["title"], "Nashville Predators vs. Example")
        self.assertEqual(update["$set"]["venue_name"], "Bridgestone Arena")
        self.assertEqual(update["$set"]["local_time"], "19:00:00")
        self.assertEqual(update["$set"]["image_url"], "https://example.com/hero.jpg")
        self.assertEqual(update["$set"]["ticket_url"], "https://www.ticketmaster.com/event-123")
        self.assertEqual(update["$set"]["city_slug"], "nashville")
        self.assertEqual(collection.deletes, [{
            "source": "ticketmaster",
            "city_slug": "nashville",
            "local_date": {"$lt": "2026-06-01"},
        }])
        self.assertEqual(result["upserted"], 1)
        self.assertEqual(result["expired_deleted"], 2)


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def events_for_date(self, city_slug, local_date):
        self.city_slug = city_slug
        self.local_date = local_date
        return self.rows


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, payload):
        self.payload = payload
        self.url = None

    def __call__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        return FakeResponse(self.payload)


class SequenceOpener:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def __call__(self, url, timeout):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


class FakeWriteResult:
    upserted_id = "new-event"
    modified_count = 0


class FakeDeleteResult:
    deleted_count = 2


class FakeCollection:
    def __init__(self):
        self.updates = []
        self.deletes = []

    def update_one(self, query, update, upsert):
        self.updates.append((query, update, upsert))
        return FakeWriteResult()

    def delete_many(self, query):
        self.deletes.append(query)
        return FakeDeleteResult()


if __name__ == "__main__":
    unittest.main()
