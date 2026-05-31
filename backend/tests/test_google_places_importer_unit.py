"""Dependency-free tests for the Google Places import pipeline."""
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from google_places_importer import (  # noqa: E402
    assign_slots,
    assign_tags,
    brand_fit_score,
    build_business_document,
    dedupe_documents,
    is_broadway_override,
    is_curator_allowlisted,
    report_template,
    run_import,
    should_import_place,
)


def place(**overrides):
    row = {
        "id": "places/example",
        "displayName": {"text": "The Example Room"},
        "formattedAddress": "123 Broadway, Nashville, TN 37201",
        "rating": 4.7,
        "userRatingCount": 350,
        "types": ["bar"],
        "googleMapsUri": "https://maps.google.com/example",
    }
    row.update(overrides)
    return row


class TestFiltering(unittest.TestCase):
    def test_accepts_high_quality_place(self):
        self.assertEqual(should_import_place(place()), (True, "accepted"))

    def test_rejects_low_rating(self):
        self.assertEqual(
            should_import_place(place(rating=4.1)),
            (False, "rating_below_4_2"),
        )

    def test_rejects_low_review_count(self):
        self.assertEqual(
            should_import_place(place(userRatingCount=99)),
            (False, "rating_count_below_100"),
        )

    def test_rejects_fast_food_and_chains(self):
        self.assertEqual(
            should_import_place(place(types=["fast_food_restaurant"])),
            (False, "fast_food"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Starbucks Reserve"})),
            (False, "excluded_chain"),
        )

    def test_rejects_out_of_area_mall_airport_and_plain_hotel(self):
        self.assertEqual(
            should_import_place(place(formattedAddress="123 Main St, Franklin, TN 37064")),
            (False, "outside_target_zip_codes"),
        )
        self.assertEqual(
            should_import_place(place(formattedAddress="Example Mall Food Court, Nashville, TN 37201")),
            (False, "mall_food"),
        )
        self.assertEqual(
            should_import_place(place(formattedAddress="1 Nashville Airport Rd, Nashville, TN 37201")),
            (False, "airport_food"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Example Hotel"}, types=["lodging"])),
            (False, "hotel_without_notable_venue"),
        )

    def test_allows_notable_hotel_rooftop_bar(self):
        self.assertEqual(
            should_import_place(place(displayName={"text": "Example Hotel Rooftop Bar"}, types=["lodging", "bar"])),
            (True, "accepted"),
        )

    def test_curator_allowlist_bypasses_low_review_count(self):
        row = place(displayName={"text": "Le Loup"}, userRatingCount=83)
        self.assertTrue(is_curator_allowlisted(row))
        self.assertEqual(should_import_place(row), (True, "accepted"))

    def test_curator_allowlist_matches_google_name_suffixes(self):
        self.assertTrue(
            is_curator_allowlisted(
                place(displayName={"text": "Streetcar Taps & Garden - Germantown"})
            )
        )

    def test_curator_allowlist_does_not_bypass_rating_floor_or_safety_filters(self):
        self.assertEqual(
            should_import_place(place(displayName={"text": "Le Loup"}, rating=4.1)),
            (False, "rating_below_4_2"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Le Loup"}, types=["gas_station"])),
            (False, "blocked_place_type"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Le Loup"}, formattedAddress="123 Main St, Franklin, TN 37064")),
            (False, "outside_target_zip_codes"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Le Loup"}, formattedAddress="Example Mall Food Court, Nashville, TN 37201")),
            (False, "mall_food"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Le Loup"}, formattedAddress="Inside Hustler Club, Nashville, TN 37201")),
            (False, "adult_venue"),
        )

    def test_rejects_daytime_only_inventory(self):
        self.assertEqual(
            should_import_place(place(displayName={"text": "Example Museum"}, types=["museum", "tourist_attraction"])),
            (False, "daytime_only_attraction"),
        )
        self.assertEqual(
            should_import_place(place(displayName={"text": "Example Park"}, types=["park", "tourist_attraction"])),
            (False, "daytime_only_attraction"),
        )

    def test_broadway_override_bypasses_review_count_but_not_rating_floor(self):
        row = place(displayName={"text": "Chief's on Broadway"}, userRatingCount=12)
        self.assertTrue(is_broadway_override(row))
        self.assertEqual(should_import_place(row), (True, "accepted"))
        self.assertEqual(
            should_import_place(place(displayName={"text": "Chief's on Broadway"}, rating=4.1)),
            (False, "rating_below_4_2"),
        )

    def test_broadway_override_allows_nashville_37219_but_not_out_of_area(self):
        self.assertEqual(
            should_import_place(
                place(
                    displayName={"text": "Morgan Wallen's This Bar"},
                    formattedAddress="107 4th Ave N, Nashville, TN 37219",
                )
            ),
            (True, "accepted"),
        )
        self.assertEqual(
            should_import_place(
                place(
                    displayName={"text": "Morgan Wallen's This Bar"},
                    formattedAddress="123 Main St, Franklin, TN 37064",
                )
            ),
            (False, "outside_target_zip_codes"),
        )


class TestClassification(unittest.TestCase):
    def test_assigns_honky_tonk_tags_and_slots(self):
        row = place(displayName={"text": "Downtown Honky Tonk"}, types=["bar", "live_music_venue"])
        tags = assign_tags(row, ["honky tonks in downtown Nashville"])
        self.assertTrue({"honky_tonk", "live_music", "nightlife", "late_night"} <= set(tags))
        self.assertEqual(assign_slots(row, tags), ["drinks", "entertainment", "late-night"])

    def test_restaurant_gets_dinner_slot_and_date_tag(self):
        row = place(types=["restaurant", "fine_dining_restaurant"])
        tags = assign_tags(row, ["date night restaurants in 37203 Nashville"])
        self.assertIn("date_night", tags)
        self.assertEqual(assign_slots(row, tags), ["dinner"])

    def test_rooftop_bar_gets_drinks_and_late_night(self):
        row = place(displayName={"text": "Skyline Rooftop"}, types=["bar"])
        tags = assign_tags(row, ["rooftop bars in 37203 Nashville"])
        self.assertTrue({"rooftop", "scenic"} <= set(tags))
        self.assertEqual(assign_slots(row, tags), ["drinks", "late-night"])

    def test_broadway_document_has_override_category(self):
        document = build_business_document(
            place(displayName={"text": "The Stage on Broadway"}, userRatingCount=20),
            ["The Stage Nashville"],
        )
        self.assertEqual(document["import_override_reason"], "broadway_override")
        self.assertIn("Broadway", document["nightlife_categories"])

    def test_query_context_assigns_nightlife_categories(self):
        row = place(types=["restaurant"])
        tags = assign_tags(
            row,
            [
                "date night restaurants in 37203 Nashville",
                "speakeasies in 37203 Nashville",
            ],
        )
        self.assertTrue({"date_night", "speakeasy"} <= set(tags))

    def test_brand_fit_prioritizes_destination_venue(self):
        venue = place(
            displayName={"text": "Downtown Rooftop Honky Tonk"},
            types=["bar", "live_music_venue"],
            userRatingCount=5000,
        )
        generic = place(displayName={"text": "Example Restaurant"}, types=["restaurant"], userRatingCount=150)
        venue_tags = assign_tags(venue, ["honky tonks in downtown Nashville"])
        generic_tags = assign_tags(generic, ["best restaurants in 37201 Nashville"])
        self.assertGreaterEqual(brand_fit_score(venue, venue_tags, []), 70)
        self.assertLess(brand_fit_score(generic, generic_tags, []), 70)


class TestDedupeAndStatus(unittest.TestCase):
    def test_document_defaults_to_pending(self):
        document = build_business_document(place(), ["cocktail bars in 37201 Nashville"])
        self.assertEqual(document["imported_status"], "pending")
        self.assertEqual(document["city_slug"], "nashville")
        self.assertEqual(document["google_place_id"], "places/example")

    def test_allowlisted_document_is_pending_with_override_reason_and_actual_metrics(self):
        document = build_business_document(
            place(displayName={"text": "Le Loup"}, rating=4.4, userRatingCount=83),
            ["best restaurants in 37208 Nashville"],
        )
        self.assertEqual(document["imported_status"], "pending")
        self.assertEqual(document["import_override_reason"], "curator_allowlist")
        self.assertEqual(document["google_rating"], 4.4)
        self.assertEqual(document["google_user_rating_count"], 83)
        self.assertLess(document["brand_fit_score"], 70)

    def test_dedupes_by_google_place_id(self):
        first = build_business_document(place(), ["cocktail bars"])
        second = {**first, "name": "Renamed Place"}
        unique, duplicates = dedupe_documents([first, second])
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)

    def test_dedupes_by_normalized_name_and_address(self):
        first = build_business_document(place(id="places/one"), ["cocktail bars"])
        second = build_business_document(
            place(id="places/two", displayName={"text": " THE example room "}),
            ["cocktail bars"],
        )
        unique, duplicates = dedupe_documents([first, second])
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)

    def test_report_template_is_no_network_dry_run_shape(self):
        report = report_template()
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["pending"], 0)
        self.assertEqual(report["approved"], 0)
        self.assertEqual(
            report["candidate_pool_by_slot"],
            {"dinner": 0, "drinks": 0, "entertainment": 0, "late-night": 0},
        )

    def test_dry_run_report_counts_without_writing(self):
        accepted = place(
            id="places/accepted",
            displayName={"text": "Downtown Rooftop Honky Tonk"},
            types=["bar", "live_music_venue"],
            userRatingCount=5000,
        )
        duplicate = place(
            id="places/existing",
            displayName={"text": "Existing Rooftop Honky Tonk"},
            types=["bar", "live_music_venue"],
            userRatingCount=5000,
        )
        rejected = place(id="places/rejected", rating=4.0)

        class FakeClient:
            def search_text(self, query):
                return [accepted, duplicate, rejected]

            def place_details(self, place_id):
                return {
                    row["id"]: row
                    for row in [accepted, duplicate, rejected]
                }[place_id]

        report = run_import(
            FakeClient(),
            existing=[{"google_place_id": "places/existing", "name": "Existing Place", "address": duplicate["formattedAddress"]}],
            dry_run=True,
            zip_codes=["37201"],
            query_limit=1,
        )
        self.assertEqual(report["found"], 3)
        self.assertEqual(report["details_fetched"], 3)
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(report["duplicated"], 1)
        self.assertEqual(report["pending"], 1)
        self.assertEqual(report["approved"], 0)
        self.assertEqual(report["inserted"], 0)
        self.assertEqual(report["nightlife_inventory"]["total_nightlife_venues"], 1)
        self.assertEqual(report["nightlife_inventory"]["rooftops"], 1)

    def test_dry_run_includes_allowlisted_low_score_candidate(self):
        allowlisted = place(
            id="places/le-loup",
            displayName={"text": "Le Loup"},
            rating=4.4,
            userRatingCount=83,
            types=["restaurant"],
            formattedAddress="1400 Adams St, Nashville, TN 37208",
        )

        class FakeClient:
            def search_text(self, query):
                return [allowlisted]

            def place_details(self, place_id):
                return allowlisted

        report = run_import(FakeClient(), dry_run=True, zip_codes=["37208"], query_limit=1)
        self.assertEqual(report["pending"], 1)
        self.assertEqual(report["skipped"], 0)
        self.assertEqual(report["top_pending_candidates"][0]["name"], "Le Loup")
        self.assertEqual(
            report["top_pending_candidates"][0]["import_override_reason"],
            "curator_allowlist",
        )
        le_loup = next(
            row for row in report["curator_allowlist_results"]
            if row["name"] == "Le Loup"
        )
        self.assertTrue(le_loup["included"])
        self.assertEqual(le_loup["import_override_reason"], "curator_allowlist")
        self.assertTrue(
            any(
                row["name"] == "The Henry"
                and row["rejection_reason"] == "not_discovered"
                for row in report["curator_allowlist_results"]
            )
        )


if __name__ == "__main__":
    unittest.main()
