## Immediate Follow-Up

0. Use `docs/production/monitoring_and_alerting_runbook.md` as the launch-watch baseline:
   - confirm the exact Railway, Mongo, Resend, Ticketmaster, and admin dashboards Blake wants open during launch
   - keep the 30 to 60 minute watch cadence during the first real traffic push

0. Decide whether to implement a very small logging-only follow-up before launch for the gaps documented in the runbook:
   - itinerary generation failure logging
   - saved-itinerary Resend failure logging
   - owner-invite email failure logging
   - Hotel QR admin write failure logging
   - if done, keep it narrow and operational only with no behavior changes

0. Manually QA the new write-rate limits after the next deploy:
   - confirm normal app usage does not trip limits for `analytics/track` or `itinerary/generate`
   - confirm repeated `itinerary/save` abuse attempts return a clean `429` with no save-email crash path
   - confirm repeated owner-invite attempts return `429` before spamming Resend
   - confirm repeated Hotel QR create/update/deactivate/delete attempts return `429` cleanly
   - confirm a `business/claim` spam burst is throttled without breaking a normal one-time claim flow

0. If production ends up running multiple backend instances, replace the current in-process limiter with a shared store:
   - Redis or equivalent
   - preserve the same bucket names and limits as the baseline unless real traffic suggests tuning
   - keep hashed subject keys so raw IP/email values are still not stored in limiter state

0. Manually QA the admin session transition after the next deploy:
   - confirm a fresh admin login still succeeds through the existing `/api/auth/session` flow
   - confirm `/api/auth/me` succeeds with the new hashed admin session rows
   - confirm `Logout` clears the admin session cleanly
   - if any legacy raw admin sessions still exist, confirm they either upgrade cleanly on first authenticated request or fail cleanly with a re-login prompt
   - confirm business-owner login/session behavior is unchanged and still separate from admin auth

0. If the backend moves behind `api.yournotdown.com`, re-run admin session QA specifically in Safari and mobile browsers:
   - confirm the `Secure` / `HttpOnly` / `SameSite=None` admin cookie still sticks correctly
   - confirm login/logout behavior remains stable across the same-site custom-domain setup

0. Manually QA the updated admin `Analytics` top cards after the next deploy:
   - confirm the cards read clearly as:
     - `Total Visits`
     - `Unique Visitors`
     - `Returning Visitors`
     - `Returning Visitor Rate`
   - confirm `7d`, `30d`, `90d`, and `All time` update those totals correctly
   - confirm usage cards reflect `homepage_visit` traffic and stored `visitor_id` values rather than IP-based counts
   - confirm the lower leaderboards still respect the vibe and slot filters

0. Manually QA the updated admin `Hotel QR` output after the next deploy:
   - confirm the preview QR renders white on black in the admin table
   - confirm `Download QR` saves a white-on-black PNG
   - confirm the downloaded PNG still scans reliably on iPhone and Android camera flows
   - confirm `Copy URL`, `Deactivate`, and `Delete` behavior is unchanged

0. If Blake approves the latest production-readiness P0D tooling/docs pass, run the new harness locally first:
   - `python3 scripts/load_test_ynd.py --target http://localhost:8000 --users 10 --concurrency 10 --duration 60 --ramp-up 10 --city nashville --vibe down`
   - confirm the script refuses `yournotdown.com` targets unless `--allow-production` is passed
   - confirm the output includes total requests, success/failure counts, average latency, p95, p99, and grouped endpoint/status errors
0. Before any production smoke test, use the staged plan in `docs/production/load_test_plan.md`:
   - local correctness first
   - non-production/staging traffic ramp next
   - tiny production smoke only (`1-5` users, `30s`, save disabled) and only with explicit approval
0. Keep `/api/itinerary/save` disabled for the first production smoke:
   - avoid unnecessary Resend traffic
   - avoid testing email volume before the read-heavy path is understood
   - if save testing is ever enabled later, use a dedicated test inbox only and keep concurrency very low
