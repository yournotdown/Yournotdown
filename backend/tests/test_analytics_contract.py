"""Dependency-free source contracts for sponsor-grade analytics tracking."""
import ast
import unittest
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)


def named_function(name: str):
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


class TestAnalyticsContract(unittest.TestCase):
    def test_business_scoped_events_include_ticket_locked_and_saved_types(self):
        source = SERVER_SOURCE
        self.assertIn('"ticket_click"', source)
        self.assertIn('"step_locked"', source)
        self.assertIn('"saved_itinerary_business"', source)

    def test_business_appearance_events_now_stamp_slot(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("generate_itinerary"))
        self.assertIn('slot=step.get("slot", "")', source)
        self.assertIn('source_surface="tonight_page"', source)

    def test_track_endpoint_stamps_sponsor_tier_for_business_scoped_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("track_event"))
        self.assertIn("event.event_type in BUSINESS_SCOPED_EVENT_TYPES", source)
        self.assertIn('"visitor_id": _normalize_visitor_id(event.visitor_id) or None', source)
        self.assertIn('"slot": event.slot', source)
        self.assertIn('"event_id": event.event_id', source)
        self.assertIn('"event_source": event.event_source', source)
        self.assertIn("await _upsert_visitor_profile(", source)

    def test_visitor_profile_helper_tracks_first_and_repeat_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_upsert_visitor_profile"))
        self.assertIn('"visitor_id": visitor_id', source)
        self.assertIn('"first_seen_at": now', source)
        self.assertIn('"last_seen_at": now', source)
        self.assertIn('"event_count": int(existing.get("event_count", 0)) + 1', source)
        self.assertIn('"saved_itinerary_count": int(existing.get("saved_itinerary_count", 0)) + (1 if increment_saved_itinerary else 0)', source)

    def test_missing_visitor_id_is_ignored_safely(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_upsert_visitor_profile"))
        self.assertIn("if not visitor_id:", source)
        self.assertIn("return None", source)

    def test_save_itinerary_writes_saved_business_analytics_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('"saved_itinerary_business"', source)
        self.assertIn('await db.analytics_events.insert_many(saved_step_events)', source)
        self.assertIn('logger.warning("saved_itinerary_business analytics write failed: %s", exc)', source)

    def test_admin_summary_supports_filters_and_leaderboards(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_analytics_summary"))
        self.assertIn('days: str = "30"', source)
        self.assertIn("city_slug: Optional[str] = None", source)
        self.assertIn("vibe: Optional[str] = None", source)
        self.assertIn("slot: Optional[str] = None", source)
        self.assertIn('"slot_leaderboards": slot_leaderboards', source)
        self.assertIn('"top_saved_in_final_move_businesses": top_saved_in_final_move_businesses', source)
        self.assertIn('"top_website_click_businesses": top_website_click_businesses', source)
        self.assertIn('"top_directions_click_businesses": top_directions_click_businesses', source)
        self.assertIn('"top_phone_click_businesses": top_phone_click_businesses', source)
        self.assertIn('"top_click_through_businesses": top_click_through_businesses', source)
        self.assertIn('"top_sponsor_businesses": top_sponsor_businesses', source)
        self.assertIn('"vibe_breakdown": vibe_breakdown', source)
        self.assertIn('"totals": totals', source)

    def test_metric_aliases_define_total_engagement_and_safe_rate(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_metric_aliases"))
        self.assertIn('"appearances": counts.get("business_appearance", 0)', source)
        self.assertIn('"locked_in": counts.get("step_locked", 0)', source)
        self.assertIn('"saved_in_final_move": counts.get("saved_itinerary_business", 0)', source)
        self.assertIn('"ticket_clicks": counts.get("ticket_click", 0)', source)
        self.assertIn('if counts.get("business_appearance", 0)', source)


if __name__ == "__main__":
    unittest.main()
