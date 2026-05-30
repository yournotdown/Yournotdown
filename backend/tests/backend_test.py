"""Backend tests for You're Not Down — Nashville discovery app."""
import os
import io
import base64
import pytest
import requests
from test_config import BASE_URL, API, ADMIN_TOKEN, USER_TOKEN  # noqa: F401

EXPECTED_CATEGORIES = {"drinks", "date-night", "live-music", "night-out", "family-fun", "surprise-me"}
EXPECTED_CATEGORY_ORDER = ["drinks", "date-night", "live-music", "night-out", "family-fun", "surprise-me"]
EXPECTED_CATEGORY_META = {
    "drinks": ("Drinks & Conversation", "🍸"),
    "date-night": ("Date Night", "❤️"),
    "live-music": ("Live Music", "🎵"),
    "night-out": ("Night Out", "🌃"),
    "family-fun": ("Family Time", "👨\u200d👩\u200d👧"),
    "surprise-me": ("Surprise Me", "🎲"),
}
REMOVED_CATEGORIES = ["food", "sports", "rooftops", "events"]


@pytest.fixture(scope="session")
def admin_headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture(scope="session")
def user_headers():
    return {"Authorization": f"Bearer {USER_TOKEN}"}


# ---------------- Health ----------------
class TestHealth:
    def test_health(self):
        r = requests.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