0. The new harness intentionally does not cover image bandwidth, browser asset loading, or admin flows:
   - if launch confidence later requires image-heavy or frontend-render pressure, plan that as a separate controlled pass instead of broadening the first API harness
0. Use the new load-test tooling only after the already-landed hardening passes are present in the target environment:
   - P0A Mongo indexes/query hardening
   - P0B image/bandwidth optimization
   - P0C admin analytics query hardening
   - then compare Railway/Mongo metrics stage by stage instead of jumping directly to a 500-user run

0. If Blake approves the latest `Run It Back` repeat-prevention pass, manually QA Tonight’s Move rerolls after deploy:
   - confirm a business seen in `Dinner` does not reappear in `Dinner` during the same page session until the slot pool is exhausted
   - confirm the same rule holds for `Drinks`, `Entertainment` fallback businesses, and `Late Night`
   - confirm locked cards remain fixed while only unlocked slots reroll
   - confirm exhausting a small slot pool gracefully allows a repeat only after the unseen slot history is exhausted
0. Specifically QA the preserved Ticketmaster exception path after deploy:
   - first load still prefers Ticketmaster when eligible
   - every fourth `Run It Back` still requests Ticketmaster mode
   - Ticketmaster event rotation still uses event-id exclusion behavior rather than the new business slot-history rule
0. If future UX tuning is needed, decide whether same-session repeat prevention should eventually persist across full page reloads via `sessionStorage`; this pass intentionally keeps it in the current page/session state only and does not write reroll history to Mongo

0. If Blake approves the latest production-readiness P0B pass, manually QA image delivery after deploy:
   - inspect a real Tonight’s Move session in DevTools and confirm Google-photo requests now carry bounded `max_width` values instead of always using the default full-size proxy path
   - verify the first Tonight image still looks sharp enough while lower-priority/admin thumbnails request visibly smaller image payloads
   - confirm no regressions in business-photo rendering on Tonight, category detail, admin business list, and per-business analytics pages
0. Confirm the new longer cache headers are actually honored in the production path for:
   - `/api/google-places/photo`
   - `/api/files/{path}`
   - if Railway or any edge layer ignores them, the next infra step should be a dedicated CDN/front-cache decision rather than more frontend tweaks
0. P0B reduced bandwidth pressure, but it did not remove Railway from the image path:
   - Google Places images still proxy through the backend because the key must stay server-side
   - uploaded object-storage images still proxy through `/api/files`
   - if launch monitoring shows image traffic is still the primary bottleneck, the next deeper follow-up is CDN/direct-public-asset work rather than more card-level styling changes
0. Before claiming 500-user readiness, include image-heavy traffic in the future controlled load test:
   - Tonight page with 4 business images
   - category detail cards
   - a small admin image mix
   - capture Railway outbound bandwidth plus request concurrency, not just API latency

0. If Blake approves the latest production-readiness P0A pass, manually inspect Mongo/railway behavior after deploy:
   - confirm startup maintenance completes instead of deferring
   - confirm no index-creation error appears for any newly indexed collection
   - sanity-check that `GET /api/admin/audience` loads faster and no longer needs to scan the entire `visitor_profiles` collection
0. Use the new startup-managed indexes as the baseline before any future controlled load test:
   - verify the hot-path collections now show the expected indexes in Mongo Atlas
   - if Atlas metrics still show slow scans on `analytics_events`, `businesses`, or `saved_itineraries`, capture the exact query shapes before changing behavior further
0. Next production-readiness follow-up after P0A should stay focused on the remaining audit P0s:
   - image/proxy pressure from the Google Places photo pass-through
   - broader `/api/itinerary/generate` read cost under spike traffic
   - admin analytics and Hotel QR query weight on larger event volumes
   - admin auth/session hardening called out in the production audit
0. Before any real 500-user confidence claim, run a controlled non-production load test against the indexed build:
   - warm `/api/itinerary/generate`, `/api/analytics/track`, and `/api/itinerary/save`
   - include a smaller admin read mix for `/api/admin/audience` and `/api/admin/hotel-qr`
   - capture p50/p95 latency plus Mongo CPU/IO rather than guessing from unit tests

