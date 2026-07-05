## Top 5 Next Tasks

1. Manually verify the patched public event surfaces with real data:
   - `/api/itinerary/generate`
   - `/api/events/today?city=nashville`
   - `/:citySlug/tonight?vibe=send-it`
   - the “Another Night” refresh flow on the Tonight page
2. Confirm the new `LIVE MUSIC` cadence on the Tonight page feels right in production-like QA:
   - normal refreshes should rotate standard live-music venues
   - every fourth `Another Night` should request a Ticketmaster-backed live-music step when eligible shows exist
   - Ticketmaster mode should rotate to a different eligible show when possible and safely recycle when the event pool is exhausted
3. Manually QA the desktop and tablet layouts for `/:citySlug` and `/:citySlug/vibe` at 1440px, 1728px, tablet, and mobile widths to confirm the landing hero and 2x2 vibe grid now feel intentional without regressing mobile.
4. Use the new admin itinerary bucket chips/filters to audit which businesses currently feed Dinner, Drinks, Live Music, and Late Night, then identify any polluted/event-like catalog rows that need cleanup.
5. Define and implement a schema/data cleanup for event-like catalog rows so future public suppression can be generic and data-driven instead of name-based.
6. If frontend regression testing is needed locally, install the frontend JS dependencies first so `craco test` and `craco build` can run; current workspace does not have `craco` or `react-scripts` available.
7. Keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or explicit mapping rules change.
8. After the event-surface verification work, return to the backend-local `ticketmaster_sync_job.py` validation and only later create the Railway cron service after Blake explicitly approves that infra step.
9. After the Ticketmaster/event correctness work, replace Emergent-backed admin authentication with first-party admin auth plus the existing admin allowlist, without touching production secrets or deploying until Blake approves.
10. After auth replacement planning, replace any remaining Emergent-backed admin upload/object-storage dependency so Emergent can be fully removed safely.
11. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`, then revisit the Mongo Atlas outbound IP hardening if still open.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
- Do not create the Railway Ticketmaster cron service until Blake explicitly approves that step.
- Do not delete or decommission Emergent auth/storage dependencies until first-party replacements are implemented and verified.
