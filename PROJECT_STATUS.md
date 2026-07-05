## Current State

You're Not Down is Blake's nightlife and tourist discovery product focused on helping visitors quickly decide what to do tonight, with Nashville as the first market. The intended product shape remains lightweight and conversion-focused: hotel QR distribution, simple itinerary generation, and fast 1 to 4 step plans for tourists choosing bars, restaurants, and local activities.

The repo is currently on branch `main`. The only known worktree changes outside this documentation update are two unrelated untracked migration files: `migrations/copy_catalog_collections.py` and `migrations/import_via_production_admin_api.py`. They remain untouched.

## Latest Work Session

The immediate Ticketmaster production verification step is complete, and the current local follow-up is a production-safe Railway cron entrypoint that can run the sync non-interactively without using the admin HTTP endpoint.

Verified production Ticketmaster manual apply sync result:
- apply sync returned `STATUS 200`
- `fetched=13`
- `after_dedupe=12`
- `would_upsert=12`
- `matched=5`
- `unmatched=7`
- `upserted=12`
- `/api/events/today?city=nashville` now returns `count=4`, `matched=1`, `unmatched=3`
- cancelled/off-sale filtering appears to work
- `Ole Red - Nashville` alias works and the Ole Red event is matched
- `First Horizon Park` and `Grand Ole Opry House` remain intentionally unmatched

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
- added the safe Ticketmaster alias `Ole Red - Nashville` -> `Ole Red`
- did not add First Horizon Park itinerary matching
- did not add broad aliases for venues missing approved business records
- added a backend-local `backend/ticketmaster_sync_job.py` Railway cron entrypoint that reads `MONGO_URL`, `DB_NAME`, and `TICKETMASTER_API_KEY`, defaults to `city=nashville` and `days=2`, applies by default, supports `--dry-run`, prints a safe summary, and exits non-zero on failure

## Last Known Focus

The immediate focus has shifted from one-off manual sync verification to safe repeatability on Railway:
1. syntax-check and unit-test the new backend-local Ticketmaster cron entrypoint
2. later create the Railway cron service with the approved command only after Blake approves that step
3. run the new cron entrypoint in `--dry-run` mode first on Railway or equivalent safe environment and confirm the summary/log shape
4. after that, allow the intentional apply-mode cron run and verify `city_events` counts plus `/api/events/today?city=nashville`
5. continue to leave `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or rules change
6. after the Ticketmaster/cron work, plan first-party admin auth replacement and a storage replacement path so Emergent can be removed safely
7. later resolve the remaining 3 intentionally untouched image records and the outbound IP follow-up if still open

## Prior Session Notes

Before this cron-entrypoint update, the repo had local-only tooling prepared for Emergent-image cleanup, Google photo refresh support, and admin-triggered Ticketmaster sync support. That work is now partially reflected in production outcomes:
- the 7 approved Emergent-hosted image records were safely backfilled
- the 3 exception records remain intentionally unresolved pending later review
- the Railway photo refresh cron exists and the backend is healthy
- manual Ticketmaster apply sync in production is now verified successful

No production changes were made in this local patching session.
