"""Source contract tests for admin itinerary bucket visibility."""
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


if __name__ == "__main__":
    unittest.main()
