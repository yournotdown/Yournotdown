# YourNotDown Safe Load Test Plan

Date: 2026-07-08

## Purpose

This plan defines a safe way to test YourNotDown traffic handling without:

- deploying new code
- spamming production users or partners
- triggering Ticketmaster sync
- overloading Resend
- mutating business/admin data

The companion harness is:

- `scripts/load_test_ynd.py`

## Scope

The load-test harness simulates a narrow public user journey only:

1. `GET /api/health`
2. `GET /api/businesses?city=<city>`
3. `POST /api/analytics/track` for `homepage_visit`
4. `POST /api/analytics/track` for `vibe_click`
5. `POST /api/itinerary/generate`
6. Optional: `POST /api/itinerary/save` only when explicitly enabled

It intentionally does not call:

- Ticketmaster sync endpoints
- admin write endpoints
- import endpoints
- business owner claim/invite endpoints
- delete endpoints
- migration/import helpers

## Production Safety Rules

### Never run these against production by default

The harness defaults to a local target and refuses any `yournotdown.com` target unless:

- `--allow-production` is explicitly passed

### Do not test these in production

- `POST /api/itinerary/save` at any meaningful volume
- any admin write endpoint
- any business owner invite/revoke flow
- any import/sync route
- any destructive endpoint

### Resend safety

`/api/itinerary/save` can trigger transactional email. Because of that:

- save testing is disabled by default
- production smoke tests should leave save disabled
- if save testing is ever enabled, use a dedicated test inbox only
- do not enable save testing for concurrency runs without explicit approval

### Ticketmaster safety

This harness does not call any Ticketmaster sync route. It only uses the normal public itinerary generation path.

## Recommended Environments

### 1. Local first

Use local when validating:

- script behavior
- argument parsing
- production-target protections
- basic API contract health

Recommended starting point:

- target: local backend root
- users: `10`
- concurrency: `10`
- duration: `60s`
- ramp-up: `10s`

Example:

```bash
python3 scripts/load_test_ynd.py \
  --target http://localhost:8000 \
  --users 10 \
  --concurrency 10 \
  --duration 60 \
  --ramp-up 10 \
  --city nashville \
  --vibe down
```

### 2. Staging or isolated preview next

Use a non-production environment before any production smoke test.

Recommended stages:

1. `10` users, `60s`
2. `25` users, `120s`
3. `50` users, `180s`
4. `100` users, `300s`
5. only then consider larger ramps toward `250+`

If the goal is eventual 500-concurrent confidence, do not jump directly there. Increase gradually while watching Railway and Mongo metrics after each stage.

### 3. Tiny production smoke only

Production should get only a very small smoke test before launch.

Recommended production smoke envelope:

- users: `1` to `5`
- concurrency: `1` to `5`
- duration: `30s`
- save testing: disabled
- target: backend API host only

Example:

```bash
python3 scripts/load_test_ynd.py \
  --target https://api.yournotdown.com \
  --allow-production \
  --users 3 \
  --concurrency 3 \
  --duration 30 \
  --ramp-up 5 \
  --city nashville \
  --vibe down
```

## Endpoint Safety Notes

### Safe to hit in controlled tests

- `GET /api/health`
- `GET /api/businesses`
- `POST /api/analytics/track`
- `POST /api/itinerary/generate`

### Writes to Mongo

- `POST /api/analytics/track`
  - writes analytics events
  - may update visitor profiles
- `POST /api/itinerary/generate`
  - writes itinerary rows
  - writes analytics events
- `POST /api/itinerary/save`
  - writes saved itineraries
  - updates audience contacts
  - updates visitor profiles
  - may call Resend

### Avoid in production smoke

- `POST /api/itinerary/save`

Even though save is part of the public flow, it is intentionally excluded from the safe default because it can send email and creates more downstream writes.

## Metrics To Watch

### Railway

Watch during each run:

- request count / throughput
- average latency
- p95 and p99 latency
- CPU usage
- memory usage
- outbound bandwidth
- restart/crash events
- 5xx rate

### Mongo / Atlas

Watch during each run:

- CPU
- IOPS / disk pressure
- connections
- slow queries
- lock pressure if visible
- collection scan warnings
- write latency

### Application behavior

Watch for:

- `Couldn't plan tonight. Try again.` frequency
- `502/503/504` spikes
- image-related failures
- analytics write failures
- elevated itinerary generation latency

## Success Criteria

For a controlled pre-launch progression, a stage is healthy if:

- success rate is at least `99%`
- p95 latency stays within an acceptable product threshold
- p99 latency does not degrade sharply across the run
- Railway does not approach sustained CPU or memory saturation
- Mongo does not show obvious scan or write bottlenecks
- no endpoint begins returning frequent 5xx responses

Reasonable early thresholds to aim for:

- `GET /api/health`: p95 under `250ms`
- `GET /api/businesses`: p95 under `500ms`
- `POST /api/analytics/track`: p95 under `500ms`
- `POST /api/itinerary/generate`: p95 under `1500ms`

These are operational targets, not product guarantees. Tighten them after the first staging runs.

## Failure Signals

Stop escalating traffic if any of these appear:

- repeated 5xx errors
- p95 or p99 latency grows stage-over-stage without recovery
- Railway CPU stays pegged
- Mongo shows slow scans on hot collections
- generate requests begin failing while health/businesses stay healthy
- save testing triggers unwanted email volume

## Recommended Stage Plan Toward 500 Concurrent Users

Do not run this entire progression on production.

### Stage A: local correctness

- `10` users
- `10` concurrency
- `60s`

### Stage B: small staging baseline

- `10` users
- `10` concurrency
- `120s`

### Stage C: moderate staging

- `25` users
- `25` concurrency
- `180s`

### Stage D: heavier staging

- `50` users
- `50` concurrency
- `300s`

### Stage E: pre-launch staging

- `100` users
- `100` concurrency
- `300s`

### Stage F: controlled high staging

- `250` users
- `250` concurrency
- `300s`

### Stage G: only after explicit approval

- `500` users
- `500` concurrency
- controlled window
- real monitoring staffed live

## Script Usage Notes

The harness prints:

- total requests
- success count
- failure count
- average latency
- p95 latency
- p99 latency
- per-endpoint error counts by status/result

It is intentionally lightweight and does not try to be a full distributed load generator.

## What This Harness Intentionally Avoids

- browser rendering simulation
- image download load
- admin writes
- owner auth flows
- Ticketmaster sync
- business data mutation
- background worker/queue simulation
- CDN or edge-cache validation

If later launch confidence requires image or frontend asset pressure testing, that should be a separate controlled plan rather than being folded into this first safe API harness.
