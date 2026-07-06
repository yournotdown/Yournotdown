## Current State

You're Not Down is Blake's nightlife and tourist discovery product focused on helping visitors quickly decide what to do tonight, with Nashville as the first market. The intended product shape remains lightweight and conversion-focused: hotel QR distribution, simple itinerary generation, and fast 1 to 4 step plans for tourists choosing bars, restaurants, and local activities.

The repo is currently on branch `main`. The only known worktree changes outside this documentation update are two unrelated untracked migration files: `migrations/copy_catalog_collections.py` and `migrations/import_via_production_admin_api.py`. They remain untouched.

## Latest Work Session

The immediate production issue is no longer cron execution. Ticketmaster sync and the Railway cron are verified working in production, and the current local follow-up is correcting how today/tonight event data is filtered and rendered in the customer-facing product.

Verified production Ticketmaster cron/apply summary:
- `status=ok`
- `mode=apply`
- `dates=2026-07-05,2026-07-06`
- `fetched=16`
- `after_dedupe=16`
- `matched=8`
- `unmatched=8`
- `upserted=9`
- `deleted_expired=5`
- `errors=0`

Investigated user-facing event paths and root causes:
- `frontend/src/pages/CategoryDetailPage.jsx` was fetching `/api/events/today` for every category and rendering a city-wide event list, not matched venue events for Live Music.
- `frontend/src/pages/TonightPage.jsx` already rendered attached event data when the itinerary business matched `city_events`, but the CTA label/time display needed cleanup.
- public `/api/businesses` results were still exposing static event-like catalog rows such as `Tomato Art Fest`, `Live On The Green`, and `CMA Fest`, plus imported `Musicians Corner`, even when they were outside the today/tonight window.
- `Musicians Corner` is currently coming from approved imported business data, not from a Ticketmaster `city_events` row.
- `Tomato Art Fest` is currently coming from legacy seeded business data migrated from the removed `events` category into `night-out`, not from Ticketmaster.
- no reliable structured field currently distinguishes those rows from normal public business/venue rows after import and category migration; generic suppression will require schema/data cleanup rather than name matching.
- no static frontend fixtures or prompt text were found to be injecting those names into the public experience; the leakage was from public business catalog reads.
- the actual public Tonight product surface is `/:citySlug/tonight?vibe=...`, which calls only `POST /api/itinerary/generate` plus the same call again for the “Another Night” refresh flow.
- `CategoryDetailPage.jsx` is still publicly routed at `/:citySlug/c/:slug`, but it is not the real Tonight flow and should not be treated as the primary event-surfacing path.

