## Top 5 Next Tasks

1. Manually verify the patched public event surfaces with real data:
   - `/api/itinerary/generate`
   - `/api/events/today?city=nashville`
   - `/:citySlug/tonight?vibe=send-it`
   - the “Another Night” refresh flow on the Tonight page
2. Confirm the revised `LIVE MUSIC` precedence on the Tonight page feels right in production-like QA:
   - active admin featured live music event overrides everything
   - active Tonight’s Move sponsorship renders near the Tonight page hero without affecting itinerary selection
   - first load uses Ticketmaster when eligible and no featured override exists
   - normal refreshes rotate standard live-music venues
   - every fourth `Another Night` requests a Ticketmaster-backed live-music step
   - Ticketmaster mode rotates when possible and safely recycles when the eligible pool is exhausted
3. Use the new admin Sponsorships tab plus itinerary bucket chips/filters to audit paid/event promotion behavior and identify polluted/event-like catalog rows that still need cleanup.
4. Manually QA the new Sponsorships admin tab:
   - Featured Live Music control is no longer inside Businesses
   - Tonight’s Move Sponsorship save/activate/clear flow works
   - active sponsor name/link/tagline render cleanly on `/:citySlug/tonight?vibe=...`
5. Manually QA the desktop and tablet layouts for `/:citySlug` and `/:citySlug/vibe` at 1440px, 1728px, tablet, and mobile widths to confirm the landing hero and 2x2 vibe grid now feel intentional without regressing mobile.
6. Define and implement a schema/data cleanup for event-like catalog rows so future public suppression can be generic and data-driven instead of name-based.
7. If frontend regression testing is needed locally, install the frontend JS dependencies first so `craco test` and `craco build` can run; current workspace does not have `craco` or `react-scripts` available.
8. Keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or explicit mapping rules change.
9. Validate the new Ticketmaster cron 429 behavior in production-like logs:
   - expected rate limits should print `status=rate_limited`
   - `retry_after` should appear when Ticketmaster sends it
   - no expired-event cleanup should run on a rate-limited fetch
   - normal successful sync output should remain unchanged
10. Decide whether a minimum successful-sync interval guard is worth adding to the cron path via a lazy `sync_state` collection; keep dry-run behavior unblocked and avoid changing manual admin workflows without explicit approval.
11. After the event-surface verification work, return to the backend-local `ticketmaster_sync_job.py` validation and only later create or adjust Railway cron service behavior after Blake explicitly approves that infra step.
12. After the Ticketmaster/event correctness work, replace Emergent-backed admin authentication with first-party admin auth plus the existing admin allowlist, without touching production secrets or deploying until Blake approves.
13. After auth replacement planning, replace any remaining Emergent-backed admin upload/object-storage dependency so Emergent can be fully removed safely.
14. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`, then revisit the Mongo Atlas outbound IP hardening if still open.
15. Review `backend/discovery_reports/nashville_next_candidates.json` and `.csv` to choose the next 60 YourNotDown additions before any import work; pay extra attention to bucket balance and any remaining nightlife false positives.
16. Review `backend/discovery_reports/nashville_next_candidates_balanced_top60.csv`, `..._maybe.csv`, and `..._rejected.csv` to finalize the next import batch; the current balanced pass still needs `4` better live-music candidates to hit the ideal target mix without lowering standards.
17. If the next import batch needs refinement, tune `backend/discover_ynd_candidates.py` query mix and `backend/curate_ynd_candidates.py` taste rules before writing anything to Mongo.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
- Do not create the Railway Ticketmaster cron service until Blake explicitly approves that step.
- Do not delete or decommission Emergent auth/storage dependencies until first-party replacements are implemented and verified.
