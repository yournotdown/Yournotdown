"""Dependency-free regression tests for itinerary seed slot assignment."""
import sys
import unittest
from collections import Counter
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from seed_data import (  # noqa: E402
    BUSINESSES,
    CATEGORY_MIGRATIONS,
    canonical_category_slug,
    default_slots_for_category,
)


class TestSeedSlots(unittest.TestCase):
    def test_legacy_category_mappings(self):
        self.assertEqual(
            CATEGORY_MIGRATIONS,
            {
                "food": "date-night",
                "sports": "night-out",
                "rooftops": "night-out",
                "events": "night-out",
            },
        )

    def test_every_seeded_business_has_default_slots(self):
        missing = [
            business["name"]
            for business in BUSINESSES
            if not default_slots_for_category(business["category_slug"])
        ]
        self.assertEqual(missing, [])

    def test_repaired_seed_candidate_pool_sizes(self):
        counts = Counter()
        for business in BUSINESSES:
            counts.update(default_slots_for_category(business["category_slug"]))

        self.assertEqual(
            counts,
            {
                "dinner": 7,
                "drinks": 4,
                "entertainment": 10,
                "late-night": 12,
            },
        )

    def test_slot_lists_are_fresh_copies(self):
        slots = default_slots_for_category("surprise-me")
        slots.clear()
        self.assertEqual(
            default_slots_for_category("surprise-me"),
            ["entertainment", "late-night"],
        )

    def test_unknown_category_has_no_default_slots(self):
        self.assertEqual(default_slots_for_category("unknown"), [])
        self.assertEqual(canonical_category_slug("unknown"), "unknown")


if __name__ == "__main__":
    unittest.main()