0. If Blake approves the latest vibe-card typography polish, manually QA the Vibe page after deploy:
   - confirm `See Where It Goes` and `Make It Count` keep clear spacing between words on mobile and desktop
   - confirm the cards still feel premium and balanced with the emoji-first layout
   - confirm no regressions in the two-column card grid or hover/tap behavior

0. If Blake approves the latest vibe-label pass, manually QA the public copy after deploy:
   - confirm the vibe picker shows `Take It Easy`, `See Where It Goes`, `Make It Count`, and `No Regrets`
   - confirm Tonight's Move `Curated for` copy uses the new labels while the URL/query slugs still remain `just-vibing`, `down`, `very-down`, and `send-it`
   - confirm the saved-itinerary email uses `See Where It Goes` / `Make It Count` instead of the old `Let's ...` phrasing
   - confirm admin vibe filters and vibe tables show the new friendly wording rather than raw slugs
0. There is still no editable hotel placard design source in the repo; if Blake wants a printable placard next, use `docs/hotel-qr/placard_copy.md` as the approved copy baseline for design work.

0. Manually QA the simplified admin `Audience` tab after the next deploy:
   - confirm the five main cards read clearly as:
     - `Email Captures`
     - `Marketing Opt-ins`
     - `Saved Moves`
     - `Returning Visitor Rate`
     - `Repeat Savers`
   - confirm the page still handles empty data with a clean `No email captures yet.` state
   - confirm a failed `/api/admin/audience` response shows the inline error banner instead of crashing the page
   - confirm the table/search/filter behavior is unchanged
0. Manually QA the new `Hotel QR` admin tab after the next deploy:
   - create a QR code such as `The Russell Lobby`
   - confirm the generated destination URL uses `https://www.yournotdown.com?qr=<slug>`
   - confirm create no longer fails with a JSON/ObjectId response serialization error
   - confirm `Copy URL` works
   - confirm QR previews render
   - confirm `Download QR` saves a usable PNG
   - confirm deactivate flips the placement inactive without deleting history
   - confirm delete removes the QR from the admin list after confirmation but leaves historical analytics untouched
0. Manually QA end-to-end Hotel QR attribution after the next deploy:
   - open the public site with a real `?qr=<slug>` URL
   - confirm the root homepage URL redirects into Nashville without losing the `qr` param
   - confirm one `hotel_qr_scan` is recorded for the session
   - confirm later `homepage_visit`, `vibe_click`, `itinerary_view`, `step_locked`, and `save_itinerary` activity inherit the same `qr_slug`
   - save a locked move and confirm the Hotel QR row reflects scans, lock clicks, saved moves, email captures, and marketing opt-ins
0. There are no existing hotel QR placard/card design assets in the repo today, so the safer next step is:
   - keep admin QR download separate from placard design for now
   - place the downloaded QR into a manually designed hotel placard/card once the print layout is approved
   - only build `Download Placard` after Blake locks the real placard format, copy, and brand treatment
0. Decide whether `PATCH /api/admin/hotel-qr/{id}` should keep the slug stable on future metadata edits or intentionally regenerate it when the placement name changes; the current implementation regenerates the slug when `name` changes.

0. Manually QA the Tonight's Move card CTA hierarchy after the next deploy:
   - confirm `Lock This In` is visually dominant on unlocked cards
   - confirm Website, Directions, Call, and Buy Tickets remain usable but clearly secondary
   - confirm locked cards still show an active lime `Locked in` state with a secondary `Unlock` action
0. Manually QA the renamed Tonight's Move reroll CTA after the next deploy:
   - confirm the button now reads `Run it back.`
   - confirm the reroll behavior is unchanged
   - confirm any event logging still uses the existing `another_night_click` backend/frontend naming
0. Manually QA the repaired admin `Audience` tab after the next deploy:
   - confirm the tab no longer blanks when opening Audience
   - confirm a failed `/api/admin/audience` request shows the new inline error state instead of crashing the page
   - confirm empty-data cases still show `No email captures yet.` cleanly
   - confirm the new/returning visitor stat cards render even when some totals are missing
