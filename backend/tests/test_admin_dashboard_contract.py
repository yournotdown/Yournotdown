"""Source contract tests for admin itinerary bucket and sponsorship visibility."""
import unittest
from pathlib import Path


ADMIN_PAGE_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "AdminDashboardPage.jsx"
ADMIN_PAGE_SOURCE = ADMIN_PAGE_PATH.read_text()
SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
SERVER_SOURCE = SERVER_PATH.read_text()


class TestAdminDashboardContract(unittest.TestCase):
    def test_admin_business_list_uses_backend_computed_itinerary_buckets(self):
        self.assertIn("annotate_itinerary_buckets(items)", SERVER_SOURCE)
        self.assertIn("itinerary_buckets", ADMIN_PAGE_SOURCE)

    def test_admin_businesses_panel_has_bucket_filter(self):
        self.assertIn('data-testid="admin-filter-bucket"', ADMIN_PAGE_SOURCE)
        self.assertIn("All itinerary buckets", ADMIN_PAGE_SOURCE)
        self.assertIn("Live Music", ADMIN_PAGE_SOURCE)
        self.assertIn("Late Night", ADMIN_PAGE_SOURCE)

    def test_admin_businesses_panel_renders_bucket_badges(self):
        self.assertIn("admin-itinerary-buckets-", ADMIN_PAGE_SOURCE)
        self.assertIn("ItineraryBucketBadge", ADMIN_PAGE_SOURCE)

    def test_admin_featured_live_music_panel_renders_core_fields(self):
        self.assertIn("Featured Live Music Event", ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="admin-sponsorships-tab"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="admin-featured-live-music"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="featured-live-music-title"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="featured-live-music-venue-name"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="featured-live-music-local-date"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="featured-live-music-ticket-url"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="featured-live-music-save"', ADMIN_PAGE_SOURCE)

    def test_server_exposes_admin_featured_live_music_endpoints(self):
        self.assertIn('@api_router.get("/admin/featured-events/live-music")', SERVER_SOURCE)
        self.assertIn('@api_router.put("/admin/featured-events/live-music")', SERVER_SOURCE)
        self.assertIn('@api_router.delete("/admin/featured-events/live-music/{event_id}")', SERVER_SOURCE)
        self.assertIn("user=Depends(require_admin)", SERVER_SOURCE)

    def test_sponsorships_tab_exists_and_contains_tonight_move_controls(self):
        self.assertIn('{ id: "sponsorships", label: "Sponsorships", icon: Star }', ADMIN_PAGE_SOURCE)
        self.assertIn("Tonight&apos;s Move Sponsorship", ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="admin-tonight-move-sponsorship"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="tonight-move-sponsorship-name"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="tonight-move-sponsorship-url"', ADMIN_PAGE_SOURCE)
        self.assertIn('data-testid="tonight-move-sponsorship-save"', ADMIN_PAGE_SOURCE)

    def test_businesses_tab_no_longer_renders_featured_live_music_panel(self):
        self.assertNotIn('{tab === "businesses" && (\n          <>\n            <FeaturedLiveMusicPanel', ADMIN_PAGE_SOURCE)
        self.assertIn('{tab === "sponsorships" && (', ADMIN_PAGE_SOURCE)

    def test_server_exposes_admin_tonight_move_sponsorship_endpoints(self):
        self.assertIn('@api_router.get("/admin/sponsorships/tonight-move")', SERVER_SOURCE)
        self.assertIn('@api_router.put("/admin/sponsorships/tonight-move")', SERVER_SOURCE)
        self.assertIn('@api_router.delete("/admin/sponsorships/tonight-move/{sponsorship_id}")', SERVER_SOURCE)
        self.assertIn("db.admin_sponsorships", SERVER_SOURCE)


if __name__ == "__main__":
    unittest.main()
