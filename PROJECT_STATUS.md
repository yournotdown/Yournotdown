## Current State

You're Not Down is Blake's nightlife and tourist discovery product focused on helping visitors quickly decide what to do tonight, with Nashville as the first market. The intended product shape remains lightweight and conversion-focused: hotel QR distribution, simple itinerary generation, and fast 1 to 4 step plans for tourists choosing bars, restaurants, and local activities.

The repo is currently on branch `main`. The only known worktree changes outside this documentation update are two unrelated untracked migration files: `migrations/copy_catalog_collections.py` and `migrations/import_via_production_admin_api.py`. They remain untouched.

## Latest Work Session

The Railway production cutover is complete, and the current backend patch focus is Ticketmaster/event correctness before any apply sync.

Verified production state:
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

Operational constraints preserved in this session:
- no deploy
- no merge
- no delete
- no migrations run
- no staging or commit
- no Ticketmaster apply sync

Latest local patch state:
- added shared city-event eligibility logic for public event reads and itinerary event attachment
- excluded `cancelled`, `canceled`, and `offsale` event statuses from public/today eligibility
- added same-day stale filtering with a configurable grace window via `EVENT_START_GRACE_MINUTES` defaulting to 60
- kept `local_time == null` events eligible for now unless status is excluded
- added the safe Ticketmaster alias `Ole Red - Nashville` -> `Ole Red`
- did not add First Horizon Park itinerary matching
- did not add broad aliases for venues missing approved business records

## Last Known Focus

The immediate focus has shifted from cutover work to production data quality and event correctness:
1. verify the new Ticketmaster/event eligibility patch locally
2. verify production behavior after a future approved deploy, without running apply sync yet
3. then decide whether to run a one-time Ticketmaster apply sync
4. later review admin event controls and any additional venue matching work
5. later resolve the remaining 3 intentionally untouched image records and the outbound IP follow-up if still open

## Prior Session Notes

Before this verification update, the repo had local-only tooling prepared for Emergent-image cleanup and Google photo refresh support. That work is now partially reflected in production outcomes:
- the 7 approved Emergent-hosted image records were safely backfilled
- the 3 exception records remain intentionally unresolved pending later review
- the Railway photo refresh cron exists and the backend is healthy

No production changes were made in this local patching session.
