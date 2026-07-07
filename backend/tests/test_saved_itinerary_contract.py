"""Dependency-free tests for saved-itinerary source contracts and helpers."""
import ast
import os
from datetime import datetime, timezone
import unittest
from html import unescape
from pathlib import Path
from typing import List, Optional


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)
EMAIL_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "saved_itinerary_email.py"
EMAIL_TEMPLATE_SOURCE = EMAIL_TEMPLATE_PATH.read_text()
EMAIL_TEMPLATE_TREE = ast.parse(EMAIL_TEMPLATE_SOURCE)


def named_function(name: str):
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def template_named_function(name: str):
    return next(
        node
        for node in EMAIL_TEMPLATE_TREE.body
        if isinstance(node, ast.FunctionDef) and node.name == name
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
        "saved_itinerary_email_content": None,
        "saved_itinerary_email_subject": None,
        "now_iso": lambda: datetime(2026, 7, 6, 17, 0, tzinfo=timezone.utc).isoformat(),
    }
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_slot_meta")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_locked_step")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_safe_saved_itinerary_steps")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_valid_email")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_email_delivery_result")), namespace)
    template_namespace = {
        "html": __import__("html"),
        "os": os,
        "datetime": datetime,
        "quote_plus": __import__("urllib.parse").parse.quote_plus,
    }
    for assign_name in ("VIBE_META", "STEP_LABELS", "EMAIL_SUBJECT", "EMAIL_PREHEADER"):
        assign_node = next(
            node
            for node in EMAIL_TEMPLATE_TREE.body
            if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == assign_name for target in node.targets)
        )
        exec(ast.get_source_segment(EMAIL_TEMPLATE_SOURCE, assign_node), template_namespace)
    for fn_name in (
        "_escape",
        "_friendly_vibe_label",
        "_friendly_city_label",
        "_friendly_step_label",
        "_friendly_time",
        "_directions_url",
        "_step_links",
        "_step_card_html",
        "_text_step_block",
        "saved_itinerary_email_subject",
        "saved_itinerary_email_preheader",
        "saved_itinerary_email_content",
    ):
        exec(ast.get_source_segment(EMAIL_TEMPLATE_SOURCE, template_named_function(fn_name)), template_namespace)
    namespace["saved_itinerary_email_subject"] = template_namespace["saved_itinerary_email_subject"]
    namespace["saved_itinerary_email_content"] = template_namespace["saved_itinerary_email_content"]
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_saved_itinerary_email_subject")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_saved_itinerary_email_content")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_send_resend_email")), namespace)
    return (
        namespace["_safe_saved_itinerary_steps"],
        namespace["_valid_email"],
        namespace["_email_delivery_result"],
        namespace["_saved_itinerary_email_subject"],
        namespace["_saved_itinerary_email_content"],
        namespace["_send_resend_email"],
        template_namespace["saved_itinerary_email_preheader"],
        template_namespace["_friendly_time"],
    )


(
    SAFE_SAVED_ITINERARY_STEPS,
    VALID_EMAIL,
    EMAIL_DELIVERY_RESULT,
    EMAIL_SUBJECT,
    EMAIL_CONTENT,
    SEND_RESEND_EMAIL,
    EMAIL_PREHEADER,
    FRIENDLY_TIME,
) = load_save_helpers()


