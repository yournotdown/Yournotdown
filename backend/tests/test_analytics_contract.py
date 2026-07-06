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
        self.assertIn('"slot": event.slot', source)
        self.assertIn('"event_id": event.event_id', source)
        self.assertIn('"event_source": event.event_source', source)

    def test_save_itinerary_writes_saved_business_analytics_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('"saved_itinerary_business"', source)
        self.assertIn('await db.analytics_events.insert_many(saved_step_events)', source)
        self.assertIn('logger.warning("saved_itinerary_business analytics write failed: %s", exc)', source)


if __name__ == "__main__":
    unittest.main()
