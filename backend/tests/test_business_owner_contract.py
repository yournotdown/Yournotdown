"""Dependency-free source contracts for business-owner invite and session scaffolding."""
import ast
import os
import unittest
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()
SERVER_TREE = ast.parse(SERVER_SOURCE)
EMAIL_PATH = Path(__file__).resolve().parents[1] / "business_owner_email.py"
EMAIL_SOURCE = EMAIL_PATH.read_text()
EMAIL_TREE = ast.parse(EMAIL_SOURCE)


def named_function(name: str):
    return next(
        node
        for node in SERVER_TREE.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def email_named_function(name: str):
    return next(
        node
        for node in EMAIL_TREE.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def load_owner_helpers():
    namespace = {
        "hashlib": __import__("hashlib"),
        "secrets": __import__("secrets"),
        "os": os,
    }
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_hash_token")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_new_owner_token")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_business_owner_claim_url")), namespace)
    exec(ast.get_source_segment(SERVER_SOURCE, named_function("_owner_invite_delivery_result")), namespace)

    email_namespace = {
        "html": __import__("html"),
        "datetime": __import__("datetime").datetime,
    }
    assign = next(
        node for node in EMAIL_TREE.body
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "EMAIL_SUBJECT" for target in node.targets)
    )
    exec(ast.get_source_segment(EMAIL_SOURCE, assign), email_namespace)
    login_assign = next(
        node for node in EMAIL_TREE.body
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "LOGIN_EMAIL_SUBJECT" for target in node.targets)
    )
    exec(ast.get_source_segment(EMAIL_SOURCE, login_assign), email_namespace)
    for fn_name in (
        "_escape",
        "_friendly_expiration",
        "business_owner_invite_email_subject",
        "business_owner_invite_email_content",
        "business_owner_login_email_subject",
        "business_owner_login_email_content",
    ):
        exec(ast.get_source_segment(EMAIL_SOURCE, email_named_function(fn_name)), email_namespace)
    return (
        namespace["_hash_token"],
        namespace["_new_owner_token"],
        namespace["_business_owner_claim_url"],
        namespace["_owner_invite_delivery_result"],
        email_namespace["business_owner_invite_email_subject"],
        email_namespace["business_owner_invite_email_content"],
        email_namespace["business_owner_login_email_subject"],
        email_namespace["business_owner_login_email_content"],
    )


(
    HASH_TOKEN,
    NEW_OWNER_TOKEN,
    BUSINESS_OWNER_CLAIM_URL,
    OWNER_INVITE_DELIVERY_RESULT,
    OWNER_INVITE_EMAIL_SUBJECT,
    OWNER_INVITE_EMAIL_CONTENT,
    OWNER_LOGIN_EMAIL_SUBJECT,
    OWNER_LOGIN_EMAIL_CONTENT,
) = load_owner_helpers()


