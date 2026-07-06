"""Dependency-free tests for saved-itinerary source contracts and helpers."""
import ast
import os
import unittest
from pathlib import Path
from typing import List, Optional


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)


def named_function(name: str):
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def load_save_helpers():
    namespace = {
        "SLOT_LABELS": [
            {"slot": "dinner", "label": "Dinner", "emoji": "🍽️", "number": 1},
            {"slot": "drinks", "label": "Drinks", "emoji": "🍸", "number": 2},
            {"slot": "entertainment", "label": "Entertainment", "emoji": "🎵", "number": 3},
            {"slot": "late-night", "label": "Late Night", "emoji": "🌃", "number": 4},
        ],
        "Optional": Optional,
        "List": List,
        "os": os,
    }
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_slot_meta")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_locked_step")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_saved_itinerary_steps")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_valid_email")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_email_delivery_result")), namespace)
    return (
        namespace["_safe_saved_itinerary_steps"],
        namespace["_valid_email"],
        namespace["_email_delivery_result"],
    )


SAFE_SAVED_ITINERARY_STEPS, VALID_EMAIL, EMAIL_DELIVERY_RESULT = load_save_helpers()


class TestSavedItineraryContract(unittest.TestCase):
    def test_valid_save_request_persists_saved_itinerary_document(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('await db.saved_itineraries.insert_one(doc)', source)
        self.assertIn('"source_itinerary_id": payload.source_itinerary_id', source)
        self.assertIn('"locked_slots": safe_locked_slots', source)
        self.assertIn('"steps": safe_steps', source)
        self.assertIn('"delivery_channel": "email"', source)

    def test_invalid_email_is_rejected(self):
        self.assertTrue(VALID_EMAIL("traveler@example.com"))
        self.assertFalse(VALID_EMAIL("bad-email"))
        self.assertFalse(VALID_EMAIL("missing-domain@"))
        self.assertFalse(VALID_EMAIL("missingdot@example"))

    def test_provider_unconfigured_when_no_email_provider_exists(self):
        keys = ["RESEND_API_KEY", "SENDGRID_API_KEY", "MAILGUN_API_KEY", "SMTP_HOST", "SMTP_URL"]
        previous = {key: os.environ.get(key) for key in keys}
        try:
            for key in keys:
                os.environ.pop(key, None)
            result = EMAIL_DELIVERY_RESULT()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(result["delivery_status"], "provider_unconfigured")
        self.assertEqual(result["email_provider"], "")
        self.assertEqual(result["delivery_error"], "")
        self.assertIsNone(result["sent_at"])

    def test_saved_snapshot_includes_locked_slots_and_steps(self):
        steps = SAFE_SAVED_ITINERARY_STEPS([
            {
                "slot": "dinner",
                "business": {"id": "pelato", "name": "Pelato"},
            },
            {
                "slot": "entertainment",
                "business": {"id": "basement", "name": "The Basement East"},
                "event": {"external_event_id": "tm-1", "title": "Show"},
            },
        ])
        self.assertEqual([step["slot"] for step in steps], ["dinner", "entertainment"])
        self.assertEqual(steps[0]["business"]["id"], "pelato")
        self.assertEqual(steps[1]["event"]["external_event_id"], "tm-1")


if __name__ == "__main__":
    unittest.main()
