"""Unit tests for featured live music override helpers."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from featured_live_music import (  # noqa: E402
    LIVE_MUSIC_EVENT_MODE_TICKETMASTER_PREFERRED,
    active_featured_live_music_event,
    featured_event_is_active,
    featured_live_music_is_excluded,
    featured_live_music_business,
    featured_live_music_pick,
    featured_live_music_step_event,
    normalize_live_music_event_mode,
)


class TestFeaturedLiveMusic(unittest.TestCase):
    def test_active_featured_event_overrides_by_priority_then_time_then_created_at(self):
        rows = [
            {
                "id": "priority-two",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 2,
                "title": "Priority Two",
                "local_date": "2026-07-05",
                "local_time": "20:00:00",
                "created_at": "2026-07-05T08:00:00+00:00",
                "updated_at": "2026-07-05T10:00:00+00:00",
            },
            {
                "id": "priority-one-early",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 1,
                "title": "Priority One Early",
                "local_date": "2026-07-05",
                "local_time": "19:00:00",
                "created_at": "2026-07-05T07:00:00+00:00",
                "updated_at": "2026-07-05T09:00:00+00:00",
            },
            {
                "id": "priority-one-later",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 1,
                "title": "Priority One Later",
                "local_date": "2026-07-05",
                "local_time": "21:00:00",
                "created_at": "2026-07-05T11:00:00+00:00",
                "updated_at": "2026-07-05T09:00:00+00:00",
            },
        ]
        selected = active_featured_live_music_event(
            rows,
            "nashville",
            now=datetime(2026, 7, 5, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(selected["id"], "priority-one-early")

    def test_same_priority_prefers_more_recent_created_at(self):
        rows = [
            {
                "id": "older",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 1,
                "title": "Older Created",
                "local_date": "2026-07-05",
                "local_time": "20:00:00",
                "created_at": "2026-07-05T08:00:00+00:00",
            },
            {
                "id": "newer",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 1,
                "title": "Newer Created",
                "local_date": "2026-07-05",
                "local_time": "20:00:00",
                "created_at": "2026-07-05T09:00:00+00:00",
            },
        ]
        selected = active_featured_live_music_event(
            rows,
            "nashville",
            now=datetime(2026, 7, 5, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(selected["id"], "newer")

    def test_inactive_or_expired_featured_event_does_not_apply(self):
        now = datetime(2026, 7, 5, 18, tzinfo=timezone.utc)
        self.assertFalse(
            featured_event_is_active(
                {
                    "city_slug": "nashville",
                    "slot": "live_music",
                    "active": False,
                    "local_date": "2026-07-05",
                },
                "nashville",
                now=now,
            )
        )
        self.assertFalse(
            featured_event_is_active(
                {
                    "city_slug": "nashville",
                    "slot": "live_music",
                    "active": True,
                    "local_date": "2026-07-05",
                    "active_until": "2026-07-05T10:00:00",
                },
                "nashville",
                now=now,
            )
        )

    def test_future_featured_event_outside_tonight_window_does_not_apply(self):
        self.assertIsNone(
            active_featured_live_music_event(
                [{
                    "id": "future",
                    "city_slug": "nashville",
                    "slot": "live_music",
                    "active": True,
                    "local_date": "2026-08-15",
                    "local_time": "20:00:00",
                }],
                "nashville",
                now=datetime(2026, 7, 5, 18, tzinfo=timezone.utc),
            )
        )

    def test_missing_date_or_time_does_not_apply(self):
        now = datetime(2026, 7, 5, 18, tzinfo=timezone.utc)
        self.assertFalse(
            featured_event_is_active(
                {
                    "city_slug": "nashville",
                    "slot": "live_music",
                    "active": True,
                    "local_date": "",
                    "local_time": "21:00:00",
                },
                "nashville",
                now=now,
            )
        )
        self.assertFalse(
            featured_event_is_active(
                {
                    "city_slug": "nashville",
                    "slot": "live_music",
                    "active": True,
                    "local_date": "2026-07-05",
                    "local_time": "",
                },
                "nashville",
                now=now,
            )
        )

    def test_featured_event_can_be_mapped_to_step_business_and_event(self):
        record = {
            "id": "feature-1",
            "city_slug": "nashville",
            "slot": "live_music",
            "active": True,
            "title": "Featured Show",
            "venue_name": "Exit/In",
            "description": "Paid promo",
            "image_url": "https://example.com/featured.jpg",
            "ticket_url": "https://tickets.example.com",
            "local_date": "2026-07-05",
            "local_time": "21:00",
        }
        business = featured_live_music_business(record)
        event = featured_live_music_step_event(record)
        self.assertEqual(business["name"], "Exit/In")
        self.assertEqual(event["title"], "Featured Show")
        self.assertEqual(event["ticket_url"], "https://tickets.example.com")

    def test_featured_event_preserves_uploaded_image_path(self):
        record = {
            "id": "feature-2",
            "city_slug": "nashville",
            "slot": "live_music",
            "active": True,
            "title": "Uploaded Art Show",
            "venue_name": "Brooklyn Bowl",
            "image_url": "https://example.com/fallback.jpg",
            "image_path": "your-not-down/images/admin/uploaded.webp",
        }
        business = featured_live_music_business(record)
        event = featured_live_music_step_event(record)
        self.assertEqual(business["image_path"], "your-not-down/images/admin/uploaded.webp")
        self.assertEqual(business["image_url"], "https://example.com/fallback.jpg")
        self.assertEqual(event["image_path"], "your-not-down/images/admin/uploaded.webp")
        self.assertEqual(event["image_url"], "https://example.com/fallback.jpg")

    def test_featured_pick_returns_business_and_event_without_override_flag(self):
        record = {
            "id": "feature-3",
            "city_slug": "nashville",
            "slot": "live_music",
            "active": True,
            "priority": 1,
            "title": "Priority One Show",
            "venue_name": "The Basement East",
            "local_date": "2026-07-05",
            "local_time": "20:30:00",
        }
        business, event = featured_live_music_pick(record)
        self.assertEqual(business["id"], "featured-live-music-feature-3")
        self.assertEqual(event["source"], "admin_featured_event")
        self.assertEqual(event["title"], "Priority One Show")

    def test_sponsorship_fields_do_not_control_featured_visibility(self):
        rows = [
            {
                "id": "feature-4",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 1,
                "title": "Visible Without Sponsorship",
                "venue_name": "Mercy Lounge",
                "local_date": "2026-07-05",
                "local_time": "20:00:00",
                "sponsorship_active": False,
                "sponsor_tier": "none",
                "sponsored": False,
            },
        ]
        selected = active_featured_live_music_event(
            rows,
            "nashville",
            now=datetime(2026, 7, 5, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(selected["id"], "feature-4")

    def test_featured_event_is_excluded_by_synthetic_business_id(self):
        record = {"id": "feature-3", "venue_business_id": "", "slot": "live_music"}
        self.assertTrue(
            featured_live_music_is_excluded(
                record,
                {"featured-live-music-feature-3"},
                set(),
            )
        )

    def test_featured_event_is_excluded_by_event_id(self):
        record = {"id": "feature-3", "venue_business_id": "venue-123", "slot": "live_music"}
        self.assertTrue(
            featured_live_music_is_excluded(
                record,
                set(),
                {"feature-3"},
            )
        )

    def test_featured_event_remains_available_when_not_excluded(self):
        record = {"id": "feature-3", "venue_business_id": "venue-123", "slot": "live_music"}
        self.assertFalse(
            featured_live_music_is_excluded(
                record,
                {"other-venue"},
                {"other-feature"},
            )
        )

    def test_normalizes_first_load_mode(self):
        self.assertEqual(
            normalize_live_music_event_mode("ticketmaster_preferred"),
            LIVE_MUSIC_EVENT_MODE_TICKETMASTER_PREFERRED,
        )
        self.assertEqual(normalize_live_music_event_mode("weird"), "normal")


if __name__ == "__main__":
    unittest.main()
