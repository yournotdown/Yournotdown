"""Source contract tests for the Tonight page Ticketmaster rendering path."""
import unittest
from pathlib import Path


TONIGHT_PAGE_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "TonightPage.jsx"
TONIGHT_PAGE_SOURCE = TONIGHT_PAGE_PATH.read_text()


class TestTonightPageContract(unittest.TestCase):
    def test_another_night_posts_excluded_event_ids(self):
        self.assertIn("exclude_event_ids: excludeEventIds", TONIGHT_PAGE_SOURCE)
        self.assertIn("generate(seenIds, seenEventIds)", TONIGHT_PAGE_SOURCE)
        self.assertIn("setSeenIds(newIds)", TONIGHT_PAGE_SOURCE)
        self.assertIn("setSeenEventIds(newEventIds)", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("new Set([...prev, ...newIds])", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("new Set([...prev, ...newEventIds])", TONIGHT_PAGE_SOURCE)

    def test_live_music_step_renders_event_details_inline(self):
        self.assertIn("Tonight: {event.title}", TONIGHT_PAGE_SOURCE)
        self.assertIn('formatEventTime(event?.local_time)', TONIGHT_PAGE_SOURCE)
        self.assertIn('event.venue_name || b.name', TONIGHT_PAGE_SOURCE)
        self.assertIn('href={event.ticket_url}', TONIGHT_PAGE_SOURCE)

    def test_standalone_tonights_shows_section_is_removed(self):
        self.assertNotIn("live_music_events", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("Tonight's Shows", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("TONIGHT'S SHOWS", TONIGHT_PAGE_SOURCE)
        self.assertNotIn("No eligible Ticketmaster shows listed for tonight", TONIGHT_PAGE_SOURCE)


if __name__ == "__main__":
    unittest.main()
