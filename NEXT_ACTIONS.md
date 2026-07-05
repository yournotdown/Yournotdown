## Top 5 Next Tasks

1. Manually verify the patched public event surfaces with real data:
   - `/api/businesses?category=live-music&city=nashville`
   - `/api/businesses?category=night-out&city=nashville`
   - `/api/events/today?city=nashville`
   - `/api/itinerary/generate`
2. Confirm the Live Music UI now renders matched Ticketmaster event title, show date/time, and `Buy Tickets` CTA on the correct venue cards.
3. Define and implement a schema/data cleanup for event-like catalog rows so future public suppression can be generic and data-driven instead of name-based.
4. If frontend regression testing is needed locally, install the frontend JS dependencies first so `craco test` can run; current workspace does not have `craco` available.
5. Keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or explicit mapping rules change.
6. After the event-surface verification work, return to the backend-local `ticketmaster_sync_job.py` validation and only later create the Railway cron service after Blake explicitly approves that infra step.
7. After the Ticketmaster/event correctness work, replace Emergent-backed admin authentication with first-party admin auth plus the existing admin allowlist, without touching production secrets or deploying until Blake approves.
8. After auth replacement planning, replace any remaining Emergent-backed admin upload/object-storage dependency so Emergent can be fully removed safely.
9. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`, then revisit the Mongo Atlas outbound IP hardening if still open.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
- Do not create the Railway Ticketmaster cron service until Blake explicitly approves that step.
- Do not delete or decommission Emergent auth/storage dependencies until first-party replacements are implemented and verified.
