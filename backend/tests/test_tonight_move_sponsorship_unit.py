"""Unit tests for Tonight's Move sponsorship helpers."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from tonight_move_sponsorship import (  # noqa: E402
    TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
    active_tonight_move_sponsorship,
    sponsorship_is_active,
)


class TestTonightMoveSponsorship(unittest.TestCase):
    def test_active_sponsorship_applies_when_window_and_placement_match(self):
        now = datetime(2026, 7, 5, 18, tzinfo=timezone.utc)
        self.assertTrue(
            sponsorship_is_active(
                {
                    "city_slug": "nashville",
                    "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
                    "active": True,
                    "active_from": "2026-07-05T10:00:00",
                    "active_until": "2026-07-05T23:59:00",
                },
                "nashville",
                now=now,
            )
        )

    def test_inactive_sponsorship_does_not_apply(self):
        self.assertFalse(
            sponsorship_is_active(
                {
                    "city_slug": "nashville",
                    "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
                    "active": False,
                },
                "nashville",
            )
        )

    def test_expired_sponsorship_does_not_apply(self):
        now = datetime(2026, 7, 5, 18, tzinfo=timezone.utc)
        self.assertFalse(
            sponsorship_is_active(
                {
                    "city_slug": "nashville",
                    "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
                    "active": True,
                    "active_until": "2026-07-05T10:00:00",
                },
                "nashville",
                now=now,
            )
        )

    def test_highest_priority_active_sponsorship_wins(self):
        selected = active_tonight_move_sponsorship(
            [
                {
                    "id": "low",
                    "city_slug": "nashville",
                    "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
                    "active": True,
                    "priority": 1,
                    "sponsor_name": "Low",
                    "updated_at": "2026-07-05T10:00:00+00:00",
                },
                {
                    "id": "high",
                    "city_slug": "nashville",
                    "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
                    "active": True,
                    "priority": 9,
                    "sponsor_name": "High",
                    "updated_at": "2026-07-05T09:00:00+00:00",
                },
            ],
            "nashville",
        )
        self.assertEqual(selected["id"], "high")

    def test_city_and_placement_must_match(self):
        self.assertIsNone(
            active_tonight_move_sponsorship(
                [
                    {
                        "id": "wrong-city",
                        "city_slug": "miami",
                        "placement": TONIGHT_MOVE_SPONSORSHIP_PLACEMENT,
                        "active": True,
                    },
                    {
                        "id": "wrong-placement",
                        "city_slug": "nashville",
                        "placement": "other",
                        "active": True,
                    },
                ],
                "nashville",
            )
        )


if __name__ == "__main__":
    unittest.main()
