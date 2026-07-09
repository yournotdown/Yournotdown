"""Dependency-free source contracts for sponsor-grade analytics tracking."""
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


class TestAnalyticsContract(unittest.TestCase):
    def test_startup_maintenance_creates_hot_path_indexes(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_apply_startup_maintenance"))
        self.assertIn('await db.businesses.create_index([("id", 1)])', source)
        self.assertIn('await db.businesses.create_index([("city_slug", 1), ("imported_status", 1), ("featured", -1), ("order", 1)])', source)
        self.assertIn('await db.analytics_events.create_index([("event_type", 1), ("timestamp", -1)])', source)
        self.assertIn('await db.saved_itineraries.create_index([("visitor_id", 1), ("created_at", -1)])', source)
        self.assertIn('await db.audience_contacts.create_index([("marketing_opt_in", 1), ("last_saved_at", -1)])', source)
        self.assertIn('await db.visitor_profiles.create_index([("last_seen_at", -1)])', source)
        self.assertIn('await db.hotel_qr_codes.create_index([("city_slug", 1), ("active", 1), ("created_at", -1)])', source)
        self.assertIn('await db.business_owner_invites.create_index([("business_id", 1), ("status", 1), ("created_at", -1)])', source)
        self.assertIn('await db.business_owner_sessions.create_index([("business_id", 1), ("revoked_at", 1)])', source)
        self.assertIn('await db.user_sessions.create_index([("session_token_hash", 1)])', source)
        self.assertIn('await db.user_sessions.create_index([("expires_at", 1)])', source)

    def test_business_scoped_events_include_ticket_locked_and_saved_types(self):
        source = SERVER_SOURCE
        self.assertIn('"ticket_click"', source)
        self.assertIn('"step_locked"', source)
        self.assertIn('"saved_itinerary_business"', source)

    def test_business_appearance_events_now_stamp_slot(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("generate_itinerary"))
        self.assertIn('slot=step.get("slot", "")', source)
        self.assertIn('source_surface="tonight_page"', source)

    def test_itinerary_request_and_picker_support_slot_specific_seen_excludes(self):
        request_source = ast.get_source_segment(SERVER_SOURCE, named_function("generate_itinerary"))
        picker_source = ast.get_source_segment(SERVER_SOURCE, named_function("_weighted_pick"))
        self.assertIn('exclude_ids_by_slot: Dict[str, List[str]] = Field(default_factory=dict)', SERVER_SOURCE)
        self.assertIn("exclude_ids_by_slot = {", request_source)
        self.assertIn('slot_history_excludes = exclude_ids_by_slot.get(label["slot"], set())', request_source)
        self.assertIn("vibe: Optional[str],", picker_source)
        self.assertIn("historical_exclude_ids: Optional[set] = None", picker_source)
        self.assertIn('filtered_pool = [b for b in pool if b["id"] not in historical_exclude_ids]', picker_source)
        self.assertIn('pool = [b for b in candidates if b["id"] not in exclude_ids]', picker_source)
        self.assertIn("relevance = _relevance_score(b, vibe)", picker_source)
        self.assertIn('sponsor_mult = SPONSOR_MULTIPLIERS.get(b.get("sponsor_tier", "none"), 1)', picker_source)

    def test_track_endpoint_stamps_sponsor_tier_for_business_scoped_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("track_event"))
        self.assertIn("event.event_type in BUSINESS_SCOPED_EVENT_TYPES", source)
        self.assertIn('"visitor_id": _normalize_visitor_id(event.visitor_id) or None', source)
        self.assertIn('"qr_slug": _normalize_qr_slug(event.qr_slug) or None', source)
        self.assertIn('"slot": event.slot', source)
        self.assertIn('"event_id": event.event_id', source)
        self.assertIn('"event_source": event.event_source', source)
        self.assertIn("await _upsert_visitor_profile(", source)

    def test_visitor_profile_helper_tracks_first_and_repeat_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_upsert_visitor_profile"))
        self.assertIn('"visitor_id": visitor_id', source)
        self.assertIn('"first_seen_at": now', source)
        self.assertIn('"last_seen_at": now', source)
        self.assertIn('"event_count": int(existing.get("event_count", 0)) + 1', source)
        self.assertIn('"saved_itinerary_count": int(existing.get("saved_itinerary_count", 0)) + (1 if increment_saved_itinerary else 0)', source)

    def test_missing_visitor_id_is_ignored_safely(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_upsert_visitor_profile"))
        self.assertIn("if not visitor_id:", source)
        self.assertIn("return None", source)

    def test_visitor_profile_helper_tracks_qr_slug_when_present(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_upsert_visitor_profile"))
        self.assertIn('"first_qr_slug": qr_slug or ""', source)
        self.assertIn('"last_qr_slug": qr_slug or existing.get("last_qr_slug", "")', source)

    def test_save_itinerary_writes_saved_business_analytics_events(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("save_itinerary"))
        self.assertIn('"saved_itinerary_business"', source)
        self.assertIn('await db.analytics_events.insert_many(saved_step_events)', source)
        self.assertIn('logger.warning("saved_itinerary_business analytics write failed: %s", exc)', source)

    def test_hotel_qr_admin_endpoints_exist_and_require_admin(self):
        source = SERVER_SOURCE
        self.assertIn('@api_router.get("/admin/hotel-qr")', source)
        self.assertIn('@api_router.post("/admin/hotel-qr")', source)
        self.assertIn('@api_router.patch("/admin/hotel-qr/{qr_id}")', source)
        self.assertIn('@api_router.post("/admin/hotel-qr/{qr_id}/deactivate")', source)
        self.assertIn('@api_router.delete("/admin/hotel-qr/{qr_id}")', source)
        self.assertIn("user=Depends(require_admin)", ast.get_source_segment(SERVER_SOURCE, named_function("admin_create_hotel_qr_code")))
        self.assertIn("user=Depends(require_admin)", ast.get_source_segment(SERVER_SOURCE, named_function("admin_list_hotel_qr_codes")))
        self.assertIn("user=Depends(require_admin)", ast.get_source_segment(SERVER_SOURCE, named_function("admin_delete_hotel_qr_code")))

    def test_hotel_qr_slug_generation_and_destination_url_are_safe(self):
        slug_source = ast.get_source_segment(SERVER_SOURCE, named_function("_slugify_qr_name"))
        unique_source = ast.get_source_segment(SERVER_SOURCE, named_function("_unique_hotel_qr_slug"))
        destination_source = ast.get_source_segment(SERVER_SOURCE, named_function("_hotel_qr_destination_url"))
        self.assertIn("re.sub", slug_source)
        self.assertIn('candidate = f"{slug}-{suffix}"', unique_source)
        self.assertIn('return f"{base}?qr={qr_slug}"', destination_source)

    def test_hotel_qr_response_helper_strips_raw_objectid_fields(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_hotel_qr_response"))
        self.assertIn('"id": doc.get("id", "")', source)
        self.assertIn('"destination_url": doc.get("destination_url", "")', source)
        self.assertNotIn('"_id"', source)

    def test_hotel_qr_analytics_summary_includes_scans_saves_and_lock_clicks(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_list_hotel_qr_codes"))
        self.assertIn('"hotel_qr_scan"', source)
        self.assertIn('"step_locked"', source)
        self.assertIn('"saved_moves": saved_moves', source)
        self.assertIn('"email_captures": len(stats.get("emails", set()))', source)
        self.assertIn('"marketing_opt_ins": len(stats.get("marketing_emails", set()))', source)
        self.assertIn('"conversion_rate": round(saved_moves / scans, 4) if scans else 0', source)
        self.assertIn("payload_rows.append(_hotel_qr_response({", source)

    def test_hotel_qr_create_update_and_deactivate_return_json_safe_responses(self):
        create_source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_create_hotel_qr_code"))
        update_source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_update_hotel_qr_code"))
        deactivate_source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_deactivate_hotel_qr_code"))
        delete_source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_delete_hotel_qr_code"))
        self.assertIn("await db.hotel_qr_codes.insert_one(doc)", create_source)
        self.assertIn("return _hotel_qr_response(doc)", create_source)
        self.assertIn("return _hotel_qr_response(await db.hotel_qr_codes.find_one", update_source)
        self.assertIn("return _hotel_qr_response(await db.hotel_qr_codes.find_one", deactivate_source)
        self.assertIn('"deleted": _hotel_qr_response(existing)', delete_source)

    def test_image_endpoints_use_bounded_google_widths_and_longer_cache_headers(self):
        photo_source = ast.get_source_segment(SERVER_SOURCE, named_function("google_places_photo"))
        files_source = ast.get_source_segment(SERVER_SOURCE, named_function("serve_file"))
        self.assertIn("max_width: Optional[int] = None", photo_source)
        self.assertIn("safe_max_width = normalize_google_places_photo_width(max_width)", photo_source)
        self.assertIn('await run_in_threadpool(fetch_google_places_photo, photo_name, safe_max_width)', photo_source)
        self.assertIn('"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"', photo_source)
        self.assertIn('"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"', files_source)

    def test_duplicate_risk_indexes_remain_non_unique_except_existing_safe_keys(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_apply_startup_maintenance"))
        self.assertIn('await db.audience_contacts.create_index("email_normalized", unique=True)', source)
        self.assertIn('await db.visitor_profiles.create_index("visitor_id", unique=True)', source)
        self.assertIn('await db.hotel_qr_codes.create_index("slug", unique=True)', source)
        self.assertNotIn('await db.businesses.create_index("id", unique=True)', source)
        self.assertNotIn('await db.business_owner_invites.create_index([("token_hash", 1)], unique=True)', source)
        self.assertNotIn('await db.business_owner_sessions.create_index([("session_token_hash", 1)], unique=True)', source)
        self.assertNotIn('await db.user_sessions.create_index([("session_token_hash", 1)], unique=True)', source)

    def test_hotel_qr_delete_removes_only_config_row_and_handles_missing(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_delete_hotel_qr_code"))
        self.assertIn('await db.hotel_qr_codes.delete_one({"id": qr_id})', source)
        self.assertIn('raise HTTPException(status_code=404, detail="Hotel QR not found")', source)
        self.assertNotIn("analytics_events.delete", source)
        self.assertNotIn("saved_itineraries.delete", source)

    def test_hotel_qr_list_is_bounded_and_supports_days_window(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_list_hotel_qr_codes"))
        self.assertIn('days: str = "30"', source)
        self.assertIn('limit: int = ADMIN_HOTEL_QR_DEFAULT_LIMIT', source)
        self.assertIn('offset: int = 0', source)
        self.assertIn("limit, offset = _normalize_pagination(", source)
        self.assertIn("since = _analytics_since(days)", source)
        self.assertIn('skip(offset).limit(limit)', source)
        self.assertIn('"meta": {', source)

    def test_admin_summary_supports_filters_and_leaderboards(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_analytics_summary"))
        self.assertIn('days: str = "30"', source)
        self.assertIn("city_slug: Optional[str] = None", source)
        self.assertIn("vibe: Optional[str] = None", source)
        self.assertIn("slot: Optional[str] = None", source)
        self.assertIn("base_match = _analytics_match_query(days=days, city_slug=city_slug, vibe=vibe_filter)", source)
        self.assertIn('{"$group": {"_id": "$business_id", **_event_count_group_fields()}}', source)
        self.assertIn('ADMIN_ANALYTICS_BUSINESS_BREAKDOWN_LIMIT', source)
        self.assertIn('ADMIN_ANALYTICS_LEADERBOARD_LIMIT', source)
        self.assertIn('ADMIN_ANALYTICS_SLOT_LEADERBOARD_LIMIT', source)
        self.assertIn('"limits": {', source)
        self.assertIn('"slot_leaderboards": slot_leaderboards', source)
        self.assertIn('"top_saved_in_final_move_businesses": top_saved_in_final_move_businesses', source)
        self.assertIn('"top_website_click_businesses": top_website_click_businesses', source)
        self.assertIn('"top_directions_click_businesses": top_directions_click_businesses', source)
        self.assertIn('"top_phone_click_businesses": top_phone_click_businesses', source)
        self.assertIn('"top_click_through_businesses": top_click_through_businesses', source)
        self.assertIn('"top_sponsor_businesses": top_sponsor_businesses', source)
        self.assertIn('"vibe_breakdown": vibe_breakdown', source)
        self.assertIn('"totals": totals', source)

    def test_homepage_visit_usage_metrics_use_visitor_id_not_ip(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_homepage_visit_usage_metrics"))
        self.assertIn('match["event_type"] = "homepage_visit"', source)
        self.assertIn('{"$match": {"visitor_id": {"$nin": [None, ""]}}}', source)
        self.assertIn('{"$group": {"_id": "$visitor_id", "visit_count": {"$sum": 1}}}', source)
        self.assertIn('"unique_visitors": {"$sum": 1}', source)
        self.assertIn('{"$gt": ["$visit_count", 1]}', source)
        self.assertIn('"returning_visitor_rate": returning_visitor_rate', source)
        self.assertNotIn('"ip"', source)

    def test_admin_summary_totals_include_usage_cards(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_analytics_summary"))
        self.assertIn("usage_totals = await _homepage_visit_usage_metrics(days=days, city_slug=city_slug)", source)
        self.assertIn("**usage_totals", source)
        self.assertIn('"totals": totals', source)

    def test_admin_business_analytics_defaults_to_bounded_window(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("admin_business_analytics"))
        self.assertIn('days: str = "30"', source)
        self.assertIn("since = _analytics_since(days)", source)
        self.assertIn('totals_match = {"business_id": business_id}', source)
        self.assertIn('if since:', source)
        self.assertIn('ADMIN_ANALYTICS_BUSINESS_TIMELINE_LIMIT', source)
        self.assertIn('"filters": {', source)

    def test_metric_aliases_define_total_engagement_and_safe_rate(self):
        source = ast.get_source_segment(SERVER_SOURCE, named_function("_metric_aliases"))
        self.assertIn('"appearances": counts.get("business_appearance", 0)', source)
        self.assertIn('"locked_in": counts.get("step_locked", 0)', source)
        self.assertIn('"saved_in_final_move": counts.get("saved_itinerary_business", 0)', source)
        self.assertIn('"ticket_clicks": counts.get("ticket_click", 0)', source)
        self.assertIn('if counts.get("business_appearance", 0)', source)


if __name__ == "__main__":
    unittest.main()
