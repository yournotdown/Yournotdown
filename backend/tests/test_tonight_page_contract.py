"""Source contract tests for the Tonight page Ticketmaster rendering path."""
import unittest
from pathlib import Path


TONIGHT_PAGE_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "TonightPage.jsx"
TONIGHT_PAGE_SOURCE = TONIGHT_PAGE_PATH.read_text()


class TestTonightPageContract(unittest.TestCase):
    def test_another_night_posts_excluded_event_ids(self):
        self.assertIn("exclude_event_ids: excludeEventIds", TONIGHT_PAGE_SOURCE)
        self.assertIn("live_music_event_mode: liveMusicEventMode", TONIGHT_PAGE_SOURCE)
        self.assertIn('const liveMusicStep = r.data.steps.find((step) => step.slot === "entertainment");', TONIGHT_PAGE_SOURCE)
        self.assertIn("const liveMusicEvent = liveMusicStep?.event;", TONIGHT_PAGE_SOURCE)
        self.assertIn("const liveMusicEventId = liveMusicEvent?.external_event_id || liveMusicEvent?.id;", TONIGHT_PAGE_SOURCE)
        self.assertIn("setSeenIds(newIds)", TONIGHT_PAGE_SOURCE)
        self.assertIn('if (liveMusicEvent?.source === "ticketmaster" && liveMusicEventId)', TONIGHT_PAGE_SOURCE)
        self.assertIn("setLastTicketmasterEventIds([liveMusicEventId]);", TONIGHT_PAGE_SOURCE)
        self.assertIn('} else if (liveMusicEventMode === "ticketmaster") {', TONIGHT_PAGE_SOURCE)
        self.assertIn("setLastTicketmasterEventIds([]);", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("new Set([...prev, ...newIds])", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("new Set([...prev, ...newEventIds])", TONIGHT_PAGE_SOURCE)

    def test_another_night_uses_ticketmaster_mode_every_fourth_refresh(self):
        self.assertIn("const [refreshCount, setRefreshCount] = useState(0);", TONIGHT_PAGE_SOURCE)
        self.assertIn("const nextRefreshCount = refreshCount + 1;", TONIGHT_PAGE_SOURCE)
        self.assertIn('const liveMusicEventMode = nextRefreshCount % 4 === 0 ? "ticketmaster" : "normal";', TONIGHT_PAGE_SOURCE)
        self.assertIn('excludeEventIds: liveMusicEventMode === "ticketmaster" ? lastTicketmasterEventIds : [],', TONIGHT_PAGE_SOURCE)

    def test_first_load_requests_ticketmaster_preferred_mode(self):
        self.assertIn('generate({ liveMusicEventMode: "ticketmaster_preferred" });', TONIGHT_PAGE_SOURCE)
        self.assertIn('if (liveMusicEvent?.source === "ticketmaster" && liveMusicEventId)', TONIGHT_PAGE_SOURCE)

    def test_live_music_step_renders_event_details_inline(self):
        self.assertIn("Tonight: {event.title}", TONIGHT_PAGE_SOURCE)
        self.assertIn('formatEventTime(event?.local_time)', TONIGHT_PAGE_SOURCE)
        self.assertIn('event.venue_name || b.name', TONIGHT_PAGE_SOURCE)
        self.assertIn('href={event.ticket_url}', TONIGHT_PAGE_SOURCE)

    def test_tonight_page_renders_active_sponsorship_when_present(self):
        self.assertIn("const sponsorship = itinerary?.tonight_move_sponsorship;", TONIGHT_PAGE_SOURCE)
        self.assertIn('data-testid="tonight-sponsorship"', TONIGHT_PAGE_SOURCE)
        self.assertIn("Sponsored by", TONIGHT_PAGE_SOURCE)
        self.assertIn('data-testid="tonight-sponsorship-link"', TONIGHT_PAGE_SOURCE)
        self.assertIn('data-testid="tonight-sponsorship-tagline"', TONIGHT_PAGE_SOURCE)

    def test_standalone_tonights_shows_section_is_removed(self):
        self.assertNotIn("live_music_events", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("Tonight's Shows", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("TONIGHT'S SHOWS", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("No eligible Ticketmaster shows listed for tonight", TONIGHT_PAGE_SOURCE)


if __name__ == "__main__":
    unittest.main()
