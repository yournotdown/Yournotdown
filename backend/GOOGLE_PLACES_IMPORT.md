# Nashville Google Places Import

The importer discovers Nashville places through Google Places Text Search,
fetches Place Details, applies quality rules, deduplicates candidates, and
inserts accepted places as `pending` for admin review.

Candidates must be inside the configured Nashville ZIP codes, pass the chain
and filler filters, fit the nightlife inventory, and receive a
`brand_fit_score` of at least `70`. Museums, parks, zoos, science centers,
historical sites, family attractions, and daytime-only attractions are excluded.

Curator-allowlisted venues may bypass the review-count and brand-fit thresholds.
They remain `pending`, carry `import_override_reason: "curator_allowlist"`,
and cannot bypass safety, geography, or the `4.2` rating floor.

Major Broadway destinations bypass review-count and brand-fit thresholds. They
remain `pending`, carry `import_override_reason: "broadway_override"`, and
cannot bypass safety, geography, or the `4.2` rating floor.

It never publishes imported places automatically. Public business listing and
itinerary generation only include rows with `imported_status: "approved"`.

## Safety

- Keep `GOOGLE_PLACES_API_KEY` in the backend environment only.
- Start with the no-network report template.
- Use `--query-limit 1` for the first paid API smoke test.
- Review a full dry-run report before using `--apply`.
- `--apply` still inserts rows as `pending`.

## Commands

Print the report structure without an API key or network request:

```bash
python3 backend/google_places_importer.py --report-template
```

Run one discovery query as a paid dry-run smoke test:

```bash
GOOGLE_PLACES_API_KEY=... python3 backend/google_places_importer.py --query-limit 1
```

Run the planned Nashville dry run:

```bash
GOOGLE_PLACES_API_KEY=... python3 backend/google_places_importer.py
```

Insert reviewed dry-run candidates into MongoDB as pending:

```bash
GOOGLE_PLACES_API_KEY=... MONGO_URL=... DB_NAME=... \
  python3 backend/google_places_importer.py --apply
```

## Report

The JSON report includes:

- `found`
- `details_fetched`
- `skipped` and `skipped_by_reason`
- `duplicated`
- `pending`
- `approved`
- `inserted`
- `candidate_pool_by_slot`
- `nightlife_inventory`
- `broadway_override_results`
- `top_pending_candidates`
- `bottom_rejected_candidates`

Use the admin dashboard's **Import Review** tab to edit tags, itinerary slots,
and sponsor tiers before bulk approval or rejection.
