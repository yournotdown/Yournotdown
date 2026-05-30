"""Backend tests for You're Not Down — Nashville discovery app."""
import os
import io
import base64
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://whatsyoudown.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_TOKEN = "test_session_admin_1780165861579"
USER_TOKEN = "test_session_user_1780165861637"

EXPECTED_CATEGORIES = {"food", "drinks", "live-music", "date-night", "family-fun", "sports", "rooftops", "events", "surprise-me"}


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
        assert nashville["default"] is True

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


# ---------------- Businesses ----------------
class TestBusinesses:
    def test_food_category(self):
        r = requests.get(f"{API}/businesses", params={"category": "food"}, timeout=10)
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
        r = requests.get(f"{API}/businesses", params={"category": "food"}, timeout=10)
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
        {"event_type": "category_click", "category_slug": "food"},
        {"event_type": "phone_click"},
        {"event_type": "directions_click"},
        {"event_type": "website_click"},
    ])
    def test_track_events(self, evt):
        r = requests.post(f"{API}/analytics/track", json=evt, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_business_view_event(self):
        r = requests.get(f"{API}/businesses", params={"category": "food"}, timeout=10)
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
        payload = {"name": "TEST_Biz", "description": "test", "category_slug": "food", "city_slug": "nashville"}
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
        assert r.json()["featured"] is True
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
        assert len(r.json()) == 9

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