0. Manually QA the refined Tonight's Move sponsor badge:
   - confirm it still sits beside or just under `MOVE`, never above the headline
   - confirm the slimmer pill reads clearly on desktop and mobile
   - confirm sponsor logo + name spacing feels premium and not cramped
0. Manually QA the new all-time visitor-stickness layer in the admin `Audience` tab:
   - confirm a first-time browser/device appears as a `New` visitor after its first tracked event/save
   - confirm the same browser/device becomes `Returning` after subsequent tracked events or another saved move
   - confirm repeat saver counts increase when the same visitor/email saves multiple locked itineraries
   - confirm saves without a `visitor_id` still work and show `Unknown` visitor status without crashing the table
0. Decide whether the Audience tab should eventually support date-range-aware new/returning visitor stats; this chunk intentionally kept visitor stickiness all-time only.
0. Decide whether future reporting should merge multiple visitor ids by normalized email after enough real traffic is observed; this chunk intentionally does not merge visitor profiles by email.
0. Manually QA the new admin `Audience` tab after the next deploy:
   - save a locked Tonight's Move once without checking the marketing box and confirm the contact appears as `Not opted in`
   - save again with the same email and the marketing box checked and confirm the same contact record is reused, `saved_itinerary_count` increments, and opt-in flips to `true`
   - confirm a later save without the box checked does not turn `marketing_opt_in` back to `false`
   - verify search by email and the `All` / `Marketing opted in` / `Not opted in` filters
0. Decide whether the admin audience section needs a lightweight CSV export in a future chunk; it was intentionally left out here to keep the first pass low-risk.
0. Decide whether `recent captures` should stay on a rolling 7-day definition or become date-range aware once the audience tab gets broader filtering.
0. If outbound marketing is added later, build it on top of `audience_contacts` and `unsubscribed_at` rather than repurposing `saved_itineraries`.
0. After the next deploy, verify the admin revoke flow specifically:
   - owner panel flips to `Portal inactive`
   - owner email display becomes `—`
   - invite status becomes `Invite none`
   - a fresh invite to the same email works again
0. Before expecting the business-owner portal to work reliably across Safari/mobile browsers, put the backend behind a same-site custom domain such as `api.yournotdown.com`, then point the frontend `REACT_APP_BACKEND_URL` at that domain and re-run the fresh invite QA for `lansingblake@gmail.com`.
0. After the next owner-access deploy, send a fresh invite to `lansingblake@gmail.com` and confirm:
   - the admin panel clears owner email / pending invite state immediately after revoke
   - reopened invite links fail cleanly after revoke
   - `/business/dashboard` loads on the intended browser after claim
0. After the business-owner hotfix deploy, send a fresh invite to `lansingblake@gmail.com` for `The End` and manually verify:
   - invite email no longer contains `MVP`
   - claim link succeeds end to end
   - `/business/dashboard` loads with the owner session instead of `Not authenticated`
   - reopening the consumed invite fails cleanly
   - revoking owner access kills `/api/business/me` and `/business/dashboard`
0. Manually QA the latest frontend polish before any deploy approval:
   - confirm the browser tab favicon is the new YND lime-on-black mark instead of the generic globe
   - confirm Tonight's Move sponsorship no longer renders above the headline
   - confirm the sponsor badge now sits beside or directly under `MOVE`, reads clearly, and feels larger/premium on desktop and mobile
0. Manually QA the new business-owner invite flow before any deploy approval:
   - open an existing business in the admin edit modal and confirm the Business Owner Access section loads
   - send an invite with Resend configured and confirm the email arrives with the claim link
   - send an invite without Resend configured and confirm the UI reports the honest `provider_unconfigured` state
   - claim the link and confirm `/business/dashboard` loads with only that business context
   - revoke owner access and confirm the existing owner session can no longer reach `/api/business/me`