class TestBusinessOwnerContract(unittest.TestCase):
    def test_admin_session_endpoint_stores_hash_not_raw_token(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("auth_session"))
        self.assertIn('"session_token_hash": _hash_token(session_token)', source)
        self.assertNotIn('"session_token": session_token', source)
        self.assertIn('key=ADMIN_SESSION_COOKIE', source)
        self.assertIn('httponly=True', source)
        self.assertIn('secure=True', source)
        self.assertIn('samesite="none"', source)
        self.assertIn('return {"user": user}', source)

    def test_admin_auth_supports_hashed_sessions_with_legacy_fallback(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("get_current_user"))
        self.assertIn('token_hash = _hash_token(token)', source)
        self.assertIn('await db.user_sessions.find_one({"session_token_hash": token_hash}', source)
        self.assertIn('legacy_sess = await db.user_sessions.find_one({"session_token": token}', source)
        self.assertIn('"session_token_hash": token_hash', source)
        self.assertIn('"session_token": ""', source)
        self.assertIn('HTTPException(status_code=401, detail="Invalid session")', source)
        self.assertIn('HTTPException(status_code=401, detail="Session expired")', source)

    def test_admin_logout_revokes_hashed_and_legacy_raw_sessions(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("logout"))
        self.assertIn('{"session_token_hash": _hash_token(session_token)}', source)
        self.assertIn('{"session_token": session_token}', source)
        self.assertIn('response.delete_cookie(ADMIN_SESSION_COOKIE, path="/", secure=True, samesite="none")', source)

    def test_invite_endpoint_stores_token_hash_not_raw_token(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_business_owner_invite"))
        self.assertIn('"token_hash": _hash_token(raw_token)', source)
        self.assertNotIn('"token": raw_token', source)
        self.assertIn('timedelta(days=BUSINESS_OWNER_INVITE_DAYS)', source)
        self.assertIn('await db.business_owner_invites.insert_one(doc)', source)

    def test_claim_endpoint_hashes_token_and_sets_cookie(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("business_claim"))
        self.assertIn('_require_ip_rate_limit(', source)
        self.assertIn('"business_claim_ip"', source)
        self.assertIn("RATE_LIMIT_BUSINESS_CLAIM_PER_IP", source)
        self.assertIn('{"token_hash": _hash_token(raw_token)}', source)
        self.assertIn("await _create_business_owner_session(owner_doc, response, request)", source)
        self.assertIn('"status": "accepted"', source)

    def test_claim_endpoint_reuses_invite_exactly_once(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("business_claim"))
        self.assertIn('if invite.get("status") == "accepted":', source)
        self.assertIn('raise HTTPException(status_code=400, detail="This invite has already been used.")', source)
        self.assertIn('if invite.get("status") != "pending":', source)

    def test_owner_auth_and_me_endpoints_are_business_scoped(self):
        admin_source = ast.get_source_segment(SERVER_SOURCE, named_function("get_current_user"))
        auth_source = ast.get_source_segment(SERVER_SOURCE, named_function("get_current_business_owner"))
        self.assertIn('session_token: Optional[str] = Cookie(None)', admin_source)
        self.assertIn('ADMIN_SESSION_COOKIE = "session_token"', SERVER_SOURCE)
        self.assertIn('business_owner_session: Optional[str] = Cookie(None)', auth_source)
        self.assertIn('BUSINESS_OWNER_SESSION_COOKIE = "business_owner_session"', SERVER_SOURCE)
        self.assertIn('raise HTTPException(status_code=401, detail="Not authenticated")', auth_source)
        self.assertIn('await db.business_owner_sessions.find_one({"session_token_hash": token_hash}', auth_source)
        self.assertIn('await db.businesses.find_one({"id": owner["business_id"]}', auth_source)
        me_source = ast.get_source_segment(SERVER_SOURCE, named_function("business_me"))
        self.assertIn("Depends(get_current_business_owner)", me_source)
        self.assertIn('_owner_safe(owner_ctx["owner"], owner_ctx["business"])', me_source)
        self.assertNotIn("db.user_sessions", auth_source)

    def test_business_owner_claim_and_session_storage_remain_separate_from_admin(self):
        claim_source = ast.get_source_segment(SERVER_SOURCE, named_function("business_claim"))
        session_source = ast.get_source_segment(SERVER_SOURCE, named_function("_create_business_owner_session"))
        self.assertIn('"session_token_hash": _hash_token(session_token)', session_source)
        self.assertIn('await db.business_owner_sessions.insert_one(session_doc)', session_source)
        self.assertIn('key=BUSINESS_OWNER_SESSION_COOKIE', session_source)
        self.assertIn("await _create_business_owner_session(owner_doc, response, request)", claim_source)
        self.assertNotIn('db.user_sessions.insert_one', claim_source)

    def test_login_request_endpoint_is_generic_and_hashes_token(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("business_login_request"))
        self.assertIn('_require_ip_rate_limit(', source)
        self.assertIn('"business_login_request_ip"', source)
        self.assertIn('_require_rate_limit_key(', source)
        self.assertIn('"business_login_request_email"', source)
        self.assertIn('"message": "If your email has access, we’ll send a secure login link."', source)
        self.assertIn('await db.business_owners.find_one({"email": email, "status": "active"}', source)
        self.assertIn('"token_hash": _hash_token(raw_token)', source)
        self.assertNotIn('"token": raw_token', source)
        self.assertIn('await db.business_owner_login_links.insert_one(doc)', source)

    def test_login_claim_endpoint_rejects_reuse_and_sets_owner_cookie(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("business_login_claim"))
        self.assertIn('_require_ip_rate_limit(', source)
        self.assertIn('"business_login_claim_ip"', source)
        self.assertIn('await db.business_owner_login_links.find_one({"token_hash": _hash_token(raw_token)}', source)
        self.assertIn('if login_link.get("status") == "used":', source)
        self.assertIn('raise HTTPException(status_code=400, detail="This login link has already been used.")', source)
        self.assertIn('raise HTTPException(status_code=400, detail="This login link has expired.")', source)
        self.assertIn('"status": "used"', source)
        self.assertIn('await _create_business_owner_session(owner, response, request)', source)

    def test_owner_access_summary_only_returns_pending_invites_and_active_owner(self):
        summary_source = ast.get_source_segment(SERVER_SOURCE, named_function("_owner_access_summary"))
        self.assertIn('{"business_id": business_id, "status": "pending"}', summary_source)
        self.assertIn('{"business_id": business_id, "status": "active"}', summary_source)

    def test_revoke_endpoint_revokes_pending_invites_active_owner_and_sessions(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_revoke_business_owner_access"))
        self.assertIn('{"business_id": business_id, "status": "pending"}', source)
        self.assertIn('{"business_id": business_id, "status": "active"}', source)
        self.assertIn('await db.business_owner_login_links.update_many(', source)
        self.assertIn('{"business_id": business_id, "revoked_at": None}', source)
        self.assertIn('"status": "revoked"', source)
        self.assertIn('"revoked_at": revoked_at', source)

    def test_revoke_endpoint_is_idempotent(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_revoke_business_owner_access"))
        self.assertIn("update_many", source)
        self.assertNotIn("raise HTTPException(status_code=409", source)

    def test_fresh_invite_can_be_sent_again_after_revoke(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_business_owner_invite"))
        self.assertIn('_require_rate_limit_key(', source)
        self.assertIn('"admin_owner_invite_user"', source)
        self.assertIn("RATE_LIMIT_OWNER_INVITE_PER_ADMIN", source)
        self.assertIn('_require_ip_rate_limit(', source)
        self.assertIn('"admin_owner_invite_ip"', source)
        self.assertIn("RATE_LIMIT_OWNER_INVITE_PER_IP", source)
        self.assertIn('"owner invite email failed: business_id=%s delivery_status=%s email_hash=%s error_type=%s"', source)
        self.assertIn('_hash_token(email)[:12]', source)
        self.assertIn('{"business_id": business_id, "email": email, "status": "pending"}', source)
        self.assertIn('await db.business_owner_invites.insert_one(doc)', source)

    def test_provider_unconfigured_when_resend_env_missing(self):
        previous = {
            "RESEND_API_KEY": os.environ.get("RESEND_API_KEY"),
            "RESEND_FROM_EMAIL": os.environ.get("RESEND_FROM_EMAIL"),
        }
        try:
            os.environ.pop("RESEND_API_KEY", None)
            os.environ.pop("RESEND_FROM_EMAIL", None)
            result = OWNER_INVITE_DELIVERY_RESULT()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(result["delivery_status"], "provider_unconfigured")
        self.assertEqual(result["email_provider"], "")

    def test_token_and_claim_url_helpers(self):
        token = NEW_OWNER_TOKEN()
        self.assertTrue(token)
        self.assertEqual(HASH_TOKEN("abc"), HASH_TOKEN("abc"))
        self.assertNotEqual(HASH_TOKEN("abc"), HASH_TOKEN("xyz"))
        url = BUSINESS_OWNER_CLAIM_URL("raw-token")
        self.assertIn("/business/claim/raw-token", url)
        login_url = ast.get_source_segment(SERVER_SOURCE, named_function("_business_owner_login_url"))
        self.assertIn('/business/login?token={token}', login_url)

    def test_owner_invite_email_template_is_branded(self):
        self.assertEqual(OWNER_INVITE_EMAIL_SUBJECT({}), "Create your YourNotDown business account")
        text_body, html_body = OWNER_INVITE_EMAIL_CONTENT({
            "business_name": "The Patterson House",
            "claim_url": "https://www.yournotdown.com/business/claim/test-token",
            "expires_at": "2026-07-13T17:00:00+00:00",
        })
        self.assertIn("YND", html_body)
        self.assertIn("Create Account", html_body)
        self.assertIn("The Patterson House", html_body)
        self.assertIn("Jul", text_body)
        self.assertIn("Built with YourNotDown", html_body)
        self.assertIn("https://www.yournotdown.com/business/claim/test-token", text_body)
        self.assertNotIn("MVP", html_body)
        self.assertIn("No password required.", html_body)

    def test_owner_login_email_template_is_branded(self):
        self.assertEqual(OWNER_LOGIN_EMAIL_SUBJECT({}), "Your YourNotDown business dashboard login")
        text_body, html_body = OWNER_LOGIN_EMAIL_CONTENT({
            "business_name": "The Patterson House",
            "login_url": "https://www.yournotdown.com/business/login?token=test-token",
            "expires_at": "2026-07-13T17:00:00+00:00",
        })
        self.assertIn("YND", html_body)
        self.assertIn("Open Dashboard", html_body)
        self.assertIn("The Patterson House", html_body)
        self.assertIn("Jul", text_body)
        self.assertIn("Built with YourNotDown", html_body)
        self.assertIn("https://www.yournotdown.com/business/login?token=test-token", text_body)
        self.assertNotIn("MVP", html_body)
        self.assertIn("No password required.", html_body)

    def test_owner_business_facing_sources_do_not_use_internal_product_language(self):
        frontend_root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages"
        claim_source = (frontend_root / "BusinessClaimPage.jsx").read_text()
        dashboard_source = (frontend_root / "BusinessDashboardPage.jsx").read_text()
        login_source = (frontend_root / "BusinessLoginPage.jsx").read_text()
        for source in (EMAIL_SOURCE, claim_source, dashboard_source, login_source):
            self.assertNotIn("MVP", source)
            self.assertNotIn("prototype", source)
            self.assertNotIn("placeholder", source)
            self.assertNotIn("being prepared", source)
            self.assertNotIn("not ready", source)

    def test_owner_cors_uses_explicit_allowed_origins(self):
        self.assertIn("def _cors_allowed_origins()", SERVER_SOURCE)
        self.assertIn('allow_origins=_cors_allowed_origins()', SERVER_SOURCE)
        self.assertNotIn('allow_origin_regex=".*"', SERVER_SOURCE)


if __name__ == "__main__":
    unittest.main()
