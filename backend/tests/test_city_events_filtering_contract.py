"""Dependency-free contract tests for shared city event filtering."""
import ast
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)


def named_function(name: str) -> ast.AsyncFunctionDef:
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )


class TestCityEventsFilteringContract(unittest.TestCase):
    def test_server_imports_shared_event_eligibility_helper(self):
        self.assertIn("eligible_city_events", SERVER_SOURCE)
        self.assertIn("eligible_public_businesses", SERVER_SOURCE)

    def test_today_events_route_uses_shared_filter_after_loading_rows(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_today_city_events"))
        self.assertIn('event_date = local_today(city)', source)
        self.assertIn('rows = await db.city_events.find(', source)
        self.assertIn('return eligible_city_events(rows, city, grace_minutes=EVENT_START_GRACE_MINUTES)', source)

    def test_public_businesses_route_uses_shared_filter_after_loading_today_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_public_businesses"))
        self.assertIn('return eligible_public_businesses(businesses, event_rows if event_rows is not None else await _today_city_events(city))', source)

    def test_itinerary_generation_uses_filtered_today_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("generate_itinerary"))
        self.assertIn("event_rows = await _today_city_events(req.city)", source)
        self.assertIn("all_biz = await _public_businesses(req.city, limit=2000, require_slots=True, event_rows=event_rows)", source)
        self.assertIn("today_events_by_business = events_by_business_id(event_rows)", source)


if __name__ == "__main__":
    unittest.main()