1. Build Chunk D on top of the new owner session scaffold rather than inventing a second auth model:
   - richer owner dashboard tables/charts
   - vibe/category breakdowns
   - better empty/error states
   - owner logout / session UX if Blake wants it
2. Decide whether business-owner sessions should stay at `30` days or be shortened before production launch; the current scaffold chose a separate long-lived owner cookie for MVP convenience.
3. If Blake wants resend/reissue behavior later, add a dedicated “resend invite” control on top of the existing `owner-invite` endpoint semantics rather than creating a separate invite model.

4. Manually QA the upgraded admin analytics tab before any deploy approval:
   - switch between `7d`, `30d`, `90d`, and `All time` and confirm leaderboard/card totals update
   - apply vibe and slot filters and confirm the category-winner tables, sponsor performance rows, and top-business tables update consistently
   - confirm older analytics records without `slot` do not crash the page and simply fall out of slot-specific leaderboards
   - confirm the per-business analytics page now shows Locked In, Saved in Final Move, Buy Tickets, and Total Engagement
5. Decide whether the admin analytics tab should eventually expose a city filter in the UI once non-Nashville markets are live; the backend summary endpoint now has room for city-scoped filtering later.
6. If Blake wants deeper sponsor reporting later, the next safe extension is a dedicated `/api/admin/analytics/leaderboards` endpoint or CSV export rather than adding more rendering complexity to the current summary payload.

7. Manually QA the new sponsor-grade analytics events in a browser session before any deploy approval:
   - lock a Tonight's Move card and confirm a `step_locked` event is created only on the lock click, not on rerenders or unlock
   - click `Buy Tickets` from a Tonight entertainment card and confirm `ticket_click` now carries business/event context
   - save a final locked itinerary and confirm each saved step writes a `saved_itinerary_business` analytics event without breaking the save-email flow
   - inspect admin/business analytics responses for the new `step_locked`, `saved_itinerary_business`, `ticket_click`, and `total_engagement` totals
8. If Blake wants the admin analytics UI expanded next, build it on top of the new backend fields instead of adding new event types again:
   - leaderboard tables for top locked-in businesses, top ticket-click businesses, and top total-engagement businesses
   - optional date-range, vibe, and slot filters once the UI shape is approved
9. Before business-owner-facing sponsor reporting, decide whether `Locked In` should mean:
   - every `step_locked` click
   - every business present in a fully saved final move
   - or both as separate metrics
10. If the old pytest-based backend integration suite needs to run again, remember it still targets `https://whatsyoudown.preview.emergentagent.com` via `backend/tests/test_config.py`; the latest failure was preview DNS resolution, not a meaningful application assertion.

11. Manually QA `/:citySlug/tonight?vibe=...` for the new lock flow:
   - lock dinner/drinks/late-night individually and confirm only unlocked slots reroll
   - lock `entertainment` and confirm the same live-music/Ticketmaster card and event details persist across `Another Night`
   - confirm every-4th `Another Night` still requests Ticketmaster only when `entertainment` is unlocked
12. Manually QA the new `You're Locked In` overlay on `/:citySlug/tonight?vibe=...`:
   - confirm it auto-opens only after all 4 steps are locked
   - confirm `Keep editing` closes it without unlocking cards
   - confirm unlocking any step prevents immediate reopen until all 4 are locked again
   - confirm clicking `Another Night` from the bottom of the page scrolls smoothly back to the top only after the refreshed itinerary is visible
   - confirm valid email submission shows `Sent — check your email.` when Resend env vars are configured
   - confirm valid email submission shows the honest `provider_unconfigured` message when Resend env vars are absent
   - confirm a forced provider failure path shows `Saved, but the email could not be sent. Try again.`
   - confirm invalid email shows `Enter a valid email.`
   - confirm the premium email renders cleanly on iPhone Mail, Gmail mobile, and desktop Gmail/Apple Mail, including the neon-lime wordmark fallback, numbered cards, action buttons, and friendly event times
