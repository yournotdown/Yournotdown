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
    featured_live_music_business,
    featured_live_music_step_event,
    normalize_live_music_event_mode,
)


class TestFeaturedLiveMusic(unittest.TestCase):
    def test_active_featured_event_overrides_by_priority_then_updated_at(self):
        rows = [
            {
                "id": "low",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 1,
                "title": "Low Priority",
                "local_date": "2026-07-05",
                "local_time": "20:00:00",
                "updated_at": "2026-07-05T10:00:00+00:00",
            },
            {
                "id": "high",
                "city_slug": "nashville",
                "slot": "live_music",
                "active": True,
                "priority": 5,
                "title": "High Priority",
                "local_date": "2026-07-05",
                "local_time": "21:00:00",
                "updated_at": "2026-07-05T09:00:00+00:00",
            },
        ]
        selected = active_featured_live_music_event(
            rows,
            "nashville",
            now=datetime(2026, 7, 5, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(selected["id"], "high")

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

    def test_normalizes_first_load_mode(self):
        self.assertEqual(
            normalize_live_music_event_mode("ticketmaster_preferred"),
            LIVE_MUSIC_EVENT_MODE_TICKETMASTER_PREFERRED,
        )
        self.assertEqual(normalize_live_music_event_mode("weird"), "normal")


if __name__ == "__main__":
    unittest.main()
