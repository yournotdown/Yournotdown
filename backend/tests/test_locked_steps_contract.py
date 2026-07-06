"""Dependency-free tests for locked-step snapshot handling in server source."""
import ast
from typing import Optional
import unittest
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)


def named_function(name: str) -> ast.FunctionDef:
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def load_locked_step_helpers():
    namespace = {
        "SLOT_LABELS": [
            {"slot": "dinner", "label": "Dinner", "emoji": "🍽️", "number": 1},
            {"slot": "drinks", "label": "Drinks", "emoji": "🍸", "number": 2},
            {"slot": "entertainment", "label": "Entertainment", "emoji": "🎵", "number": 3},
            {"slot": "late-night", "label": "Late Night", "emoji": "🌃", "number": 4},
        ],
        "Optional": Optional,
    }
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_slot_meta")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_locked_step")), namespace)
    return namespace["_safe_locked_step"]


SAFE_LOCKED_STEP = load_locked_step_helpers()


class TestLockedStepsContract(unittest.TestCase):
    def test_locked_non_entertainment_step_returns_snapshot_with_business_intact(self):
        snapshot = {
            "slot": "drinks",
            "number": 2,
            "label": "Drinks",
            "emoji": "🍸",
            "business": {
                "id": "patterson",
                "name": "The Patterson House",
                "address": "1711 Division St",
                "website": "https://example.com",
            },
        }
        step = SAFE_LOCKED_STEP("drinks", snapshot)
        self.assertEqual(step["slot"], "drinks")
        self.assertEqual(step["business"]["id"], "patterson")
        self.assertEqual(step["business"]["name"], "The Patterson House")
        self.assertEqual(step["business"]["address"], "1711 Division St")
        self.assertEqual(step["label"], "Drinks")

    def test_locked_entertainment_step_keeps_event_snapshot_intact(self):
        snapshot = {
            "slot": "entertainment",
            "business": {"id": "basement-east", "name": "The Basement East"},
            "event": {
                "external_event_id": "tm-123",
                "title": "Indie Show",
                "ticket_url": "https://tickets.example.com/show",
            },
        }
        step = SAFE_LOCKED_STEP("entertainment", snapshot)
        self.assertEqual(step["slot"], "entertainment")
        self.assertEqual(step["business"]["id"], "basement-east")
        self.assertEqual(step["event"]["external_event_id"], "tm-123")
        self.assertEqual(step["event"]["title"], "Indie Show")
        self.assertEqual(step["event"]["ticket_url"], "https://tickets.example.com/show")

    def test_locked_step_with_missing_business_is_still_safe_to_render(self):
        step = SAFE_LOCKED_STEP("late-night", {"slot": "late-night"})
        self.assertEqual(step["slot"], "late-night")
        self.assertEqual(step["business"]["id"], "")
        self.assertEqual(step["business"]["name"], "")
        self.assertEqual(step["label"], "Late Night")


if __name__ == "__main__":
    unittest.main()
