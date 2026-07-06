"""Unit tests for the Railway-safe Ticketmaster sync job."""
import contextlib
import io
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from ticketmaster_events import TicketmasterRateLimitError  # noqa: E402
from ticketmaster_sync_job import main, print_summary, redact_secret_text  # noqa: E402


class FakeDatabase:
    def __init__(self):
        self.businesses = object()
        self.city_events = object()


class FakeMongoClient:
    def __init__(self):
        self.closed = False
        self.database = FakeDatabase()

    def __getitem__(self, name):
        return self.database

    def close(self):
        self.closed = True


class TestTicketmasterSyncJob(unittest.TestCase):
    def test_redacts_known_secret_values_and_apikey_query_params(self):
        message = (
            "HTTPError: https://example.com/events?apikey=backend-secret&city=Nashville "
            "mongo=mongodb+srv://user:pass@cluster"
        )
        result = redact_secret_text(
            message,
            ["backend-secret", "mongodb+srv://user:pass@cluster"],
        )
        self.assertNotIn("backend-secret", result)
        self.assertNotIn("mongodb+srv://user:pass@cluster", result)
        self.assertIn("apikey=[REDACTED]", result)
        self.assertIn("mongo=[REDACTED]", result)

    def test_print_summary_renders_apply_counts_without_errors(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            print_summary(
                {
                    "dates": ["2026-07-04", "2026-07-05"],
                    "fetched": 13,
                    "after_dedupe": 12,
                    "matched": 5,
                    "unmatched": 7,
                },
                apply_summary={"upserted": 12, "expired_deleted": 3},
                mode="apply",
            )
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            stdout.getvalue().strip().splitlines(),
            [
                "status=ok",
                "mode=apply",
                "dates=2026-07-04,2026-07-05",
                "fetched=13",
                "after_dedupe=12",
                "matched=5",
                "unmatched=7",
                "upserted=12",
                "deleted_expired=3",
                "errors=0",
            ],
        )

    def test_print_summary_emits_error_lines_to_stderr(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            print_summary({"dates": []}, mode="dry-run", errors=["RuntimeError: boom"])
        self.assertIn("status=error", stdout.getvalue())
        self.assertIn("errors=1", stdout.getvalue())
        self.assertEqual(stderr.getvalue().strip(), "error=RuntimeError: boom")

    def test_print_summary_supports_rate_limited_status_and_retry_after(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            print_summary(
                {"dates": []},
                mode="apply",
                status="rate_limited",
                extra_fields={"retry_after": "60"},
            )
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("status=rate_limited", stdout.getvalue())
        self.assertIn("retry_after=60", stdout.getvalue())
        self.assertIn("deleted_expired=0", stdout.getvalue())
        self.assertIn("errors=0", stdout.getvalue())

    def test_main_returns_zero_and_never_deletes_on_rate_limit(self):
        fake_client = FakeMongoClient()
        with patch.dict(os.environ, {
            "MONGO_URL": "mongodb+srv://user:pass@cluster",
            "DB_NAME": "ynd",
            "TICKETMASTER_API_KEY": "backend-secret",
        }, clear=False), \
                patch("ticketmaster_sync_job.parse_args", return_value=type("Args", (), {
                    "city": "nashville",
                    "days": 2,
                    "start_date": None,
                    "dry_run": False,
                })()), \
                patch("ticketmaster_sync_job.open_mongo_client", return_value=fake_client), \
                patch("ticketmaster_sync_job.load_approved_businesses", return_value=[]), \
                patch("ticketmaster_sync_job.date_range_sync_report", side_effect=TicketmasterRateLimitError("120")), \
                patch("ticketmaster_sync_job.apply_event_sync") as apply_sync:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main()
        self.assertEqual(code, 0)
        self.assertTrue(fake_client.closed)
        apply_sync.assert_not_called()
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("status=rate_limited", stdout.getvalue())
        self.assertIn("retry_after=120", stdout.getvalue())
        self.assertIn("deleted_expired=0", stdout.getvalue())
        self.assertNotIn("backend-secret", stdout.getvalue())

    def test_main_successfully_applies_and_exits_zero(self):
        fake_client = FakeMongoClient()
        report = {
            "dates": ["2026-07-05", "2026-07-06"],
            "fetched": 16,
            "after_dedupe": 16,
            "matched": 8,
            "unmatched": 8,
        }
        apply_summary = {"upserted": 9, "expired_deleted": 5}
        with patch.dict(os.environ, {
            "MONGO_URL": "mongodb+srv://user:pass@cluster",
            "DB_NAME": "ynd",
            "TICKETMASTER_API_KEY": "backend-secret",
        }, clear=False), \
                patch("ticketmaster_sync_job.parse_args", return_value=type("Args", (), {
                    "city": "nashville",
                    "days": 2,
                    "start_date": None,
                    "dry_run": False,
                })()), \
                patch("ticketmaster_sync_job.open_mongo_client", return_value=fake_client), \
                patch("ticketmaster_sync_job.load_approved_businesses", return_value=[]), \
                patch("ticketmaster_sync_job.date_range_sync_report", return_value=report), \
                patch("ticketmaster_sync_job.apply_event_sync", return_value=apply_summary) as apply_sync:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main()
        self.assertEqual(code, 0)
        self.assertTrue(fake_client.closed)
        apply_sync.assert_called_once_with(fake_client.database.city_events, report, "nashville")
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("status=ok", stdout.getvalue())
        self.assertIn("upserted=9", stdout.getvalue())

    def test_main_redacts_secrets_for_non_rate_limit_errors(self):
        fake_client = FakeMongoClient()
        with patch.dict(os.environ, {
            "MONGO_URL": "mongodb+srv://user:pass@cluster",
            "DB_NAME": "ynd",
            "TICKETMASTER_API_KEY": "backend-secret",
        }, clear=False), \
                patch("ticketmaster_sync_job.parse_args", return_value=type("Args", (), {
                    "city": "nashville",
                    "days": 2,
                    "start_date": None,
                    "dry_run": False,
                })()), \
                patch("ticketmaster_sync_job.open_mongo_client", return_value=fake_client), \
                patch("ticketmaster_sync_job.load_approved_businesses", return_value=[]), \
                patch(
                    "ticketmaster_sync_job.date_range_sync_report",
                    side_effect=RuntimeError("boom https://example.com?apikey=backend-secret"),
                ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main()
        self.assertEqual(code, 1)
        self.assertNotIn("backend-secret", stdout.getvalue())
        self.assertNotIn("backend-secret", stderr.getvalue())
        self.assertIn("apikey=[REDACTED]", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
