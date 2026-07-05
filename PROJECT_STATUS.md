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
- updated the Live Music category UI to derive “Tonight’s Shows” from matched venue events instead of a separate city-wide `/events/today` fetch
- updated Live Music business cards and Tonight’s Move cards to show event title, show date/time, and a `Buy Tickets` button when `ticket_url` exists
- removed the temporary name-based suppression for event-like business rows because it was not generic or data-driven enough to keep
- identified follow-up schema/data work still needed if those rows should be hidden from today/tonight public business discovery without relying on names
- kept the safe Ticketmaster alias `Ole Red - Nashville` -> `Ole Red`
- did not add First Horizon Park itinerary matching
- did not add broad aliases for venues missing approved business records
- did not touch cron config, deploy, run migrations, run apply sync, or modify secrets

## Last Known Focus

The immediate focus has shifted from cron verification to customer-facing event correctness:
1. verify the patched `/api/businesses`, `/api/businesses/{id}`, `/api/events/today`, and `/api/itinerary/generate` behavior against the real local/prod-like data shape
2. confirm the Live Music page now shows matched venue events, show times, and Ticketmaster purchase CTAs instead of generic city-wide events
3. design a schema/data cleanup for event-like business rows so today/tonight public suppression can become generic and data-driven without relying on business names
4. keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or rules change
5. after event-surface verification, return to the backend-local cron entrypoint validation and later Railway cron service creation only after Blake approves that infra step
6. after the Ticketmaster/event correctness work, plan first-party admin auth replacement and a storage replacement path so Emergent can be removed safely

## Prior Session Notes

Before this cron-entrypoint update, the repo had local-only tooling prepared for Emergent-image cleanup, Google photo refresh support, and admin-triggered Ticketmaster sync support. That work is now partially reflected in production outcomes:
- the 7 approved Emergent-hosted image records were safely backfilled
- the 3 exception records remain intentionally unresolved pending later review
- the Railway photo refresh cron exists and the backend is healthy
- manual Ticketmaster apply sync in production is now verified successful

Verification completed in this local patching session:
- `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract` passed (`45` tests)
- Python AST parse check passed for `backend/server.py` and `backend/ticketmaster_events.py`

Unverified in this local patching session:
- frontend Jest was not runnable locally because workspace JS dependencies are not installed and `craco` is unavailable on PATH
- no browser/manual QA was run here
- no production changes were made
