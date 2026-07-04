## Top 5 Next Tasks

1. Run local backend tests for the Ticketmaster/event eligibility patch and confirm the new shared filter behavior stays green.
2. After Blake approves deployment later, verify production `/api/events/today?city=nashville` behavior with the new exclusions and same-day grace-window logic.
3. After production verification, decide whether to run a one-time Ticketmaster apply sync for Nashville; do not run apply sync before that verification.
4. Review remaining venue matching gaps only where approved business records exist, without broad alias expansion or First Horizon Park itinerary matching.
5. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`, then revisit the Mongo Atlas outbound IP hardening if still open.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