3. If Blake wants this live in Railway, configure:
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`
   - optional `RESEND_REPLY_TO`
   - optional `PUBLIC_SITE_URL` or `FRONTEND_PUBLIC_URL`
4. After Railway env vars are configured, manually verify a real end-to-end transactional email from `/api/itinerary/save` before any deploy approval:
   - confirm subject `Your Tonight’s Move is locked in`
   - confirm preheader `Nashville is set. Here’s your locked-in move.`
   - confirm the updated `YND / EST. 26` header renders cleanly across inboxes and the neon-lime divider is visible without image blocking issues
   - confirm raw vibe slugs and raw `HH:MM:SS` event times are no longer visible
5. Treat `frontend/package-lock.json` as the intended install baseline going forward; use `cd frontend && npm install` for reproducible local/frontend CI setup and avoid falling back to ad hoc AJV patching.

## Top 5 Next Tasks

1. Manually QA the new bounded admin reporting behavior before any deploy approval:
   - confirm `Admin -> Audience` loads the first page, then `Previous` / `Next` paging works with real data
   - confirm changing Audience search or opt-in filters resets the table back to page 1
   - confirm `Admin -> Analytics` still shows the expected leaderboards and category/vibe summaries under the default 30-day window
   - confirm `Admin -> Hotel QR` still shows QR analytics rows and QR controls with the new default 30-day analytics window
2. If admin reporting still feels heavy on production-like data, the next safe hardening step is to add explicit date controls to `Hotel QR` and possibly a capped `Load More` or server-side search for the `by_business` analytics table instead of widening all-time payloads.
3. Manually QA the repaired Ticketmaster `Run It Back` flow in a browser before any deploy approval:
   - confirm a first-load Ticketmaster entertainment card can be followed by repeated `Run It Back` clicks without ever showing `Couldn't plan tonight. Try again.`
   - confirm Ticketmaster misses now fall back cleanly to normal live-music/entertainment businesses instead of breaking the whole itinerary
   - confirm same-session slot-history exhaustion still relaxes only historical excludes and still returns a full itinerary
4. Manually QA live-music Ticketmaster variety in production-like browser sessions now that the picker uses the full matched event pool:
   - verify first-load `ticketmaster_preferred` can surface more than Basement/Basement East when multiple same-day matched venues exist
   - verify every-fourth `Run It Back` in entertainment can rotate across venues like `Brooklyn Bowl Nashville`, `Ryman Auditorium`, `The East Room`, and `The Bluebird Cafe`
   - verify Ticketmaster event-id exclusions still prevent immediate repeat-show loops while allowing later fallback if the pool is exhausted
5. Decide how to resolve the catalog/data gap for `Grand Ole Opry House`:
   - there is still no approved canonical Opry business record to map that Ticketmaster venue onto
   - no alias was added in code because mapping to a missing target would be unsafe
6. Audit and eventually clean duplicate approved live-music venue rows that were observed during the read-only Ticketmaster investigation:
   - `Ryman Auditorium`
   - `The Basement East`
   - duplicate cleanup is still deferred; current code only makes the matching deterministic
7. If Ticketmaster venue coverage still feels narrow after manual QA, expand the safe venue alias map with additional real Nashville mismatches found in production data instead of changing the same-day event scope:
   - continue preferring explicit curated aliases over fuzzy matching
   - keep sports/baseball exclusions and current classification rules unchanged
8. If Blake wants broader live-music diversity after the current picker fix is verified, consider a second pass that adds weighted/randomized Ticketmaster pair selection tuning or stronger venue rotation memory without changing first-load cadence or tomorrow-event scope.
9. Review `backend/discovery_reports/nashville_take_it_easy_supplement_candidates.json`, `.csv`, and `..._report.txt`; the dry-run supplement recommends `20` additional Nashville candidates for `Take It Easy` and would likely move `just_vibing` from `15` to roughly `25-35` if a later import only approved the strongest fits.
10. Use `backend/discovery_reports/nashville_take_it_easy_supplement_human_review.csv` and `..._human_review_report.txt` for Blake review before any import-ready work:
   - current strict split: `10 approve`, `5 maybe`, `5 reject`
   - safest current approvals: `Park Cafe`, `The Cookery`, `Lockeland Table`, `Caffe Nonna`, `Epice`, `Once Upon A Time In France`, `Koré`, `Sirocco`, `ButterFLY Garden Brunch`, and `Germantown Café`
   - highest-risk rows needing caution: `The Chloe Nashville Restaurant & Bar`, `Chateau West`, `Sadie's`, `Peninsula`, `Milk & Honey Gulch`, `Frothy Monkey`, `1 Kitchen`, `Bungalow 10 Dining`, and `Twenty First`