Verified production platform state still preserved:
- `www.yournotdown.com` works on the Railway frontend
- `yournotdown.com` now forwards and loads correctly to the clean app path
- Tonight's Move loads
- photos load
- the Emergent badge and script are removed
- network checks on tested pages returned zero results for `assets.emergent`, `emergent-main`, `emergentcf`, `whatsyoudown.cluster`, and `static.prod-images.emergentagent.com`
- the Railway backend is healthy
- the Railway photo refresh cron exists
- 7 Emergent-hosted image records were safely backfilled
- 3 remaining image records are intentionally untouched for now: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`

Known remaining Emergent dependencies:
- Emergent is no longer the public production runtime for the customer-facing app; public traffic is on Railway.
- Admin login still depends on Emergent Google OAuth redirect/exchange flow (`auth.emergentagent.com` and backend session exchange against `demobackend.emergentagent.com`).
- After login, admin sessions are stored locally in Mongo for 7 days, but new admin logins still depend on Emergent being available.
- Emergent object storage may still remain an admin upload dependency and should be treated as active until replaced.
- Do not delete or fully decommission Emergent dependencies until first-party admin auth and storage replacements are in place.

Operational constraints preserved in this session:
- no deploy
- no merge
- no delete
- no migrations run
- no Railway service creation
- no secret changes
- no staging or commit
- no local or production apply sync execution from the new cron entrypoint

Latest local patch state:
- added shared city-event eligibility logic for public event reads and itinerary event attachment
- excluded `cancelled`, `canceled`, and `offsale` event statuses from public/today eligibility
- added same-day stale filtering with a configurable grace window via `EVENT_START_GRACE_MINUTES` defaulting to 60
- kept `local_time == null` events eligible for now unless status is excluded
- added shared public business filtering so `/api/businesses`, `/api/businesses/{id}`, and itinerary generation all use the same today/tonight event context
- attached matched `city_events` onto public business responses as `event`, preserving `title`, `venue_name`, `local_date`, `local_time`, `ticket_url`, and `venue_business_id`
- updated Tonight’s Move step cards to show attached event title, formatted show time, and a `Buy Tickets` button when `ticket_url` exists
- removed the temporary name-based suppression for event-like business rows because it was not generic or data-driven enough to keep
- identified follow-up schema/data work still needed if those rows should be hidden from today/tonight public business discovery without relying on names
- removed the standalone Tonight page “Live Music / Tonight’s Shows” section after confirming it was the wrong product surface
- updated itinerary generation so the numbered `LIVE MUSIC` step now prefers eligible Ticketmaster music events only, using Ticketmaster `classification_segment == Music` when present and falling back to approved live-music venue metadata when older synced rows lack stored classifications
- excluded sports/baseball Ticketmaster rows from the numbered `LIVE MUSIC` step
- updated “Another Night” to send `exclude_event_ids` so Ticketmaster-backed live-music steps can rotate to a different eligible show when available
- kept the numbered `LIVE MUSIC` step pinned to normal live-music venues when no eligible Ticketmaster music event exists, instead of falling through to arbitrary non-music entertainment businesses
- updated the Tonight step hero image preference to use the matched venue/business image first and the event image only as fallback
- fixed the Another Night exhaustion bug by stopping the frontend from accumulating itinerary business/event exclusions forever; the refresh payload now sends only the immediately previous itinerary ids
- updated live-music event picking to relax event/business exclusions when they exhaust the eligible Ticketmaster music pool, so the numbered `LIVE MUSIC` step does not get stuck without Ticketmaster forever
- updated the `/:citySlug` landing page desktop hero sizing so the headline and `I'M DOWN` CTA sit inside a centered max-width composition instead of scaling aggressively across wide desktop viewports
- updated the `/:citySlug/vibe` page desktop layout so the headline and 2x2 card grid sit inside a controlled-width container with constrained card heights and calmer desktop emoji scaling
- preserved mobile-first defaults for those pages and left `TonightPage.jsx` untouched in this session
- updated Tonight’s Move refresh cadence so the frontend now explicitly requests `live_music_event_mode` and only asks for a Ticketmaster-backed `LIVE MUSIC` step every fourth `Another Night` refresh
- updated the Tonight page first load to request `ticketmaster_preferred` mode so the initial `LIVE MUSIC` step uses an eligible Ticketmaster music event when available, without requiring four refreshes first
- changed normal Tonight refreshes to rotate standard live-music venues without forcing Ticketmaster event rendering into the numbered `LIVE MUSIC` step
- kept Ticketmaster event rendering only inside the numbered `LIVE MUSIC` step and preserved the removal of any standalone Tonight page “Tonight’s Shows” section
- added admin-only `itinerary_buckets` visibility derived from canonical business `slots`, plus matching admin filters and bucket badges for Dinner, Drinks, Live Music, and Late Night auditing
- added admin-managed featured live music overrides backed by a separate `admin_featured_events` collection, with helper logic that prioritizes an active featured live-music event above Ticketmaster and normal cadence when its active window and local date are valid for tonight
- moved Featured Live Music controls out of the Businesses tab and into a dedicated admin Sponsorships tab
- added admin-managed Tonight’s Move page sponsorships backed by a separate `admin_sponsorships` collection, including active-window and priority resolution plus public itinerary response support via `tonight_move_sponsorship`
- added admin dashboard controls to view, save, activate/deactivate, and clear both Featured Live Music and Tonight’s Move Sponsorship records using `image_url` / `sponsor_logo_url` and `ticket_url` / `sponsor_url` fields without modifying existing business data
- added Tonight page sponsor rendering near the header so active Tonight’s Move sponsorships display independently from the itinerary-selection logic
- hardened `backend/ticketmaster_sync_job.py` for Ticketmaster HTTP 429 rate limiting so cron logs emit `status=rate_limited` plus optional `retry_after`, skip deletes/writes on failed fetches, and exit cleanly instead of surfacing an expected rate limit as a crash
- added one bounded Ticketmaster client backoff path for HTTP 429 using `Retry-After` when present, capped to a short wait so the cron does not hammer the API
- added a new dry-run Google Places discovery script at `backend/discover_ynd_candidates.py` that excludes the current local catalog by `google_place_id` and normalized name/address, scores candidates for Dinner / Drinks / Live Music / Late Night fit, and writes local CSV/JSON reports without touching Mongo
- generated a Nashville discovery report at `backend/discovery_reports/nashville_next_candidates.json` and `.csv` covering ZIP codes `37201`, `37203`, `37204`, `37205`, `37206`, `37207`, `37208`, `37209`, `37210`, `37211`, and `37212`
- added a second-stage curation script at `backend/curate_ynd_candidates.py` that rebuilds the full dry-run candidate pool when needed, applies stronger YND taste filters, assigns curation metadata, and writes balanced `top60`, `maybe`, and `rejected` review files without importing anything
- generated balanced curation outputs at `backend/discovery_reports/nashville_next_candidates_balanced_top60.json`, `.csv`, `..._maybe.csv`, and `..._rejected.csv`; current balanced result lands at `56` candidates with a remaining live-music shortfall of `4`
- kept the safe Ticketmaster alias `Ole Red - Nashville` -> `Ole Red`
- did not add First Horizon Park itinerary matching
- did not add broad aliases for venues missing approved business records
- did not touch cron config, deploy, run migrations, run apply sync, or modify secrets

