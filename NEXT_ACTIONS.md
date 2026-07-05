## Top 5 Next Tasks

1. Run local syntax checks and backend unit tests for the new `backend/ticketmaster_sync_job.py` cron entrypoint plus the existing Ticketmaster helper coverage.
2. After Blake approves the infra step later, create a Railway cron service that runs the backend-local command in intentional apply mode: `python ticketmaster_sync_job.py`.
3. Before allowing the first scheduled apply run, execute the same cron command once with `--dry-run` in Railway or an equivalent safe environment and verify the log summary includes `dates`, `fetched`, `after_dedupe`, `matched`, `unmatched`, `upserted`, `deleted_expired`, and `errors`.
4. After the first approved apply-mode cron run, verify `city_events` counts and production `/api/events/today?city=nashville` behavior, confirming the known matched/unmatched shape remains sensible.
5. Keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or explicit mapping rules change.
6. After the Ticketmaster/cron work, replace Emergent-backed admin authentication with first-party admin auth plus the existing admin allowlist, without touching production secrets or deploying until Blake approves.
7. After auth replacement planning, replace any remaining Emergent-backed admin upload/object-storage dependency so Emergent can be fully removed safely.
8. Resolve the 3 intentionally untouched image records later: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`, then revisit the Mongo Atlas outbound IP hardening if still open.

## Guardrails

- Do not deploy without Blake's explicit approval.
- Do not merge to `main` without Blake's explicit approval.
- Do not delete data, secrets, branches, or production settings without Blake's explicit approval.
- Do not run migrations unless Blake explicitly approves that step.
- Do not stage or commit until Blake approves.
- Do not create the Railway Ticketmaster cron service until Blake explicitly approves that step.
- Do not delete or decommission Emergent auth/storage dependencies until first-party replacements are implemented and verified.
