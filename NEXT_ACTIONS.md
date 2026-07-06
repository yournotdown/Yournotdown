## Immediate Follow-Up

1. Manually QA `/:citySlug/tonight?vibe=...` for the new lock flow:
   - lock dinner/drinks/late-night individually and confirm only unlocked slots reroll
   - lock `entertainment` and confirm the same live-music/Ticketmaster card and event details persist across `Another Night`
   - confirm every-4th `Another Night` still requests Ticketmaster only when `entertainment` is unlocked
2. Manually QA the new `You're Locked In` overlay on `/:citySlug/tonight?vibe=...`:
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

1. Review `backend/discovery_reports/nashville_take_it_easy_supplement_candidates.json`, `.csv`, and `..._report.txt`; the dry-run supplement recommends `20` additional Nashville candidates for `Take It Easy` and would likely move `just_vibing` from `15` to roughly `25-35` if a later import only approved the strongest fits.
2. Use `backend/discovery_reports/nashville_take_it_easy_supplement_human_review.csv` and `..._human_review_report.txt` for Blake review before any import-ready work:
   - current strict split: `10 approve`, `5 maybe`, `5 reject`
   - safest current approvals: `Park Cafe`, `The Cookery`, `Lockeland Table`, `Caffe Nonna`, `Epice`, `Once Upon A Time In France`, `Koré`, `Sirocco`, `ButterFLY Garden Brunch`, and `Germantown Café`
   - highest-risk rows needing caution: `The Chloe Nashville Restaurant & Bar`, `Chateau West`, `Sadie's`, `Peninsula`, `Milk & Honey Gulch`, `Frothy Monkey`, `1 Kitchen`, `Bungalow 10 Dining`, and `Twenty First`
3. Use `backend/discovery_reports/nashville_take_it_easy_approved_10_import_ready_enriched.json`, `.csv`, and `..._enrichment_report.txt` as the current approved-only enriched dry-run import package:
   - final count: `10`
   - duplicate checks against the `v5` deduped catalog are clean by `google_place_id`, exact name, normalized name, and normalized name+address
   - core Business-schema validation is clean
   - websites found: `10/10`
   - photo sets found: `10/10`
4. If Blake approves a future production-safe database dry-run for the Take It Easy 10, use `backend/import_nashville_take_it_easy_approved_10.py` against the enriched package first:
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
   - specifically confirm `/nashville/vibe` shows all 4 vibe cards above the fold on a standard desktop viewport without feeling cramped
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
