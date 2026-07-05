"""Unit tests for admin itinerary bucket helpers."""
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from itinerary_buckets import annotate_itinerary_buckets, itinerary_buckets_for_business  # noqa: E402


class TestItineraryBuckets(unittest.TestCase):
    def test_maps_slots_to_admin_buckets(self):
        business = {"slots": ["dinner", "drinks", "entertainment", "late-night"]}
        self.assertEqual(
            itinerary_buckets_for_business(business),
            ["dinner", "drinks", "live_music", "late_night"],
        )

    def test_deduplicates_bucket_order(self):
        business = {"slots": ["entertainment", "entertainment", "late-night"]}
        self.assertEqual(itinerary_buckets_for_business(business), ["live_music", "late_night"])

    def test_annotates_admin_business_rows(self):
        rows = annotate_itinerary_buckets([
            {"id": "1", "name": "Exit/In", "slots": ["entertainment"]},
            {"id": "2", "name": "Luke's", "slots": []},
        ])
        self.assertEqual(rows[0]["itinerary_buckets"], ["live_music"])
        self.assertEqual(rows[1]["itinerary_buckets"], [])


if __name__ == "__main__":
    unittest.main()
