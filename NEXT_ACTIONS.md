## Top 5 Next Tasks

1. Investigate why Ticketmaster events are not showing in Tonight's Move, including ingestion, filtering, storage, and frontend selection paths.
2. Fix stale or outdated events so production event data reflects current listings and valid timing.
3. Review existing admin event controls and decide what needs to be added or tightened for event visibility, freshness, and overrides.
4. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`.
5. Replace Mongo Atlas `0.0.0.0/0` access with a Railway Static Outbound IP later if that security follow-up is still open.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