class TestSavedItineraryContract(unittest.TestCase):
    def test_valid_save_request_persists_saved_itinerary_document(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('await db.saved_itineraries.insert_one(doc)', source)
        self.assertIn('"visitor_id": visitor_id or None', source)
        self.assertIn('"marketing_opt_in": bool(payload.marketing_opt_in)', source)
        self.assertIn('await _upsert_audience_contact(', source)
        self.assertIn("await _upsert_visitor_profile(", source)
        self.assertIn('await db.analytics_events.insert_many(saved_step_events)', source)
        self.assertIn('await db.saved_itineraries.update_one(', source)
        self.assertIn('"source_itinerary_id": payload.source_itinerary_id', source)
        self.assertIn('"locked_slots": safe_locked_slots', source)
        self.assertIn('"steps": safe_steps', source)
        self.assertIn('"delivery_channel": "email"', source)
        self.assertIn('"provider_message_id": delivery["provider_message_id"]', source)
        self.assertIn('"saved_itinerary_business"', source)

    def test_audience_contact_upsert_tracks_repeat_saves_and_opt_in(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_upsert_audience_contact"))
        self.assertIn('"email_normalized": email_normalized', source)
        self.assertIn('"visitor_id": visitor_id or existing.get("visitor_id", "")', source)
        self.assertIn('"marketing_opt_in": next_marketing_opt_in', source)
        self.assertIn('"marketing_opt_in_at": marketing_opt_in_at', source)
        self.assertIn('"saved_itinerary_count": int(existing.get("saved_itinerary_count", 0)) + 1', source)
        self.assertIn('"first_saved_itinerary_id": saved_itinerary_id', source)
        self.assertIn('"last_saved_itinerary_id": saved_itinerary_id', source)
        self.assertIn('"source": "save_tonights_move"', source)

    def test_admin_audience_endpoint_requires_admin_and_returns_totals_rows(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_audience"))
        self.assertIn("user=Depends(require_admin)", source)
        self.assertIn('"total_contacts"', source)
        self.assertIn('"total_anonymous_visitors"', source)
        self.assertIn('"new_visitors"', source)
        self.assertIn('"returning_visitors"', source)
        self.assertIn('"returning_visitor_rate"', source)
        self.assertIn('"marketing_opted_in_contacts"', source)
        self.assertIn('"non_marketing_contacts"', source)
        self.assertIn('"total_saved_itineraries"', source)
        self.assertIn('"repeat_savers"', source)
        self.assertIn('"repeat_saver_rate"', source)
        self.assertIn('"recent_captures"', source)
        self.assertIn('"visitor_status"', source)
        self.assertIn('"rows"', source)

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

    def test_email_template_uses_premium_branding_and_buttons(self):
        text_body, html_body = EMAIL_CONTENT({
            "city_slug": "nashville",
            "vibe": "send-it",
            "steps": [
                {
                    "number": 1,
                    "slot": "dinner",
                    "label": "Dinner",
                    "business": {"name": "Pelato", "address": "123 Main", "website": "https://pelato.example"},
                },
                {
                    "number": 3,
                    "slot": "entertainment",
                    "label": "Entertainment",
                    "business": {"name": "The Basement East", "address": "917 Woodland St"},
                    "event": {"title": "Indie Show", "local_time": "20:00:00", "ticket_url": "https://tickets.example"},
                },
            ],
        })
        visible_html = unescape(html_body)
        self.assertEqual(EMAIL_SUBJECT({"city_slug": "nashville"}), "Your Tonight’s Move is locked in")
        self.assertEqual(EMAIL_PREHEADER({"city_slug": "nashville"}), "Nashville is set. Here’s your locked-in move.")
        self.assertIn("YND", visible_html)
        self.assertIn("EST. 26", visible_html)
        self.assertIn("You’re Locked In", visible_html)
        self.assertIn("🚀 No Regrets", visible_html)
        self.assertNotIn(">send-it<", visible_html)
        self.assertIn("01 DINNER", visible_html)
        self.assertIn("03 LIVE MUSIC", visible_html)
        self.assertIn("View Venue", visible_html)
        self.assertIn("Get Directions", visible_html)
        self.assertIn("Buy Tickets", visible_html)
        self.assertIn("Built with YourNotDown", visible_html)
        self.assertIn("Pelato", text_body)
        self.assertIn("Indie Show", text_body)
        self.assertIn("Vibe: 🚀 No Regrets", text_body)
        self.assertIn("View Venue: https://pelato.example", text_body)
        self.assertIn("Buy Tickets: https://tickets.example", text_body)

    def test_event_time_formats_to_friendly_time(self):
        self.assertEqual(FRIENDLY_TIME("19:00:00"), "7:00 PM")
        self.assertEqual(FRIENDLY_TIME("2026-07-06T19:00:00"), "Jul 6, 7:00 PM")

    def test_email_html_escapes_business_and_event_names(self):
        _, html_body = EMAIL_CONTENT({
            "city_slug": "nashville",
            "vibe": "down",
            "steps": [
                {
                    "number": 2,
                    "slot": "drinks",
                    "business": {
                        "name": '<script>alert("x")</script> & Lounge',
                        "address": '123 <Main> & "Broadway"',
                    },
                    "event": {"title": 'Rock & Roll <Bash>'},
                },
            ],
        })
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; Lounge", html_body)
        self.assertIn("123 &lt;Main&gt; &amp; &quot;Broadway&quot;", html_body)
        self.assertIn("Rock &amp; Roll &lt;Bash&gt;", html_body)
        self.assertNotIn("<script>alert", html_body)

    def test_plain_text_email_is_generated_cleanly(self):
        text_body, _ = EMAIL_CONTENT({
            "city_slug": "nashville",
            "vibe": "very-down",
            "steps": [
                {
                    "number": 4,
                    "slot": "late-night",
                    "business": {
                        "name": "Schulman's",
                        "address": "1201 Porter Rd",
                        "website": "https://schulmans.example",
                    },
                },
            ],
        })
        self.assertIn("YOURNOTDOWN", text_body)
        self.assertIn("Tonight's Move", text_body)
        self.assertIn("City: Nashville", text_body)
        self.assertIn("Vibe: 🔥 Let's Make It Count", text_body)
        self.assertIn("04 LATE NIGHT", text_body)
        self.assertIn("Schulman's", text_body)
        self.assertIn("1201 Porter Rd", text_body)
        self.assertIn("View Venue: https://schulmans.example", text_body)
        self.assertNotIn("{", text_body)

    def test_sent_status_when_mocked_resend_succeeds(self):
        payloads = []

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
            def fake_post(*args, **kwargs):
                payloads.append(kwargs["json"])
                return FakeResponse()

            requests_module.post = fake_post
            result = SEND_RESEND_EMAIL({
                "email": "traveler@example.com",
                "city_slug": "nashville",
                "vibe": "down",
                "steps": [
                    {
                        "number": 1,
                        "slot": "dinner",
                        "business": {"name": "Pelato", "address": "123 Main", "website": "https://pelato.example"},
                    },
                ],
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
        self.assertEqual(payloads[0]["subject"], "Your Tonight’s Move is locked in")
        self.assertIn("YND", payloads[0]["html"])
        self.assertIn("EST. 26", payloads[0]["html"])
        self.assertIn("You’re Locked In", payloads[0]["html"])
        self.assertIn("Pelato", payloads[0]["text"])

    def test_failed_status_when_mocked_resend_fails(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('except requests.RequestException as exc:', source)
        self.assertIn('"delivery_status": "failed"', source)
        self.assertIn('"email_provider": "resend"', source)


if __name__ == "__main__":
    unittest.main()
