"""Source contracts for the narrow live Google ratings Tonight's Move integration."""
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


class TestLiveRatingsContract(unittest.TestCase):
    def test_live_ratings_constants_are_narrow_and_bounded(self):
        self.assertIn('RATE_LIMIT_PLACES_LIVE_RATINGS_PER_IP = 30', SERVER_SOURCE)
        self.assertIn('GOOGLE_PLACES_DETAILS_API_URL = "https://places.googleapis.com/v1/places"', SERVER_SOURCE)
        self.assertIn('GOOGLE_PLACES_LIVE_RATINGS_FIELD_MASK = "rating,userRatingCount,googleMapsUri,attributions"', SERVER_SOURCE)
        self.assertIn('GOOGLE_PLACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,200}$")', SERVER_SOURCE)

    def test_fetch_helper_only_requests_approved_fields_and_never_persists(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_fetch_google_place_live_rating"))
        self.assertIn('"X-Goog-Api-Key": api_key', source)
        self.assertIn('"X-Goog-FieldMask": GOOGLE_PLACES_LIVE_RATINGS_FIELD_MASK', source)
        self.assertIn("timeout=5", source)
        self.assertNotIn("db.", source)

    def test_response_item_returns_safe_structured_provider_attributions(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_live_rating_response_item"))
        self.assertIn('provider = (attribution.get("provider") or "").strip()', source)
        self.assertIn('provider_uri = (attribution.get("providerUri") or "").strip()', source)
        self.assertIn('"provider": provider', source)
        self.assertIn('"providerUri": provider_uri', source)
        self.assertNotIn("raw_html", source)

    def test_endpoint_validates_limits_and_handles_partial_failures_safely(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("live_place_ratings"))
        self.assertIn('_require_ip_rate_limit(', source)
        self.assertIn('"places_live_ratings_ip"', source)
        self.assertIn('limit=RATE_LIMIT_PLACES_LIVE_RATINGS_PER_IP', source)
        self.assertIn('raise HTTPException(status_code=400, detail="Invalid place ID.")', source)
        self.assertIn('raise HTTPException(status_code=400, detail="A maximum of 4 place IDs is allowed.")', source)
        self.assertIn("seen_place_ids = set()", source)
        self.assertIn("if place_id in seen_place_ids:", source)
        self.assertIn("normalized_place_ids.append(place_id)", source)
        self.assertIn('if len(normalized_place_ids) > 4:', source)
        self.assertIn('if not normalized_place_ids:', source)
        self.assertIn('return {"results": {}}', source)
        self.assertIn('await run_in_threadpool(_fetch_google_place_live_rating, place_id)', source)
        self.assertIn("except requests.RequestException as exc:", source)
        self.assertIn("except Exception as exc:", source)
        self.assertIn("continue", source)
        self.assertIn('results[place_id] = item', source)
        self.assertNotIn("insert_one", source)
        self.assertNotIn("update_one", source)
        self.assertNotIn("update_many", source)

    def test_endpoint_logs_failures_without_raw_sensitive_request_data(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("live_place_ratings"))
        self.assertIn('"live place rating request failed: place_id_hash=%s error_type=%s detail=%s"', source)
        self.assertIn("_hash_token(place_id)[:12]", source)
        self.assertIn("describe_google_places_request_error(exc)", source)
        self.assertNotIn("X-Goog-Api-Key", source)
        self.assertNotIn("place_id=%s", source)


if __name__ == "__main__":
    unittest.main()
