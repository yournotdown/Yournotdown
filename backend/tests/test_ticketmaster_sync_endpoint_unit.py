"""Dependency-free contract tests for the protected Ticketmaster sync endpoint."""
import ast
import unittest
from pathlib import Path

SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)


def endpoint_function() -> ast.AsyncFunctionDef:
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "admin_ticketmaster_sync"
    )


def named_function(name: str) -> ast.AsyncFunctionDef:
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )


def named_class(name: str) -> ast.ClassDef:
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


class TestTicketmasterSyncEndpoint(unittest.TestCase):
    def test_admin_auth_is_required(self):
        node = endpoint_function()
        self.assertIn('@api_router.post("/admin/events/ticketmaster-sync")', SERVER_SOURCE)
        user_arg = next(arg for arg in node.args.args if arg.arg == "user")
        user_default = node.args.defaults[node.args.args.index(user_arg) - 1]
        self.assertEqual(ast.unparse(user_default), "Depends(require_admin)")

    def test_unauthenticated_requests_are_rejected_with_401(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("get_current_user"))
        self.assertIn('if not token:', source)
        self.assertIn('HTTPException(status_code=401, detail="Not authenticated")', source)

    def test_authenticated_non_admin_requests_are_rejected_with_403(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("require_admin"))
        self.assertIn('if user.get("role") != "admin":', source)
        self.assertIn('HTTPException(status_code=403, detail="Admin access required")', source)

    def test_apply_confirmation_is_validated_before_fetch_or_writes(self):
        source = ast.get_source_segment(SERVER_SOURCE, endpoint_function())
        validation = "validate_apply_confirmation(payload.apply, payload.confirm)"
        self.assertIn(validation, source)
        self.assertLess(source.index(validation), source.index("db.businesses.find"))
        self.assertLess(source.index(validation), source.index("date_range_sync_report"))
        self.assertLess(source.index(validation), source.index("db.city_events.update_one"))
        self.assertLess(source.index(validation), source.index("db.city_events.delete_many"))
        self.assertIn("HTTPException(status_code=400, detail=str(exc))", source)

    def test_city_is_validated_before_db_api_or_mutation_work(self):
        source = ast.get_source_segment(SERVER_SOURCE, endpoint_function())
        validation = "supported_city_config(payload.city)"
        self.assertIn(validation, source)
        self.assertLess(source.index(validation), source.index("db.businesses.find"))
        self.assertLess(source.index(validation), source.index("TicketmasterClient()"))
        self.assertLess(source.index(validation), source.index("date_range_sync_report"))
        self.assertLess(source.index(validation), source.index("db.city_events.update_one"))
        self.assertLess(source.index(validation), source.index("db.city_events.delete_many"))

    def test_dry_run_returns_before_any_event_write(self):
        source = ast.get_source_segment(SERVER_SOURCE, endpoint_function())
        self.assertLess(source.index("if not payload.apply:"), source.index("db.city_events.update_one"))
        self.assertLess(source.index("return api_sync_response(report)"), source.index("db.city_events.update_one"))

    def test_apply_uses_safe_write_path(self):
        source = ast.get_source_segment(SERVER_SOURCE, endpoint_function())
        self.assertIn("selector, update = event_upsert(document)", source)
        self.assertIn("db.city_events.update_one(selector, update, upsert=True)", source)
        self.assertIn("cleanup_query = expiration_cleanup_query(payload.city)", source)
        self.assertIn("db.city_events.delete_many(cleanup_query)", source)

    def test_payload_schema_has_bounded_days_and_expected_defaults(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_class("TicketmasterSyncPayload"))
        self.assertIn('city: str = "nashville"', source)
        self.assertIn("days: int = Field(default=2, ge=1, le=7)", source)
        self.assertIn("apply: bool = False", source)
        self.assertIn('confirm: str = ""', source)

    def test_response_formats_include_required_fields(self):
        source = ast.get_source_segment(SERVER_SOURCE, endpoint_function())
        self.assertIn("return api_sync_response(report)", source)
        self.assertIn("return api_sync_response(report, {", source)

    def test_endpoint_source_does_not_reference_sensitive_credentials(self):
        source = ast.get_source_segment(SERVER_SOURCE, endpoint_function())
        self.assertNotIn("TICKETMASTER_API_KEY", source)
        self.assertNotIn("MONGO_URL", source)
        self.assertNotIn("DB_NAME", source)


if __name__ == "__main__":
    unittest.main()