11. Use `backend/discovery_reports/nashville_take_it_easy_approved_10_import_ready_enriched.json`, `.csv`, and `..._enrichment_report.txt` as the current approved-only enriched dry-run import package:
   - final count: `10`
   - duplicate checks against the `v5` deduped catalog are clean by `google_place_id`, exact name, normalized name, and normalized name+address
   - core Business-schema validation is clean
   - websites found: `10/10`
   - photo sets found: `10/10`
12. If Blake approves a future production-safe database dry-run for the Take It Easy 10, use `backend/import_nashville_take_it_easy_approved_10.py` against the enriched package first:
   - default mode is dry-run
   - real inserts require `--apply --confirm IMPORT_NASHVILLE_TAKE_IT_EASY_10`
   - it inserts only non-duplicates into `db.businesses`
   - it does not update or delete existing rows
5. If Blake wants a cleaner future import-ready Take It Easy batch, only promote approved rows first and revisit the `maybe` set after manual atmosphere/brand review; do not pull rejected generic-risk rows back in without new evidence.
6. Review `backend/discovery_reports/nashville_vibe_affinity_backfill_preview_v5.json`, `.csv`, `..._report_v5.txt`, and `..._manual_review_v5.csv`; the fifth pass fixes the duplicate/example integrity issue and lands `65 down`, `64 very_down`, `25 send_it`, `15 just_vibing` after collapsing same-venue duplicates to `169` scored businesses, but it still misses the requested `just_vibing` floor.
7. If another vibe pass is needed before schema/runtime work:
   - move roughly `3-5` more calm dinner-only rows into `just_vibing`
   - preserve the current duplicate-collapsing integrity layer and unique example generation
   - keep `send_it` near `25-35`; `v5` is now on target there
   - preserve the narrow event/sports guard so only intended rows stay flagged (`Nissan Stadium`, `Bridgestone Arena`, `CMA Fest`, `Live On The Green`, `Geodis Park`, `Tomato Art Fest`)
   - decide whether `Old Glory` should also be collapsed as the same venue despite the unit-number address difference, and whether `The Patterson House` truly represents one venue or two conflicting source rows
8. Manually verify in production-like browser QA that the `TonightPage.jsx` temporal-dead-zone crash is gone on `/:citySlug/tonight?vibe=...` and the `/:citySlug/vibe` flow no longer lands on a blank page.
9. Manually verify the patched public event surfaces with real data:
   - `/api/itinerary/generate`
   - `/api/events/today?city=nashville`
   - `/:citySlug/tonight?vibe=send-it`
   - the “Another Night” refresh flow on the Tonight page
10. Confirm the revised `LIVE MUSIC` precedence on the Tonight page feels right in production-like QA:
   - active admin featured live music event overrides everything
   - active Tonight’s Move sponsorship renders near the Tonight page hero without affecting itinerary selection
   - first load uses Ticketmaster when eligible and no featured override exists
   - normal refreshes rotate standard live-music venues
   - every fourth `Another Night` requests a Ticketmaster-backed live-music step
   - Ticketmaster mode rotates when possible and safely recycles when the eligible pool is exhausted
11. Use the new admin Sponsorships tab plus itinerary bucket chips/filters to audit paid/event promotion behavior and identify polluted/event-like catalog rows that still need cleanup.
12. Manually QA the new Sponsorships admin tab:
   - Featured Live Music control is no longer inside Businesses
   - Tonight’s Move Sponsorship save/activate/clear flow works
   - active sponsor name/link/tagline render cleanly on `/:citySlug/tonight?vibe=...`
