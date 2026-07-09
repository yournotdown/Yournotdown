"""Dependency-free source contracts for public contact inquiries and legal launch pages."""
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


class TestContactInquiriesContract(unittest.TestCase):
    def test_startup_maintenance_creates_contact_inquiry_indexes(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_apply_startup_maintenance"))
        self.assertIn('await db.contact_inquiries.create_index([("created_at", -1)])', source)
        self.assertIn('await db.contact_inquiries.create_index([("status", 1), ("created_at", -1)])', source)
        self.assertIn('await db.contact_inquiries.create_index([("inquiry_type", 1), ("created_at", -1)])', source)
        self.assertIn('await db.contact_inquiries.create_index([("email", 1)])', source)

    def test_public_contact_inquiry_endpoint_validates_and_rate_limits(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("create_contact_inquiry"))
        self.assertIn('_require_ip_rate_limit(', source)
        self.assertIn('"contact_inquiry_ip"', source)
        self.assertIn('limit=RATE_LIMIT_CONTACT_INQUIRIES_PER_IP', source)
        self.assertIn('_require_rate_limit_key(', source)
        self.assertIn('"contact_inquiry_email"', source)
        self.assertIn('limit=RATE_LIMIT_CONTACT_INQUIRIES_PER_EMAIL', source)
        self.assertIn('if _trimmed_limited(payload.website, 200):', source)
        self.assertIn('"message": "Got it. We’ll review your inquiry and get back to you if it’s a fit."', source)
        self.assertIn('raise HTTPException(status_code=400, detail="Enter your name.")', source)
        self.assertIn('raise HTTPException(status_code=400, detail="Enter a valid email.")', source)
        self.assertIn('raise HTTPException(status_code=400, detail="Select an inquiry type.")', source)
        self.assertIn('raise HTTPException(status_code=400, detail="Enter a message.")', source)
        self.assertIn('"status": "new"', source)
        self.assertIn('"source": "public_contact_page"', source)
        self.assertIn('"ip_hash": _hash_token(_client_ip(request)) if _client_ip(request) else ""', source)
        self.assertIn('await db.contact_inquiries.insert_one(doc)', source)

    def test_contact_notification_is_optional_and_failure_safe(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("create_contact_inquiry"))
        helper_source = ast.get_source_segment(SERVER_SOURCE, named_function("_contact_notification_result"))
        self.assertIn('os.environ.get("CONTACT_NOTIFY_EMAIL", "").strip()', helper_source)
        self.assertIn('"notification_status": "not_configured"', helper_source)
        self.assertIn('if notification["notification_status"] != "not_configured":', source)
        self.assertIn('logger.warning(', source)
        self.assertIn('"contact inquiry notification failed: inquiry_type=%s email_hash=%s error_type=%s"', source)
        self.assertNotIn('doc["message"]', source)

    def test_admin_contact_inquiries_require_admin_and_allow_status_updates(self):
        list_source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_contact_inquiries"))
        update_source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_update_contact_inquiry"))
        self.assertIn("user=Depends(require_admin)", list_source)
        self.assertIn("user=Depends(require_admin)", update_source)
        self.assertIn('if status not in VALID_CONTACT_INQUIRY_STATUSES:', list_source)
        self.assertIn('await db.contact_inquiries.find(query, {"_id": 0}).sort([("created_at", -1)]).limit(200).to_list(200)', list_source)
        self.assertIn('if status not in VALID_CONTACT_INQUIRY_STATUSES:', update_source)
        self.assertIn('{"$set": {"status": status, "updated_at": now_iso()}}', update_source)
        self.assertIn('raise HTTPException(status_code=404, detail="Contact inquiry not found")', update_source)


if __name__ == "__main__":
    unittest.main()
