"""V2 recommendation engine tests: tag-based mood weighting + /api/admin/tags."""
import pytest
import requests
from test_config import BASE_URL, API, ADMIN_TOKEN, USER_TOKEN  # noqa: F401


@pytest.fixture(scope="session")
def admin_headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture(scope="session")
def user_headers():
    return {"Authorization": f"Bearer {USER_TOKEN}"}


CANONICAL_TAGS = {
    "coffee", "brunch", "casual", "fine_dining", "cocktails", "rooftop", "speakeasy",
    "live_music", "nightlife", "late_night", "hidden_gem", "unique", "wildcard",
    "date_night", "family", "scenic", "quiet", "popular", "tourist_favorite", "local_favorite",
}


# ---------------- /api/admin/tags ----------------
class TestAdminTagsEndpoint:
    def test_requires_auth(self):
        r = requests.get(f"{API}/admin/tags", timeout=10)
        assert r.status_code == 401

    def test_requires_admin(self, user_headers):
        r = requests.get(f"{API}/admin/tags", headers=user_headers, timeout=10)
        assert r.status_code == 403

    def test_returns_canonical_tags(self, admin_headers):
        r = requests.get(f"{API}/admin/tags", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "tags" in data and isinstance(data["tags"], list)
        tagset = set(data["tags"])
        missing = CANONICAL_TAGS - tagset
        assert not missing, f"Missing canonical tags: {missing}"


# ---------------- Backfill verification ----------------
class TestTagBackfill:
    EXPECTED = {
        "Hattie B's Hot Chicken": {"casual", "tourist_favorite", "popular"},
        "Catbird Seat": {"fine_dining", "date_night", "unique", "hidden_gem"},
        "The Bluebird Cafe": {"live_music", "quiet", "scenic", "local_favorite"},
        "Skull's Rainbow Room": {"unique", "hidden_gem", "live_music", "late_night"},
        "The Patterson House": {"cocktails", "date_night", "speakeasy", "hidden_gem"},
        "L.A. Jackson": {"rooftop", "cocktails", "scenic", "popular"},
        "UP Rooftop Lounge": {"rooftop", "nightlife", "popular"},
        "Bridgestone Arena": {"sports", "concerts", "popular", "entertainment"},
    }

    def test_seeded_businesses_have_expected_tags(self):
        # Fetch all (limit big enough)
        r = requests.get(f"{API}/businesses", params={"limit": 1000}, timeout=10)
        assert r.status_code == 200
        by_name = {b["name"]: b for b in r.json()}
        for name, expected in self.EXPECTED.items():
            assert name in by_name, f"Missing seeded business {name}"
            actual = set(by_name[name].get("tags") or [])
            assert expected.issubset(actual), \
                f"{name} tags {actual} missing expected {expected - actual}"


# ---------------- relevance_score in step response ----------------
class TestRelevanceScoreField:
    def test_each_step_has_positive_relevance_score(self):
        r = requests.post(f"{API}/itinerary/generate",
                          json={"vibe": "send-it", "city": "nashville"}, timeout=15)
        assert r.status_code == 200
        for step in r.json()["steps"]:
            assert "relevance_score" in step
            rs = step["relevance_score"]
            assert isinstance(rs, (int, float))
            assert rs > 0, f"relevance_score should be positive, got {rs}"


# ---------------- Statistical mood bias ----------------
def _run_n(vibe, n=30):
    """Return Counter-like dict of business name -> appearance count across n runs."""
    counts = {}
    for _ in range(n):
        r = requests.post(f"{API}/itinerary/generate",
                          json={"vibe": vibe, "city": "nashville"}, timeout=20)
        assert r.status_code == 200, r.text
        for s in r.json()["steps"]:
            name = s["business"]["name"]
            counts[name] = counts.get(name, 0) + 1
    return counts


class TestMoodBias:
    """Statistical tests — sufficient iterations to verify weighting is real."""

    def test_just_vibing_disfavors_nightlife_and_club(self):
        counts = _run_n("just-vibing", n=30)
        # nightlife/club-heavy names (penalty -10 each)
        nightlife_names = {"Exit/In", "The Basement East", "UP Rooftop Lounge"}
        # safe/preferred (coffee, family, quiet, scenic, casual)
        safe_names = {
            "Adventure Science Center", "Nashville Zoo at Grassmere",
            "Cheekwood Estate & Gardens", "The Bluebird Cafe",
            "Hattie B's Hot Chicken", "The Pharmacy Burger",
        }
        nightlife_total = sum(counts.get(n, 0) for n in nightlife_names)
        safe_total = sum(counts.get(n, 0) for n in safe_names)
        assert safe_total > nightlife_total, \
            f"just-vibing: safe {safe_total} should beat nightlife {nightlife_total} (counts={counts})"

    def test_send_it_prefers_wildcard_hidden_gem_unique(self):
        counts = _run_n("send-it", n=30)
        # Boosted names (wildcard/hidden_gem/unique/local_favorite weights 10/8/8/6)
        boosted = {"Skull's Rainbow Room", "Santa's Pub", "Catbird Seat", "Dino's"}
        # Penalized (tourist_favorite/casual/coffee = -2 each)
        penalized = {"Hattie B's Hot Chicken", "Nissan Stadium"}
        boosted_total = sum(counts.get(n, 0) for n in boosted)
        penalized_total = sum(counts.get(n, 0) for n in penalized)
        assert boosted_total > penalized_total, \
            f"send-it: boosted {boosted_total} should beat penalized {penalized_total} (counts={counts})"

    def test_very_down_prefers_nightlife_popular_concerts(self):
        counts = _run_n("very-down", n=30)
        boosted = {"The Basement East", "UP Rooftop Lounge", "Bridgestone Arena",
                   "CMA Fest", "Nissan Stadium"}
        penalized = {"Adventure Science Center", "The Bluebird Cafe",
                     "Cheekwood Estate & Gardens"}
        boosted_total = sum(counts.get(n, 0) for n in boosted)
        penalized_total = sum(counts.get(n, 0) for n in penalized)
        assert boosted_total > penalized_total, \
            f"very-down: boosted {boosted_total} should beat penalized {penalized_total} (counts={counts})"

    def test_down_prefers_date_night_cocktails_rooftop_live_music(self):
        counts = _run_n("down", n=30)
        preferred = {"Henrietta Red", "The Patterson House", "L.A. Jackson",
                     "The Bluebird Cafe", "Attaboy", "Rooftop at Bobby",
                     "Catbird Seat", "Rolf and Daughters"}
        pref_total = sum(counts.get(n, 0) for n in preferred)
        # We expect a strong baseline of appearances (at least 1/3 of total slot picks).
        total = sum(counts.values())  # 4 per run * 30 = 120
        assert pref_total >= total * 0.3, \
            f"down: preferred names appeared only {pref_total}/{total} (counts={counts})"


# ---------------- Sponsor weighting layered ON TOP of relevance ----------------
class TestSponsorOnTopOfRelevance:
    def test_platinum_beats_none_at_same_relevance(self, admin_headers):
        """Two TEST_ businesses, same tags, different sponsor tiers → platinum wins ~20x more."""
        a = {"name": "TEST_v2_plat", "category_slug": "drinks", "city_slug": "nashville",
             "sponsor_tier": "platinum", "slots": ["drinks"], "tags": ["cocktails"]}
        b = {"name": "TEST_v2_none", "category_slug": "drinks", "city_slug": "nashville",
             "sponsor_tier": "none", "slots": ["drinks"], "tags": ["cocktails"]}
        ra = requests.post(f"{API}/admin/businesses", headers=admin_headers, json=a, timeout=10)
        rb = requests.post(f"{API}/admin/businesses", headers=admin_headers, json=b, timeout=10)
        a_id, b_id = ra.json()["id"], rb.json()["id"]
        try:
            a_c = b_c = 0
            for _ in range(60):
                r = requests.post(f"{API}/itinerary/generate",
                                  json={"vibe": "down", "city": "nashville"}, timeout=15)
                for s in r.json()["steps"]:
                    if s["business"]["id"] == a_id:
                        a_c += 1
                    elif s["business"]["id"] == b_id:
                        b_c += 1
            assert a_c > b_c, f"platinum ({a_c}) should beat none ({b_c}) at same relevance"
        finally:
            requests.delete(f"{API}/admin/businesses/{a_id}", headers=admin_headers, timeout=10)
            requests.delete(f"{API}/admin/businesses/{b_id}", headers=admin_headers, timeout=10)


# ---------------- Edge cases: floor, empty tags, crashes ----------------
class TestEdgeCases:
    def test_heavily_penalized_business_doesnt_crash_engine(self, admin_headers):
        """A drinks slot with nightlife+club tags under just-vibing has heavy penalty (-20)
        → should clamp to floor 0.05 and not crash."""
        cr = requests.post(f"{API}/admin/businesses", headers=admin_headers, json={
            "name": "TEST_penalized", "category_slug": "drinks", "city_slug": "nashville",
            "sponsor_tier": "none", "slots": ["drinks"],
            "tags": ["nightlife", "club"],
        }, timeout=10)
        assert cr.status_code == 200
        bid = cr.json()["id"]
        try:
            for _ in range(5):
                r = requests.post(f"{API}/itinerary/generate",
                                  json={"vibe": "just-vibing", "city": "nashville"}, timeout=15)
                assert r.status_code == 200
                # All steps must have valid positive relevance_score
                for s in r.json()["steps"]:
                    assert s["relevance_score"] >= 0.05
        finally:
            requests.delete(f"{API}/admin/businesses/{bid}", headers=admin_headers, timeout=10)

    def test_business_without_tags_doesnt_crash(self, admin_headers):
        """No tags → default relevance 1.0, no crash."""
        cr = requests.post(f"{API}/admin/businesses", headers=admin_headers, json={
            "name": "TEST_no_tags", "category_slug": "drinks", "city_slug": "nashville",
            "sponsor_tier": "none", "slots": ["drinks"],
        }, timeout=10)
        assert cr.status_code == 200
        bid = cr.json()["id"]
        # The created business should have tags as empty list
        assert cr.json().get("tags") == []
        try:
            r = requests.post(f"{API}/itinerary/generate",
                              json={"vibe": "send-it", "city": "nashville"}, timeout=15)
            assert r.status_code == 200
        finally:
            requests.delete(f"{API}/admin/businesses/{bid}", headers=admin_headers, timeout=10)

    def test_slot_order_preserved(self):
        for vibe in ("just-vibing", "down", "very-down", "send-it"):
            r = requests.post(f"{API}/itinerary/generate",
                              json={"vibe": vibe, "city": "nashville"}, timeout=15)
            slots = [s["slot"] for s in r.json()["steps"]]
            assert slots == ["dinner", "drinks", "entertainment", "late-night"], \
                f"vibe {vibe} broke slot order: {slots}"

    def test_exclude_ids_still_works(self):
        r1 = requests.post(f"{API}/itinerary/generate",
                           json={"vibe": "very-down", "city": "nashville"}, timeout=15)
        first = [s["business"]["id"] for s in r1.json()["steps"]]
        r2 = requests.post(f"{API}/itinerary/generate",
                           json={"vibe": "very-down", "city": "nashville",
                                 "exclude_ids": first}, timeout=15)
        second = [s["business"]["id"] for s in r2.json()["steps"]]
        overlap = set(first) & set(second)
        assert len(overlap) <= 1, f"exclude_ids broken: overlap={overlap}"


# ---------------- Admin CRUD: tags field ----------------
class TestAdminTagsCRUD:
    def test_create_business_with_tags(self, admin_headers):
        r = requests.post(f"{API}/admin/businesses", headers=admin_headers, json={
            "name": "TEST_tags_create", "category_slug": "drinks", "city_slug": "nashville",
            "sponsor_tier": "none", "slots": ["drinks"],
            "tags": ["cocktails", "rooftop"],
        }, timeout=10)
        assert r.status_code == 200
        data = r.json()
        bid = data["id"]
        try:
            assert set(data.get("tags") or []) == {"cocktails", "rooftop"}
            # Verify persistence via public GET
            g = requests.get(f"{API}/businesses/{bid}", timeout=10)
            assert set(g.json().get("tags") or []) == {"cocktails", "rooftop"}
        finally:
            requests.delete(f"{API}/admin/businesses/{bid}", headers=admin_headers, timeout=10)

    def test_patch_tags_persists(self, admin_headers):
        cr = requests.post(f"{API}/admin/businesses", headers=admin_headers, json={
            "name": "TEST_tags_patch", "category_slug": "drinks", "city_slug": "nashville",
            "sponsor_tier": "none", "slots": ["drinks"],
        }, timeout=10)
        bid = cr.json()["id"]
        try:
            r = requests.patch(f"{API}/admin/businesses/{bid}", headers=admin_headers,
                               json={"tags": ["cocktails", "rooftop"]}, timeout=10)
            assert r.status_code == 200
            assert set(r.json().get("tags") or []) == {"cocktails", "rooftop"}
            g = requests.get(f"{API}/businesses/{bid}", timeout=10)
            assert set(g.json().get("tags") or []) == {"cocktails", "rooftop"}
        finally:
            requests.delete(f"{API}/admin/businesses/{bid}", headers=admin_headers, timeout=10)

    def test_patch_tags_empty_list(self, admin_headers):
        cr = requests.post(f"{API}/admin/businesses", headers=admin_headers, json={
            "name": "TEST_tags_clear", "category_slug": "drinks", "city_slug": "nashville",
            "sponsor_tier": "none", "slots": ["drinks"], "tags": ["cocktails"],
        }, timeout=10)
        bid = cr.json()["id"]
        try:
            r = requests.patch(f"{API}/admin/businesses/{bid}", headers=admin_headers,
                               json={"tags": []}, timeout=10)
            assert r.status_code == 200
            # Note: empty list is filtered by BusinessUpdate logic (k=v if v is not None)
            # [] is not None → it should be applied. Confirm:
            assert r.json().get("tags") == []
        finally:
            requests.delete(f"{API}/admin/businesses/{bid}", headers=admin_headers, timeout=10)
