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
TICKETMASTER_EVENTS_SOURCE = (BACKEND_DIR / "ticketmaster_events.py").read_text()
sys.path.insert(0, str(BACKEND_DIR))

from ticketmaster_events import (  # noqa: E402
    TicketmasterClient,
    api_sync_response,
    apply_event_sync,
    attach_events_to_businesses,
    attach_event_to_step,
    canonical_venue_name,
    date_range_sync_report,
    deduplicate_event_documents,
    dry_run_sync,
    eligible_public_businesses,
    eligible_city_events,
    eligible_ticketmaster_music_events,
    event_is_ticketmaster_music,
    event_upsert,
    event_has_excluded_status,
    event_is_eligible,
    event_is_on_local_date,
    events_by_business_id,
    expiration_cleanup_query,
    itinerary_event_pick,
    match_business_for_venue,
    normalize_venue_name,
    require_apply_approval,
    supported_city_config,
    ticketmaster_event_document,
    utc_city_day_window,
    validate_apply_confirmation,
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
    def test_public_business_filter_has_no_name_based_suppression_list(self):
        self.assertNotIn("PUBLIC_EVENT_ONLY_BUSINESS_NAMES", TICKETMASTER_EVENTS_SOURCE)
        self.assertNotIn("business_requires_eligible_event", TICKETMASTER_EVENTS_SOURCE)

    def test_normalizes_venue_names(self):
        self.assertEqual(normalize_venue_name("The Basement East"), "basement east")
        self.assertEqual(normalize_venue_name("Exit/In"), "exit in")

    def test_matches_existing_business_by_normalized_venue_name(self):
        business = {"id": "business-123", "name": "The Basement East"}
        self.assertEqual(match_business_for_venue("Basement East", [business]), business)

    def test_canonicalizes_3rd_and_lindsley_alias(self):
        self.assertEqual(canonical_venue_name("3rd and Lindsley"), "3rd & Lindsley")

    def test_canonicalizes_ole_red_nashville_alias(self):
        self.assertEqual(canonical_venue_name("Ole Red - Nashville"), "Ole Red")

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
        self.assertEqual(document["classification_segment"], "")
        self.assertEqual(document["updated_at"], "2026-06-01T12:00:00+00:00")

    def test_document_stores_ticketmaster_classification_fields(self):
        document = ticketmaster_event_document(
            event(classifications=[{
                "segment": {"name": "Music"},
                "genre": {"name": "Rock"},
                "subGenre": {"name": "Alternative Rock"},
            }]),
            "nashville",
            [],
        )
        self.assertEqual(document["classification_segment"], "Music")
        self.assertEqual(document["classification_genre"], "Rock")
        self.assertEqual(document["classification_subgenre"], "Alternative Rock")

    def test_document_stores_canonical_venue_alias(self):
        document = ticketmaster_event_document(
            event(_embedded={"venues": [{"name": "3rd and Lindsley"}]}),
            "nashville",
            [],
        )
        self.assertEqual(document["venue_name"], "3rd & Lindsley")

    def test_supported_city_config_rejects_unknown_city(self):
        self.assertEqual(supported_city_config("nashville")["ticketmaster_city"], "Nashville")
        with self.assertRaisesRegex(ValueError, "Unsupported city slug: miami"):
            supported_city_config("miami")


class TestDeduplication(unittest.TestCase):
    def test_deduplicates_by_source_and_external_event_id(self):
        document = ticketmaster_event_document(event(), "nashville", [])
        self.assertEqual(deduplicate_event_documents([document, {**document}]), [document])

    def test_deduplicates_feed_variants_with_same_ticket_url(self):
        first = ticketmaster_event_document(event(id="first"), "nashville", [])
        second = ticketmaster_event_document(event(id="second"), "nashville", [])
        self.assertEqual(deduplicate_event_documents([first, second]), [first])


class TestDateRangeReport(unittest.TestCase):
    def test_aggregates_dates_and_deduplicates_without_writes(self):
        client = FakeDateRangeClient({
            "2026-06-01": [event(id="first")],
            "2026-06-02": [
                event(
                    id="second",
                    dates={"start": {"localDate": "2026-06-02", "localTime": "19:00:00"}},
                ),
                event(
                    id="third",
                    dates={"start": {"localDate": "2026-06-02", "localTime": "20:00:00"}},
                ),
            ],
        })
        report = date_range_sync_report(client, [], "nashville", days=2, start_date="2026-06-01")
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["dates"], ["2026-06-01", "2026-06-02"])
        self.assertEqual(report["fetched"], 3)
        self.assertEqual(report["after_dedupe"], 1)
        self.assertEqual(report["would_upsert"], 1)
        self.assertEqual(report["duplicates_removed"], 2)

    def test_rejects_out_of_range_days(self):
        with self.assertRaisesRegex(ValueError, "days must be between 1 and 7"):
            date_range_sync_report(FakeDateRangeClient({}), [], days=8)


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

    def test_excludes_cancelled_canceled_and_offsale_statuses(self):
        for status in ("cancelled", "canceled", "offsale", " offsale "):
            with self.subTest(status=status):
                self.assertTrue(event_has_excluded_status({"status": status}))
                self.assertFalse(
                    event_is_eligible(
                        {
                            "local_date": "2026-06-01",
                            "local_time": "19:00:00",
                            "status": status,
                        },
                        "nashville",
                        now=datetime(2026, 6, 1, 12, tzinfo=timezone.utc),
                    )
                )

    def test_keeps_future_same_day_event_before_start(self):
        self.assertTrue(
            event_is_eligible(
                {
                    "local_date": "2026-06-01",
                    "local_time": "19:00:00",
                    "status": "onsale",
                },
                "nashville",
                now=datetime(2026, 6, 1, 22, 30, tzinfo=timezone.utc),
            )
        )

    def test_keeps_same_day_event_within_grace_window(self):
        self.assertTrue(
            event_is_eligible(
                {
                    "local_date": "2026-06-01",
                    "local_time": "19:00:00",
                    "status": "onsale",
                },
                "nashville",
                now=datetime(2026, 6, 2, 0, 30, tzinfo=timezone.utc),
                grace_minutes=60,
            )
        )

    def test_filters_same_day_event_after_grace_window(self):
        self.assertFalse(
            event_is_eligible(
                {
                    "local_date": "2026-06-01",
                    "local_time": "19:00:00",
                    "status": "onsale",
                },
                "nashville",
                now=datetime(2026, 6, 2, 1, 1, tzinfo=timezone.utc),
                grace_minutes=60,
            )
        )

    def test_keeps_same_day_event_with_missing_local_time(self):
        self.assertTrue(
            event_is_eligible(
                {
                    "local_date": "2026-06-01",
                    "local_time": None,
                    "status": "onsale",
                },
                "nashville",
                now=datetime(2026, 6, 2, 3, tzinfo=timezone.utc),
            )
        )

    def test_filters_city_events_with_shared_eligibility_logic(self):
        rows = [
            {"title": "Cancelled", "local_date": "2026-06-01", "local_time": "19:00:00", "status": "cancelled"},
            {"title": "Offsale", "local_date": "2026-06-01", "local_time": None, "status": "offsale"},
            {"title": "Stale", "local_date": "2026-06-01", "local_time": "18:00:00", "status": "onsale"},
            {"title": "Future", "local_date": "2026-06-01", "local_time": "21:00:00", "status": "onsale"},
            {"title": "No Time", "local_date": "2026-06-01", "local_time": None, "status": "onsale"},
        ]
        filtered = eligible_city_events(
            rows,
            "nashville",
            now=datetime(2026, 6, 2, 1, 1, tzinfo=timezone.utc),
            grace_minutes=60,
        )
        self.assertEqual([row["title"] for row in filtered], ["Future", "No Time"])

    def test_ticketmaster_music_events_require_music_segment_when_present(self):
        businesses = [{"id": "venue", "name": "Exit/In", "slots": ["entertainment"], "category_slug": "live-music"}]
        rows = [
            {"title": "Ballgame", "source": "ticketmaster", "classification_segment": "Sports", "venue_business_id": "venue"},
            {"title": "Concert", "source": "ticketmaster", "classification_segment": "Music", "venue_business_id": "venue"},
        ]
        events = eligible_ticketmaster_music_events(rows, businesses)
        self.assertEqual([row["title"] for row in events], ["Concert"])

    def test_ticketmaster_music_events_fallback_to_live_music_business_when_classification_missing(self):
        businesses = [
            {"id": "music-venue", "name": "Exit/In", "slots": ["entertainment"], "category_slug": "live-music"},
            {"id": "sports-venue", "name": "First Horizon Park", "slots": ["late-night"], "category_slug": "night-out"},
        ]
        rows = [
            {"title": "Indie Show", "source": "ticketmaster", "venue_business_id": "music-venue"},
            {"title": "Baseball", "source": "ticketmaster", "venue_business_id": "sports-venue"},
        ]
        events = eligible_ticketmaster_music_events(rows, businesses)
        self.assertEqual([row["title"] for row in events], ["Indie Show"])

    def test_event_is_ticketmaster_music_rejects_non_ticketmaster_rows(self):
        business = {"id": "venue", "slots": ["entertainment"], "category_slug": "live-music"}
        self.assertFalse(event_is_ticketmaster_music({"source": "partner"}, business))

    def test_itinerary_event_pick_respects_excluded_event_ids(self):
        businesses = [
            {"id": "exit", "name": "Exit/In"},
            {"id": "basement", "name": "The Basement East"},
        ]
        events = [
            {"title": "First Show", "venue_business_id": "exit", "external_event_id": "event-1"},
            {"title": "Second Show", "venue_business_id": "basement", "external_event_id": "event-2"},
        ]
        business, event_row = itinerary_event_pick(businesses, events, {"none"}, {"event-1"})
        self.assertEqual(business["id"], "basement")
        self.assertEqual(event_row["external_event_id"], "event-2")

    def test_itinerary_event_pick_relaxes_exclusions_when_all_events_are_exhausted(self):
        businesses = [{"id": "exit", "name": "Exit/In"}]
        events = [{"title": "Only Show", "venue_business_id": "exit", "external_event_id": "event-1"}]
        business, event_row = itinerary_event_pick(businesses, events, {"exit"}, {"event-1"})
        self.assertEqual(business["id"], "exit")
        self.assertEqual(event_row["external_event_id"], "event-1")

    def test_itinerary_event_pick_rotates_to_different_event_when_possible(self):
        businesses = [
            {"id": "exit", "name": "Exit/In"},
            {"id": "basement", "name": "The Basement East"},
        ]
        events = [
            {"title": "First Show", "venue_business_id": "exit", "external_event_id": "event-1"},
            {"title": "Second Show", "venue_business_id": "basement", "external_event_id": "event-2"},
        ]
        business, event_row = itinerary_event_pick(businesses, events, {"exit"}, {"event-1"})
        self.assertEqual(business["id"], "basement")
        self.assertEqual(event_row["external_event_id"], "event-2")

    def test_itinerary_event_pick_returns_none_when_no_candidate_available(self):
        business, event_row = itinerary_event_pick([], [], {"exit"}, {"event-1"})
        self.assertIsNone(business)
        self.assertIsNone(event_row)


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

    def test_attaches_event_to_business_records(self):
        businesses = [{"id": "venue", "name": "Exit/In"}]
        events = [{"id": "event-1", "venue_business_id": "venue", "title": "Late Show"}]
        attached = attach_events_to_businesses(businesses, events)
        self.assertEqual(attached[0]["event"]["title"], "Late Show")

    def test_public_businesses_keep_normal_live_music_venue_without_event(self):
        businesses = [
            {"id": "basement", "name": "The Basement East"},
        ]
        visible = eligible_public_businesses(businesses, [])
        self.assertEqual([business["name"] for business in visible], ["The Basement East"])
        self.assertNotIn("event", visible[0])

    def test_public_businesses_keep_musicians_corner_like_row_without_name_matching(self):
        businesses = [{"id": "music-corner", "name": "Community Concert Series", "category_slug": "live-music"}]
        visible = eligible_public_businesses(businesses, [])
        self.assertEqual([business["name"] for business in visible], ["Community Concert Series"])

    def test_public_businesses_keep_tomato_fest_like_row_without_name_matching(self):
        businesses = [{"id": "street-fest", "name": "Neighborhood Street Fest", "category_slug": "night-out"}]
        visible = eligible_public_businesses(businesses, [])
        self.assertEqual([business["name"] for business in visible], ["Neighborhood Street Fest"])

    def test_keeps_normal_live_music_venue_with_eligible_matched_event(self):
        businesses = [{"id": "music-corner", "name": "Ryman Auditorium"}]
        events = [{"id": "event-1", "venue_business_id": "music-corner", "title": "Sunday Show"}]
        visible = eligible_public_businesses(businesses, events)
        self.assertEqual(visible[0]["event"]["title"], "Sunday Show")

    def test_live_music_fallback_rejects_generic_entertainment_only_business(self):
        self.assertFalse(
            event_is_ticketmaster_music(
                {"source": "ticketmaster", "venue_business_id": "family-option"},
                {"id": "family-option", "slots": ["entertainment"], "category_slug": "family-fun", "tags": []},
            )
        )


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

    def test_rejects_unsupported_city(self):
        client = TicketmasterClient(api_key="backend-secret", opener=FakeOpener({}))
        with self.assertRaisesRegex(ValueError, "Unsupported city slug"):
            client.events_for_date("miami", "2026-06-01")

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
    def test_api_apply_confirmation_accepts_exact_approve_only(self):
        validate_apply_confirmation(False, "")
        validate_apply_confirmation(True, "APPROVE")
        for invalid in (None, "", "approve", " APPROVE", "APPROVE ", "anything"):
            with self.subTest(confirm=invalid):
                with self.assertRaisesRegex(ValueError, "Apply requires confirm=APPROVE"):
                    validate_apply_confirmation(True, invalid)

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

    def test_shared_upsert_and_cleanup_operations(self):
        document = ticketmaster_event_document(event(), "nashville", [])
        selector, update = event_upsert(document)
        self.assertEqual(selector, {"source": "ticketmaster", "external_event_id": "event-123"})
        self.assertEqual(update["$set"]["title"], "Nashville Predators vs. Example")
        self.assertEqual(update["$setOnInsert"]["id"], document["id"])
        self.assertEqual(
            expiration_cleanup_query("nashville", now=datetime(2026, 6, 1, 12, tzinfo=timezone.utc)),
            {
                "source": "ticketmaster",
                "city_slug": "nashville",
                "local_date": {"$lt": "2026-06-01"},
            },
        )

    def test_api_dry_run_response_format(self):
        response = api_sync_response(sync_report())
        self.assertEqual(response["mode"], "dry-run")
        self.assertTrue(response["success"])
        self.assertEqual(response["dates"], ["2026-06-01"])
        self.assertEqual(response["fetched"], 1)
        self.assertEqual(response["after_dedupe"], 1)
        self.assertEqual(response["would_upsert"], 1)
        self.assertEqual(len(response["sample_events"]), 1)
        self.assertNotIn("upserted", response)

    def test_api_apply_response_format(self):
        response = api_sync_response(sync_report(), {
            "upserted": 1,
            "modified": 2,
            "expired_deleted": 3,
            "expiration_cutoff": "2026-06-01",
        })
        self.assertEqual(response["mode"], "apply")
        self.assertEqual(response["upserted"], 1)
        self.assertEqual(response["updated"], 2)
        self.assertEqual(response["removed"], 3)


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def events_for_date(self, city_slug, local_date):
        self.city_slug = city_slug
        self.local_date = local_date
        return self.rows


def sync_report():
    return {
        "dates": ["2026-06-01"],
        "fetched": 1,
        "after_dedupe": 1,
        "would_upsert": 1,
        "duplicates_removed": 0,
        "matched": 0,
        "unmatched": 1,
        "events": [ticketmaster_event_document(event(), "nashville", [])],
    }


class FakeDateRangeClient:
    def __init__(self, rows_by_date):
        self.rows_by_date = rows_by_date

    def events_for_date(self, city_slug, local_date):
        return self.rows_by_date.get(local_date, [])


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