# ---------------- Cities ----------------
class TestCities:
    def test_list_cities(self):
        r = requests.get(f"{API}/cities", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 1
        nashville = next((c for c in data if c["slug"] == "nashville"), None)
        assert nashville is not None
        assert nashville["default"]

    def test_default_city(self):
        r = requests.get(f"{API}/cities/default", timeout=10)
        assert r.status_code == 200
        assert r.json()["slug"] == "nashville"


# ---------------- Categories ----------------
class TestCategories:
    def test_list_categories(self):
        r = requests.get(f"{API}/categories", timeout=10)
        assert r.status_code == 200
        cats = r.json()
        slugs = {c["slug"] for c in cats}
        assert slugs == EXPECTED_CATEGORIES
        for c in cats:
            assert c.get("emoji"), f"Missing emoji for {c['slug']}"

    def test_categories_ordered_and_named(self):
        r = requests.get(f"{API}/categories", timeout=10)
        cats = r.json()
        assert len(cats) == 6
        actual_order = [c["slug"] for c in cats]
        assert actual_order == EXPECTED_CATEGORY_ORDER
        for c in cats:
            expected_name, expected_emoji = EXPECTED_CATEGORY_META[c["slug"]]
            assert c["name"] == expected_name, f"{c['slug']} name {c['name']!r} != {expected_name!r}"
            assert c["emoji"] == expected_emoji, f"{c['slug']} emoji {c['emoji']!r} != {expected_emoji!r}"

    def test_removed_categories_absent(self):
        r = requests.get(f"{API}/categories", timeout=10)
        slugs = {c["slug"] for c in r.json()}
        for s in REMOVED_CATEGORIES:
            assert s not in slugs, f"Removed category {s} still present"


# ---------------- Migration ----------------
class TestCategoryMigration:
    def test_date_night_has_migrated_food(self):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        names = {b["name"] for b in items}
        # Migrated from food + original date-night
        expected = {"Hattie B's Hot Chicken", "Husk Nashville", "The Pharmacy Burger", "Rolf and Daughters",
                    "Catbird Seat", "Rooftop at Bobby", "Henrietta Red"}
        missing = expected - names
        assert not missing, f"date-night missing migrated businesses: {missing}"
        assert len(items) >= 6

    def test_night_out_has_migrated_sports_rooftops_events(self):
        r = requests.get(f"{API}/businesses", params={"category": "night-out"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        names = {b["name"] for b in items}
        expected = {"Nissan Stadium", "Bridgestone Arena", "Geodis Park",
                    "L.A. Jackson", "White Limozeen", "UP Rooftop Lounge",
                    "CMA Fest", "Tomato Art Fest", "Live On The Green"}
        missing = expected - names
        assert not missing, f"night-out missing migrated businesses: {missing}"
        assert len(items) >= 7

    @pytest.mark.parametrize("slug", REMOVED_CATEGORIES)
    def test_removed_categories_return_empty(self, slug):
        r = requests.get(f"{API}/businesses", params={"category": slug}, timeout=10)
        assert r.status_code == 200
        assert r.json() == [], f"{slug} should return empty list"

    def test_all_businesses_preserved(self):
        # Total seeded: 30. None should have been deleted by migration.
        r = requests.get(f"{API}/businesses", params={"limit": 1000}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        # Some TEST_ may exist from prior runs; assert at least 30 original ones still there
        non_test = [b for b in items if not b["name"].startswith("TEST_")]
        assert len(non_test) >= 30, f"Expected >=30 preserved businesses, got {len(non_test)}"

    def test_migration_idempotent_slugs_present(self):
        # After repeated startups, exactly 6 categories should remain, no dupes
        r = requests.get(f"{API}/categories", timeout=10)
        cats = r.json()
        slugs = [c["slug"] for c in cats]
        assert len(slugs) == len(set(slugs)) == 6


# ---------------- Vibe analytics ----------------
class TestVibeAnalytics:
    def test_vibe_click_tracked(self):
        r = requests.post(f"{API}/analytics/track",
                          json={"event_type": "vibe_click"}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok")


# ---------------- Businesses ----------------
class TestBusinesses:
    def test_date_night_category(self):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        b = items[0]
        for f in ("name", "description", "image_url", "website", "phone", "address"):
            assert f in b

    def test_surprise_me(self):
        r = requests.get(f"{API}/businesses", params={"category": "surprise-me"}, timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert len(items) <= 8

    def test_get_single_business(self):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.get(f"{API}/businesses/{bid}", timeout=10)
        assert r2.status_code == 200
        assert r2.json()["id"] == bid

    def test_get_missing_business_404(self):
        r = requests.get(f"{API}/businesses/nonexistent-xyz", timeout=10)
        assert r.status_code == 404


# ---------------- Analytics ----------------
class TestAnalytics:
    @pytest.mark.parametrize("evt", [
        {"event_type": "homepage_visit"},
        {"event_type": "im_down_click"},
        {"event_type": "category_click", "category_slug": "date-night"},
        {"event_type": "phone_click"},
        {"event_type": "directions_click"},
        {"event_type": "website_click"},
    ])
    def test_track_events(self, evt):
        r = requests.post(f"{API}/analytics/track", json=evt, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok")

    def test_business_view_event(self):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.post(f"{API}/analytics/track", json={"event_type": "business_view", "business_id": bid}, timeout=10)
        assert r2.status_code == 200


# ---------------- Auth ----------------
class TestAuth:
    def test_me_without_token_401(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_session_invalid_id_401(self):
        r = requests.post(f"{API}/auth/session", json={"session_id": "invalid_xyz"}, timeout=15)
        assert r.status_code == 401

    def test_me_with_admin_token(self, admin_headers):
        r = requests.get(f"{API}/auth/me", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("role") == "admin"


# ---------------- Admin: businesses CRUD ----------------
class TestAdminBusinesses:
    created_id = None

    def test_non_admin_forbidden(self, user_headers):
        r = requests.get(f"{API}/admin/businesses", headers=user_headers, timeout=10)
        assert r.status_code == 403

    def test_list_admin(self, admin_headers):
        r = requests.get(f"{API}/admin/businesses", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_business(self, admin_headers):
        payload = {"name": "TEST_Biz", "description": "test", "category_slug": "date-night", "city_slug": "nashville"}
        r = requests.post(f"{API}/admin/businesses", headers=admin_headers, json=payload, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_Biz"
        TestAdminBusinesses.created_id = data["id"]

        # Verify persistence via public GET
        r2 = requests.get(f"{API}/businesses/{data['id']}", timeout=10)
        assert r2.status_code == 200

    def test_update_business(self, admin_headers):
        bid = TestAdminBusinesses.created_id
        assert bid
        r = requests.patch(f"{API}/admin/businesses/{bid}", headers=admin_headers,
                           json={"featured": True, "name": "TEST_Biz_Updated"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["featured"]
        assert r.json()["name"] == "TEST_Biz_Updated"

    def test_reorder(self, admin_headers):
        bid = TestAdminBusinesses.created_id
        r = requests.post(f"{API}/admin/businesses/reorder", headers=admin_headers,
                          json={"items": [{"id": bid, "order": 99}]}, timeout=10)
        assert r.status_code == 200
        assert r.json()["count"] == 1

    def test_delete_business(self, admin_headers):
        bid = TestAdminBusinesses.created_id
        r = requests.delete(f"{API}/admin/businesses/{bid}", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/businesses/{bid}", timeout=10)
        assert r2.status_code == 404


# ---------------- Admin: categories & analytics ----------------
class TestAdminMisc:
    def test_admin_categories(self, admin_headers):
        r = requests.get(f"{API}/admin/categories", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert len(r.json()) == 6

    def test_admin_categories_forbidden(self, user_headers):
        r = requests.get(f"{API}/admin/categories", headers=user_headers, timeout=10)
        assert r.status_code == 403

    def test_admin_analytics(self, admin_headers):
        r = requests.get(f"{API}/admin/analytics/summary", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("by_event_type", "by_category", "by_business", "total_events"):
            assert k in data
        # we tracked these earlier
        assert data["by_event_type"].get("homepage_visit", 0) >= 1
        assert data["by_event_type"].get("im_down_click", 0) >= 1


# ---------------- Admin: per-business analytics deep-dive ----------------
class TestAdminBusinessAnalytics:
    def test_requires_admin(self, user_headers):
        # Pick any real business id
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.get(f"{API}/admin/analytics/business/{bid}",
                          headers=user_headers, timeout=10)
        assert r2.status_code == 403

    def test_requires_auth(self):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.get(f"{API}/admin/analytics/business/{bid}", timeout=10)
        assert r2.status_code == 401

    def test_404_when_business_missing(self, admin_headers):
        r = requests.get(f"{API}/admin/analytics/business/nonexistent-xyz",
                         headers=admin_headers, timeout=10)
        assert r.status_code == 404

    def test_default_days_is_30(self, admin_headers):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.get(f"{API}/admin/analytics/business/{bid}",
                         headers=admin_headers, timeout=10)
        assert r2.status_code == 200
        data = r2.json()
        # Shape
        assert "business" in data and data["business"]["id"] == bid
        assert "totals" in data
        for k in ("business_view", "website_click", "phone_click", "directions_click"):
            assert k in data["totals"]
        # timeline length
        assert isinstance(data["timeline"], list)
        assert len(data["timeline"]) == 30
        # Each row has all 4 metrics + day
        for row in data["timeline"]:
            for k in ("day", "business_view", "website_click", "phone_click", "directions_click"):
                assert k in row

    @pytest.mark.parametrize("days", [7, 30, 90])
    def test_range_selector(self, admin_headers, days):
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.get(f"{API}/admin/analytics/business/{bid}",
                         headers=admin_headers, params={"days": days}, timeout=10)
        assert r2.status_code == 200
        assert len(r2.json()["timeline"]) == days

    def test_events_aggregate_into_totals_and_today_row(self, admin_headers):
        # Pick a distinct business (use drinks category to avoid interference with other tests)
        r = requests.get(f"{API}/businesses", params={"category": "drinks"}, timeout=10)
        items = r.json()
        assert items, "Need at least one drinks business"
        bid = items[0]["id"]

        # Snapshot current totals
        before = requests.get(f"{API}/admin/analytics/business/{bid}",
                              headers=admin_headers, timeout=10).json()["totals"]

        # Generate events
        events = [
            {"event_type": "business_view", "business_id": bid},
            {"event_type": "business_view", "business_id": bid},
            {"event_type": "website_click", "business_id": bid},
            {"event_type": "phone_click", "business_id": bid},
            {"event_type": "directions_click", "business_id": bid},
        ]
        for e in events:
            rr = requests.post(f"{API}/analytics/track", json=e, timeout=10)
            assert rr.status_code == 200

        # Re-fetch and verify deltas
        after = requests.get(f"{API}/admin/analytics/business/{bid}",
                             headers=admin_headers, timeout=10).json()
        totals = after["totals"]
        assert totals["business_view"] - before["business_view"] >= 2
        assert totals["website_click"] - before["website_click"] >= 1
        assert totals["phone_click"] - before["phone_click"] >= 1
        assert totals["directions_click"] - before["directions_click"] >= 1

        # Today's row should reflect the events (last entry in timeline)
        today_row = after["timeline"][-1]
        assert today_row["business_view"] >= 2
        assert today_row["website_click"] >= 1
        assert today_row["phone_click"] >= 1
        assert today_row["directions_click"] >= 1


# ---------------- ADMIN_EMAILS allowlist enforcement ----------------
class TestAdminEmailsLockdown:
    def test_non_admin_still_forbidden_on_new_endpoint(self, user_headers):
        """The new analytics deep-dive endpoint enforces require_admin."""
        r = requests.get(f"{API}/businesses", params={"category": "date-night"}, timeout=10)
        bid = r.json()[0]["id"]
        r2 = requests.get(f"{API}/admin/analytics/business/{bid}",
                          headers=user_headers, timeout=10)
        assert r2.status_code == 403

    def test_existing_admin_token_still_works(self, admin_headers):
        """Iteration-1 injected admin token (role=admin in mongo) is unaffected by ADMIN_EMAILS."""
        r = requests.get(f"{API}/auth/me", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("role") == "admin"

    def test_session_endpoint_rejects_fake_session_id(self):
        """Cannot bypass allowlist by sending a fake session_id."""
        r = requests.post(f"{API}/auth/session",
                          json={"session_id": "fake_not_real_xyz_123"}, timeout=15)
        assert r.status_code == 401


# ---------------- Admin: upload ----------------
# 1x1 transparent PNG
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="


class TestAdminUpload:
    def test_upload_requires_admin(self, user_headers):
        files = {"file": ("p.png", io.BytesIO(base64.b64decode(PNG_B64)), "image/png")}
        r = requests.post(f"{API}/admin/upload", headers=user_headers, files=files, timeout=20)
        assert r.status_code == 403

    def test_upload_and_fetch(self, admin_headers):
        files = {"file": ("p.png", io.BytesIO(base64.b64decode(PNG_B64)), "image/png")}
        r = requests.post(f"{API}/admin/upload", headers=admin_headers, files=files, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "path" in body and "url" in body
        assert body["url"].startswith("/api/files/")

        # fetch the file back
        r2 = requests.get(f"{BASE_URL}{body['url']}", timeout=20)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/")
        assert len(r2.content) > 0