## Last Known Focus

The immediate focus has shifted from cron verification to customer-facing event correctness:
1. verify the patched `/api/businesses`, `/api/businesses/{id}`, `/api/events/today`, and `/api/itinerary/generate` behavior against the real local/prod-like data shape
2. confirm the numbered `LIVE MUSIC` step on `/:citySlug/tonight?vibe=...` now shows matched Ticketmaster music events, formatted show times, and Ticketmaster purchase CTAs without a separate standalone shows section
3. design a schema/data cleanup for event-like business rows so today/tonight public suppression can become generic and data-driven without relying on business names
4. keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or rules change
5. after event-surface verification, return to the backend-local cron entrypoint validation and later Railway cron service creation only after Blake approves that infra step
6. after the Ticketmaster/event correctness work, plan first-party admin auth replacement and a storage replacement path so Emergent can be removed safely
7. fix desktop responsiveness on the landing page and vibe selection page without redesigning the Tonight’s Move results page or altering backend logic

## Prior Session Notes

Before this cron-entrypoint update, the repo had local-only tooling prepared for Emergent-image cleanup, Google photo refresh support, and admin-triggered Ticketmaster sync support. That work is now partially reflected in production outcomes:
- the 7 approved Emergent-hosted image records were safely backfilled
- the 3 exception records remain intentionally unresolved pending later review
- the Railway photo refresh cron exists and the backend is healthy
- manual Ticketmaster apply sync in production is now verified successful

Verification completed in this local patching session:
- `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract` passed (`45` tests)
- Python AST parse check passed for `backend/server.py` and `backend/ticketmaster_events.py`
- after the Tonight-flow patch, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract` passed again (`49` tests)
- after the Live Music step correction, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract` passed (`57` tests)
- after the Another Night exhaustion fix, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract` passed again (`59` tests)
- after the live-music cadence plus admin bucket audit update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract backend.tests.test_itinerary_buckets_unit backend.tests.test_admin_dashboard_contract` passed (`66` tests)
- after the first-load Ticketmaster preference plus admin featured live music override update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_featured_live_music_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract backend.tests.test_itinerary_buckets_unit backend.tests.test_admin_dashboard_contract` passed (`74` tests)
- after the admin Sponsorships tab plus Tonight’s Move sponsorship update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_featured_live_music_unit backend.tests.test_tonight_move_sponsorship_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract backend.tests.test_itinerary_buckets_unit backend.tests.test_admin_dashboard_contract` is the required rerun target
- after the Ticketmaster cron rate-limit hardening update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_ticketmaster_sync_job_unit backend.tests.test_ticketmaster_sync_endpoint_unit` passed (`72` tests)
- `python3 backend/discover_ynd_candidates.py --report-template` passed locally and a full dry-run report was generated via Google Places without writing to Mongo
- `python3 backend/curate_ynd_candidates.py --allow-refresh` rebuilt the full candidate pool from Google Places and generated the balanced curation review files without writing to Mongo

Unverified in this local patching session:
- frontend Jest was not runnable locally because workspace JS dependencies are not installed and `craco` is unavailable on PATH
- frontend build/lint was not runnable locally because `frontend/node_modules` is missing and neither `craco` nor `react-scripts` is available in the workspace
- no browser/manual QA was run here
- no production changes were made
- `python3 -m py_compile backend/ticketmaster_events.py backend/ticketmaster_sync_job.py` was not a useful validation signal locally because macOS Python cache writes are blocked in this sandbox (`PermissionError` under `~/Library/Caches/com.apple.python`)