13. Manually QA the desktop and tablet layouts for `/:citySlug` and `/:citySlug/vibe` at 1440px, 1728px, tablet, and mobile widths to confirm the landing hero and 2x2 vibe grid now feel intentional without regressing mobile.
   - specifically confirm `/nashville/vibe` shows all 4 vibe cards above the fold on a standard desktop viewport without feeling cramped, including shorter browser heights around 900px
14. Define and implement a schema/data cleanup for event-like catalog rows so future public suppression can be generic and data-driven instead of name-based.
15. If frontend regression testing is needed locally, install the frontend JS dependencies first so `craco test` and `craco build` can run; current workspace does not have `craco` or `react-scripts` available.
16. Keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or explicit mapping rules change.
17. Validate the new Ticketmaster cron 429 behavior in production-like logs:
   - expected rate limits should print `status=rate_limited`
   - `retry_after` should appear when Ticketmaster sends it
   - no expired-event cleanup should run on a rate-limited fetch
   - normal successful sync output should remain unchanged
18. Decide whether a minimum successful-sync interval guard is worth adding to the cron path via a lazy `sync_state` collection; keep dry-run behavior unblocked and avoid changing manual admin workflows without explicit approval.
19. After the event-surface verification work, return to the backend-local `ticketmaster_sync_job.py` validation and only later create or adjust Railway cron service behavior after Blake explicitly approves that infra step.
20. After the Ticketmaster/event correctness work, replace Emergent-backed admin authentication with first-party admin auth plus the existing admin allowlist, without touching production secrets or deploying until Blake approves.
21. After auth replacement planning, replace any remaining Emergent-backed admin upload/object-storage dependency so Emergent can be fully removed safely.
22. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`, then revisit the Mongo Atlas outbound IP hardening if still open.
23. Review `backend/discovery_reports/nashville_next_candidates.json` and `.csv` to choose the next 60 YourNotDown additions before any import work; pay extra attention to bucket balance and any remaining nightlife false positives.
24. Review `backend/discovery_reports/nashville_next_candidates_balanced_top60.csv`, `..._maybe.csv`, and `..._rejected.csv` to finalize the next import batch; the current balanced pass still needs `4` better live-music candidates to hit the ideal target mix without lowering standards.
25. If the next import batch needs refinement, tune `backend/discover_ynd_candidates.py` query mix and `backend/curate_ynd_candidates.py` taste rules before writing anything to Mongo.
26. Preserve the hard reject on `Dee's Country Cocktail Lounge` in any future Nashville discovery/curation passes; it should remain rejected for `user_rejected; outside_target_zip; not_ynd_fit` and stay out of supplement/import-ready files.
27. Preserve the hard reject on `Jane's Hideaway` in any future Nashville discovery/curation passes; it should remain rejected for `user_rejected; closed` and stay out of supplement/import-ready files.
28. Use `backend/discovery_reports/nashville_import_ready_approved_54.json` / `.csv` as the current no-write import candidate set if Blake approves a later import step; the 4 missing-photo rows are now filled, so review the remaining 6 missing-website rows and the 2 mild-concern live-music rows before any actual Mongo import.
29. If Blake approves an eventual import dry run, use `backend/discovery_reports/nashville_import_ready_approved_54_validated.json` and `..._validation_report.txt` as the schema-checked source; `missing_photo_rows` is now `0`, so the remaining pre-write review is the 6 missing-website rows plus the 2 mild-concern live-music rows.
30. If Blake approves a later production-safe dry run, use `backend/import_nashville_approved_candidates.py` with the validated 54 input and real `MONGO_URL` / `DB_NAME`; keep it in default dry-run mode first, confirm duplicate counts against `db.businesses`, and only consider `--apply --confirm IMPORT_NASHVILLE_APPROVED_54` after reviewing the printed plan.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
- Do not create the Railway Ticketmaster cron service until Blake explicitly approves that step.
- Do not delete or decommission Emergent auth/storage dependencies until first-party replacements are implemented and verified.
