"""Unit tests for the Railway-safe Ticketmaster sync job."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from ticketmaster_sync_job import print_summary, redact_secret_text  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
