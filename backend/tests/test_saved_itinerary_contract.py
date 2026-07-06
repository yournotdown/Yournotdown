"""Dependency-free tests for saved-itinerary source contracts and helpers."""
import ast
import os
from datetime import datetime, timezone
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
        "requests": __import__("requests"),
        "now_iso": lambda: datetime(2026, 7, 6, 17, 0, tzinfo=timezone.utc).isoformat(),
    }
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_slot_meta")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_locked_step")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_saved_itinerary_steps")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_valid_email")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_email_delivery_result")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_saved_itinerary_email_subject")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_saved_itinerary_step_lines")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_saved_itinerary_email_content")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_send_resend_email")), namespace)
    return (
        namespace["_safe_saved_itinerary_steps"],
        namespace["_valid_email"],
        namespace["_email_delivery_result"],
        namespace["_saved_itinerary_email_content"],
        namespace["_send_resend_email"],
    )


SAFE_SAVED_ITINERARY_STEPS, VALID_EMAIL, EMAIL_DELIVERY_RESULT, EMAIL_CONTENT, SEND_RESEND_EMAIL = load_save_helpers()


class TestSavedItineraryContract(unittest.TestCase):
    def test_valid_save_request_persists_saved_itinerary_document(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('await db.saved_itineraries.insert_one(doc)', source)
        self.assertIn('await db.saved_itineraries.update_one(', source)
        self.assertIn('"source_itinerary_id": payload.source_itinerary_id', source)
        self.assertIn('"locked_slots": safe_locked_slots', source)
        self.assertIn('"steps": safe_steps', source)
        self.assertIn('"delivery_channel": "email"', source)
        self.assertIn('"provider_message_id": delivery["provider_message_id"]', source)

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
        self.assertEqual(result["provider_message_id"], "")
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

    def test_email_content_includes_locked_steps_and_footer(self):
        text_body, html_body = EMAIL_CONTENT({
            "city_slug": "nashville",
            "vibe": "send-it",
            "steps": [
                {
                    "number": 1,
                    "label": "Dinner",
                    "business": {"name": "Pelato", "address": "123 Main", "website": "https://pelato.example"},
                },
                {
                    "number": 3,
                    "label": "Entertainment",
                    "business": {"name": "The Basement East"},
                    "event": {"title": "Indie Show", "local_time": "20:00:00", "ticket_url": "https://tickets.example"},
                },
            ],
        })
        self.assertIn("YourNotDown / Tonight's Move", text_body)
        self.assertIn("Pelato", text_body)
        self.assertIn("Indie Show", text_body)
        self.assertIn("Built with YourNotDown", text_body)
        self.assertIn("Tonight's Move", html_body)
        self.assertIn("https://tickets.example", html_body)

    def test_sent_status_when_mocked_resend_succeeds(self):
        class FakeResponse:
            content = b'{"id":"msg_123"}'

            @staticmethod
            def raise_for_status():
                return None

            @staticmethod
            def json():
                return {"id": "msg_123"}

        requests_module = SEND_RESEND_EMAIL.__globals__["requests"]
        original_post = requests_module.post
        previous = {
            "RESEND_API_KEY": os.environ.get("RESEND_API_KEY"),
            "RESEND_FROM_EMAIL": os.environ.get("RESEND_FROM_EMAIL"),
            "RESEND_REPLY_TO": os.environ.get("RESEND_REPLY_TO"),
        }
        try:
            os.environ["RESEND_API_KEY"] = "test-key"
            os.environ["RESEND_FROM_EMAIL"] = "hello@yournotdown.com"
            os.environ["RESEND_REPLY_TO"] = "reply@yournotdown.com"
            requests_module.post = lambda *args, **kwargs: FakeResponse()
            result = SEND_RESEND_EMAIL({
                "email": "traveler@example.com",
                "city_slug": "nashville",
                "vibe": "down",
                "steps": [],
            })
        finally:
            requests_module.post = original_post
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(result["delivery_status"], "sent")
        self.assertEqual(result["email_provider"], "resend")
        self.assertEqual(result["provider_message_id"], "msg_123")
        self.assertEqual(result["delivery_error"], "")
        self.assertTrue(result["sent_at"])

    def test_failed_status_when_mocked_resend_fails(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('except requests.RequestException as exc:', source)
        self.assertIn('"delivery_status": "failed"', source)
        self.assertIn('"email_provider": "resend"', source)


if __name__ == "__main__":
    unittest.main()
