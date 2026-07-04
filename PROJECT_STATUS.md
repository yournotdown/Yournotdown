## Current State

You're Not Down is Blake's nightlife and tourist discovery product focused on helping visitors quickly decide what to do tonight, with Nashville as the first market. The intended product shape is lightweight and conversion-focused: hotel QR distribution, simple itinerary generation, and fast 1 to 4 step plans for tourists choosing bars, restaurants, and local activities.

The current repository memory state was being established on branch `chore/add-codex-project-memory`. At the time these notes were created, the repo had one unrelated untracked file at `migrations/import_via_production_admin_api.py` that should not be modified as part of memory setup.

## Last Known Focus

The immediate focus is safely extracting catalog data from the old Emergent production API into local JSON exports, without changing application logic, touching production data, or running any import step yet.

## Latest Work Session

A new read-only exporter now exists at `migrations/export_catalog_from_production_api.py`. It targets `https://yournotdown.com/api` by default, allows `API_BASE_URL` override, writes JSON files into `migrations/emergent_export`, supports `--collections`, and only performs HTTP GET requests.

The catalog JSON export has now been completed outside this session with:
- `categories`: 6
- `cities`: 1
- `businesses`: 121
- `city_events`: 0 because the old API only exposes `/events/today`, not the full collection

A new local-only importer now exists at `migrations/import_catalog_json_to_mongo.py`. It reads `DEST_MONGO_URL` and `DEST_DB`, defaults to `dry-run`, defaults collections to `categories,cities,businesses`, excludes `city_events` unless explicitly requested, supports Mongo Extended JSON parsing, refuses writes to non-empty collections unless `--allow-non-empty` is passed, and skips duplicate `_id` inserts with reporting.

Endpoint findings captured in code review:
- `categories`: public `GET /api/categories`
- `cities`: public `GET /api/cities`
- `businesses`: public `GET /api/businesses` per city, or authenticated `GET /api/admin/businesses` when `ADMIN_SESSION_TOKEN` is available
- `city_events`: public `GET /api/events/today` per city; no full read endpoint for the entire `city_events` collection was found in local backend code

The exporter script had already produced the JSON files before this session. The importer script was created but not run. No Mongo import, staging, commit, deploy, or domain connection steps were performed in this session.

## Photo Proxy Follow-Up

The current operational issue is the final Google Places business photo failure after catalog import. Frontend and backend are working on Railway, the Mongo catalog import completed, and Tonight's Move loads, but business photo requests are failing because the backend photo proxy is requesting Google Places media with stored `google_photo_names` that appear to be stale cached photo resource names from the earlier import.

The exported business data in `migrations/emergent_export/businesses.json` contains `121` businesses total, with `91` businesses carrying both `google_place_id` and `google_photo_names`. Those names were imported on `2026-05-31`, which makes them unsuitable to rely on indefinitely because Google Places Photos New photo names can expire and must be refreshed from Place Details or search responses.

Two local-only code changes were prepared in this session:
- `backend/google_places_photos.py` now includes a helper to redact Google API keys from logged request URLs and produce sanitized Google Places error summaries.
- `migrations/refresh_google_photo_names.py` was added as a dry-run-by-default script that reads `DEST_MONGO_URL`, `DEST_DB`, and `GOOGLE_PLACES_API_KEY`, scans businesses with `google_place_id`, calls Places Details New with `X-Goog-FieldMask: id,displayName,photos`, reports fresh photo-name coverage and samples, and only updates `google_photo_names` plus `google_photo_names_refreshed_at` when `--apply` is explicitly passed.

No deploy, no refresh run, no Mongo manual changes, no staging, and no commit were performed in this session.
