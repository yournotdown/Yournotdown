# YourNotDown Production Readiness Audit

Date: 2026-07-07

## Executive Summary

YourNotDown is materially closer to launch than it was a few weeks ago. The core public flow, admin analytics/audience/Hotel QR surfaces, and business-owner magic-link access all have meaningful automated coverage and the currently approved safe test suite passes.

That said, the app is **not yet ready for a confident 500-concurrent-user launch spike** without additional hardening. The largest risks are:

1. **Hot public paths do too many Mongo reads/writes per journey**
2. **Core hot collections are missing indexes for real traffic**
3. **Public images are still proxied through the backend**
4. **Admin analytics/audience/Hotel QR queries rely on broad scans/aggregations**
5. **Admin auth/session storage still has operational/security debt**

## Launch Recommendation

**Recommendation: HOLD for a 500-concurrent-user launch target.**

If Blake wants a softer limited launch with controlled hotel distribution and monitoring in place, the app is closer to a **conditional pass**. But for the stated bar of roughly 500 concurrent users, there are enough performance and operational risks that the safer recommendation is to harden first.

## Exact Files / Functions Audited

### Public flow
- `frontend/src/pages/HomePage.jsx`
- `frontend/src/pages/VibePage.jsx`
- `frontend/src/pages/TonightPage.jsx`
- `frontend/src/pages/CategoriesPage.jsx`
- `frontend/src/pages/CategoryDetailPage.jsx`
- `frontend/src/lib/api.js`
- `frontend/src/lib/qr.js`
- `frontend/src/lib/visitor.js`

### Backend/API
- `backend/server.py`
  - `generate_itinerary`
  - `_public_businesses`
  - `_today_city_events`
  - `track_event`
  - `save_itinerary`
  - `admin_audience`
  - `admin_list_hotel_qr_codes`
  - `admin_analytics_summary`
  - `admin_business_analytics`
  - `get_current_user`
  - `get_current_business_owner`
  - `admin_business_owner_invite`
  - `admin_revoke_business_owner_access`
  - `_apply_startup_maintenance`
  - `_upsert_audience_contact`
  - `_upsert_visitor_profile`
- `backend/saved_itinerary_email.py`
- `backend/business_owner_email.py`
- `backend/storage_client.py`
- `backend/ticketmaster_events.py`

### Admin / owner portal
- `frontend/src/pages/AdminDashboardPage.jsx`
- `frontend/src/pages/AdminBusinessAnalyticsPage.jsx`
- `frontend/src/pages/BusinessClaimPage.jsx`
- `frontend/src/pages/BusinessDashboardPage.jsx`
- `frontend/src/App.js`

### Tests reviewed/run
- `backend/tests/test_business_owner_contract.py`
- `backend/tests/test_analytics_contract.py`
- `backend/tests/test_saved_itinerary_contract.py`
- `backend/tests/test_locked_steps_contract.py`
- `backend/tests/test_tonight_page_contract.py`
- `backend/tests/test_city_events_filtering_contract.py`
- `backend/tests/test_ticketmaster_events_unit.py`
- `frontend/src/pages/pages.contract.test.js`
- `frontend/src/lib/api.test.js`
- `frontend/src/lib/cities.test.js`

## What Looks Good

- Public homepage -> vibe -> Tonight flow is simple and narrow.
- Internal vibe slugs remain stable while public labels were cleaned up.
- Hotel QR attribution is wired from `?qr=` through analytics, saved itineraries, audience contacts, and visitor profiles.
- Saved-itinerary email and business-owner invite email both have branded HTML/text rendering with provider fallback behavior.
- Business-owner invite tokens are hashed.
- Business-owner session tokens are hashed.
- Owner endpoints derive business scope from the session, not arbitrary client input.
- Owner revoke now revokes invites, active owner rows, and active owner sessions.
- Hotel QR duplicate slug handling is safe.
- Hotel QR create/list/update/deactivate/delete responses are now JSON-safe.
- Audience/admin dashboards defensively handle missing fields in several places.
- Ticketmaster sync is admin-only and isolated from public spike traffic.

## P0 — Must Fix Before Launch

### 1. Add indexes for hot public/admin/session paths

This is the single biggest pre-launch gap.

Current startup indexing in `backend/server.py::_apply_startup_maintenance` only covers:
- `businesses.google_place_id`
- `businesses.normalized_name_address`
- `city_events(city_slug, local_date)`
- `city_events(source, external_event_id)`
- `audience_contacts.email_normalized`
- `visitor_profiles.visitor_id`
- `hotel_qr_codes.slug`

Missing high-value indexes include at least:
- `businesses.id`
- `businesses(city_slug, imported_status, order)`
- `businesses(city_slug, imported_status, category_slug, order)`
- `businesses(city_slug, imported_status, featured, order)`
- `analytics_events(timestamp)`
- `analytics_events(event_type, timestamp)`
- `analytics_events(business_id, timestamp)`
- `analytics_events(qr_slug, timestamp)`
- `analytics_events(visitor_id, timestamp)`
- `analytics_events(city_slug, timestamp)`
- `analytics_events(vibe, timestamp)`
- `analytics_events(slot, timestamp)`
- `saved_itineraries(email, created_at)` or `saved_itineraries(created_at)`
- `saved_itineraries(qr_slug, created_at)`
- `user_sessions.session_token`
- `business_owner_invites.token_hash`
- `business_owner_invites(business_id, status, created_at)`
- `business_owners(owner_id)`
- `business_owners(business_id, status)`
- `business_owner_sessions.session_token_hash`
- `business_owner_sessions(business_id, revoked_at)`

Why this is P0:
- `/api/itinerary/generate` is the hottest product endpoint and depends on a broad `businesses` query.
- `/api/analytics/track`, `/api/itinerary/save`, admin analytics, audience, and Hotel QR all rely on collections that will grow quickly.
- Session lookups should not be collection scans.

### 2. Reduce or isolate backend image proxy load before a 500-user launch

Public image delivery currently routes through:
- `GET /api/files/{path:path}` in `backend/server.py`
- `backend/storage_client.py::get_object`

That means public image requests proxy through the API backend to Emergent object storage.

Why this is P0:
- Tonight’s Move cards, category grids, and detail pages are image-heavy.
- A 500-user spike can become a backend bandwidth/concurrency problem even if Mongo is healthy.
- This is not a CDN-style setup today.

Launch-safe options:
- move public image delivery behind a CDN or direct public asset URLs
- aggressively cache in front of Railway
- reduce image count/weight on first impression surfaces

### 3. Hardening for `/api/itinerary/generate` under burst traffic

`backend/server.py::generate_itinerary` currently:
- fetches all eligible city events for the day
- fetches up to 2000 approved businesses with slots
- groups candidates in memory
- selects steps
- inserts an itinerary row
- inserts `business_appearance` analytics rows
- inserts `itinerary_generated`

Why this is P0:
- it is both read-heavy and write-heavy
- it currently has no caching layer
- every reroll repeats the work
- a 500-user burst likely means hundreds of near-identical reads against the same catalog/event set

At minimum before launch:
- add indexes for the businesses query
- evaluate short-lived city/event/business caching
- confirm Railway instance sizing and Mongo tier are adequate

## P1 — Should Fix Before Launch

### 4. Admin auth/session storage still has debt

`backend/server.py::auth_session` stores `user_sessions.session_token` **raw**, not hashed.

This is weaker than the owner-session model, which hashes tokens.

Risks:
- raw admin session tokens in Mongo are directly reusable if exposed
- no index on `user_sessions.session_token`
- admin auth still depends on Emergent (`EMERGENT_AUTH_URL`)

Why P1 instead of P0:
- it is admin-only, not public
- but it is still production-significant and should be cleaned up pre-launch if possible

### 5. No rate limiting / abuse controls on public write endpoints

High-risk public endpoints:
- `POST /api/analytics/track`
- `POST /api/itinerary/generate`
- `POST /api/itinerary/save`
- `GET /api/google-places/photo`
- `GET /api/files/{path:path}`
- `POST /api/leads`

Current code shows no rate-limiter/throttling layer.

Risks:
- bot traffic can inflate analytics writes
- save/generate abuse can create avoidable Mongo load
- photo proxy abuse can hit backend/object-storage bandwidth

### 6. Admin analytics / audience / Hotel QR queries will degrade as data grows

Examples:
- `admin_audience` loads up to 500 rows, then potentially `visitor_profiles.find({}, ...).to_list(5000)`
- `admin_list_hotel_qr_codes` loads all QR rows, then up to `20000` analytics docs and `10000` saved-itinerary docs
- `admin_analytics_summary` runs several wide aggregations over `analytics_events`
- `admin_business_analytics` uses aggregate pipelines over `analytics_events` without dedicated indexes

These are admin-only, so they are not the first public-launch blocker, but they will get slower quickly.

### 7. Saved-itinerary email send is synchronous in the request path

`backend/server.py::save_itinerary`:
- writes saved itinerary
- writes/upserts audience and visitor records
- writes saved-itinerary business analytics
- then calls Resend in-threadpool before returning if configured

Risks:
- external email latency can slow user response time
- burst save traffic can saturate threadpool/network

Recommendation:
- move delivery to async/background queue after launch or before if time permits

### 8. Category detail page analytics fan-out is expensive

`frontend/src/pages/CategoryDetailPage.jsx` sends one `business_view` event per business on page load.

Risks:
- one page visit can create many analytics writes
- inflates write volume on category browsing
- can distort business-view metrics

This is not in the tightest launch loop, but it is a meaningful analytics/performance smell.

## P2 — Can Wait

### 9. Expired invite/session cleanup lifecycle

The owner access system handles revoke/expiry logically, but there is no obvious cleanup job for:
- expired business owner invites
- old business owner sessions
- stale user sessions

This is manageable at launch but should be cleaned up later.

### 10. Duplicate business risk for fully manual entries

Import paths are protected by unique indexes on:
- `google_place_id`
- `normalized_name_address`

But fully manual admin-created businesses can still duplicate if those fields are absent or inconsistent.

### 11. Frontend bundle is acceptable but not especially lean

Current build output:
- `319.68 kB` gzipped JS
- `13.5 kB` gzipped CSS

This is not catastrophic, but it is large enough to matter on hotel Wi-Fi / tourist mobile conditions.

### 12. Audience/visitor metrics are all-time only

This is okay for launch, but analytics usefulness is limited without date-range-aware stickiness reporting.

## 500-Concurrent-User Readiness Assessment

### Bottom line

**Not yet proven safe for 500 concurrent users.**

### Likely hottest public endpoints

1. `GET /api/files/{path:path}`
2. `POST /api/analytics/track`
3. `POST /api/itinerary/generate`
4. `POST /api/itinerary/save`
5. `GET /api/google-places/photo`

### Approximate writes per typical user journey

A realistic user journey can create roughly:
- `homepage_visit`: 1 analytics write
- `vibe_click`: 1 analytics write
- `itinerary/generate`:
  - 1 itinerary write
  - ~4 `business_appearance` writes
  - 1 `itinerary_generated` write
  - plus frontend `itinerary_view`: 1 analytics write
- 1 to 4 `step_locked` writes
- optional reroll: repeat most of the generate load
- save flow:
  - 1 `saved_itineraries` write
  - 1 `audience_contacts` upsert
  - 1 `visitor_profiles` upsert
  - up to 4 `saved_itinerary_business` writes
  - 1 `saved_itineraries` update after email delivery

That puts a full journey roughly in the range of **13 to 18 Mongo writes** depending on behavior.

At 500 concurrent users, even a moderate share completing most of the flow can create a **multi-thousand-write burst**.

### Read pressure estimate

Every `itinerary/generate` currently pulls:
- eligible city events for the day
- up to 2000 approved businesses with slots

With 500 near-simultaneous generates, that is a large repeated read pattern against the same catalog.

### Overall readiness for 500 concurrent

If forced to predict today:
- **public browsing only**: probably survivable if traffic is short-lived and image caching cooperates
- **full funnel with generate, lock, reroll, save, and image-heavy browsing**: too much uncertainty to claim confidence

## Biggest Backend / API Risks

1. Missing indexes on hot collections
2. No public request rate limiting
3. Public image proxying through Railway backend
4. `generate_itinerary` doing broad reads every time with no short-term caching
5. Admin analytics relying on large aggregations over `analytics_events`
6. Raw admin session token storage in `user_sessions`
7. Synchronous Resend email call in `save_itinerary`

## Biggest Frontend / UX Risks

1. Public image-heavy surfaces depend on backend-proxied assets
2. `Save Tonight’s Move` still shows infrastructure-facing messages like:
   - `Email sending is not configured yet.`
   - okay for admin testing, not ideal for production users
3. Mobile/tourist-network performance may suffer from current bundle + image strategy
4. Category detail pages can create a lot of analytics writes on simple browsing

## Biggest Admin / Owner Portal Risks

1. Admin login still depends on Emergent auth exchange
2. Admin session token is stored raw
3. Audience / Hotel QR / analytics pages will slow as analytics volume grows
4. Owner portal depends on cross-subdomain cookie correctness and continued `api.yournotdown.com` health

## Mongo / Index Recommendations

Add before launch:
- `businesses.id` unique
- `businesses(city_slug, imported_status, order)`
- `businesses(city_slug, imported_status, category_slug, order)`
- `businesses(city_slug, imported_status, featured, order)`
- `user_sessions.session_token` unique or at least indexed
- `business_owner_sessions.session_token_hash` unique
- `business_owner_invites.token_hash` unique
- `business_owner_invites(business_id, status, created_at)`
- `business_owners(owner_id)` unique
- `business_owners(business_id, status)`
- `analytics_events(event_type, timestamp)`
- `analytics_events(business_id, timestamp)`
- `analytics_events(qr_slug, timestamp)`
- `analytics_events(visitor_id, timestamp)`
- `analytics_events(city_slug, timestamp)`
- `analytics_events(vibe, timestamp)`
- `analytics_events(slot, timestamp)`
- `saved_itineraries(qr_slug, created_at)`
- `saved_itineraries(email, created_at)`

Strongly consider:
- TTL or cleanup strategy for session-like collections if appropriate
- pre-aggregated analytics tables/materialized summaries later

## Railway / Resource Recommendations

Before launch, verify:
- `api.yournotdown.com` is the active backend host for cookie-based owner auth
- Railway instance size is not the smallest hobby footprint if 500-user spikes are expected
- logs and metrics retention are sufficient to debug launch night
- public image traffic is not all funneled through a tiny shared instance
- environment values for:
  - `MONGO_URL`
  - `DB_NAME`
  - `PUBLIC_SITE_URL`
  - `FRONTEND_PUBLIC_URL`
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL`
  - `ADMIN_EMAILS`
  are correct in production

Operationally check:
- startup maintenance is completing rather than being deferred
- Mongo plan has enough connections / write throughput headroom
- storage backend latency is acceptable for image-heavy traffic

## Email / Resend Risks

### Saved itinerary email

Strengths:
- branded HTML/text
- escaped content
- provider fallback exists

Risks:
- synchronous delivery in request path
- user-facing `provider_unconfigured` / fallback copy is not ideal for launch
- no queue/retry system beyond the immediate request

### Business owner invite email

Strengths:
- branded
- no visible MVP language
- secure magic-link model

Risks:
- same synchronous Resend dependency
- invite delivery admin path can block on network

## Security Risks

### Stronger areas
- owner invite tokens are hashed
- owner session tokens are hashed
- owner endpoints scope to owner session business
- admin endpoints use `require_admin`
- CORS is explicit via `_cors_allowed_origins()`
- emails escape user/business/event strings

### Risks
- admin session tokens are stored raw in Mongo
- no visible rate limiting on public endpoints
- no visible CSRF layer for cookie-authenticated admin/owner actions
- admin auth still depends on Emergent external service
- image/file proxy endpoints are public and could be abused

## Data Integrity Risks

1. Manual-business duplicate risk remains
2. Analytics events will keep growing quickly without aggregation/retention strategy
3. Old analytics rows missing newer fields are generally handled defensively, but analytics complexity will increase maintenance cost
4. Owner/session/invite records accumulate without cleanup
5. Failed Hotel QR creates may already have inserted rows historically if they hit the old serialization bug

## Public User Flow Audit Notes

### Homepage / vibe / Tonight’s Move
- Core flow is narrow and readable.
- QR attribution from `?qr=` is correctly captured before routing deeper.
- `Run It Back` retains behavior and analytics naming.
- `Lock This In` is visually clearer now.

### All-locked overlay / save flow
- Email is required; marketing opt-in is optional.
- Save flow writes a lot of data, but behaviorally it is coherent.
- Delivery-state UX is still somewhat operationally flavored.

### Mobile / desktop
- Public UI is visually cohesive.
- The major risk is performance and asset loading, not obvious logic breakage in the current code review.

## Admin Audit Notes

### Analytics / Audience / Hotel QR
- Feature scope is useful for launch.
- Biggest concern is query cost, not missing basic functionality.

### Businesses / sponsorships
- Admin business list loads up to 5000 rows with no pagination.
- Fine for a small catalog, not durable long-term.

### Owner invite / revoke
- Model is sensible.
- Revoke logic now looks correct in code.
- Business-owner scoping appears correct.

## Safe Load Test Plan

Do **not** load test production first.

### Recommended plan

1. Create a staging or isolated Railway service pointing at a staging Mongo database.
2. Seed it with:
   - current Nashville businesses
   - representative city events
   - some analytics history
3. Disable or stub Resend for load testing.
4. Use a controlled script or k6/Locust plan:
   - 25 concurrent for 5 minutes
   - 100 concurrent for 5 minutes
   - 250 concurrent for 5 minutes
   - 500 concurrent for a short peak window
5. Test these flows:
   - homepage visit
   - vibe click
   - itinerary generate
   - 1 or 2 lock actions
   - optional reroll
   - optional save flow
6. Capture:
   - p50/p95/p99 latency
   - Mongo CPU/connections/ops
   - Railway CPU/memory/network
   - error rate
   - image proxy latency

### Minimal pre-launch success criteria

- `/api/itinerary/generate` p95 remains acceptable under staged target load
- save flow does not time out or backlog
- Mongo connections stay healthy
- image routes do not overwhelm the backend

## Recommended Fix Chunks In Order

### Chunk 1 — Launch hardening
- add the missing Mongo indexes
- confirm startup maintenance applies them reliably
- add `businesses.id` / session-token indexes

### Chunk 2 — Public performance
- reduce backend image proxy pressure
- evaluate short-lived caching for public business/event reads used by `generate_itinerary`

### Chunk 3 — Abuse controls
- add basic rate limiting or throttling around public write-heavy endpoints
- add monitoring around `/analytics/track`, `/itinerary/generate`, `/itinerary/save`

### Chunk 4 — Admin auth/session cleanup
- hash admin session tokens
- plan/replace Emergent dependency for admin auth

### Chunk 5 — Analytics durability
- move saved-itinerary email delivery off the critical request path
- reduce write amplification where possible
- consider pre-aggregation or bounded analytics queries for admin dashboards

## Test Status

Safe suite run for this audit:

- `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit`
  - passed (`113` tests)
- `cd frontend && npm run build`
  - passed
- `cd frontend && CI=true npm test -- --watchAll=false`
  - passed (`3` suites, `34` tests)

Not run:
- old pytest integration suite pointing at the unreachable preview DNS host
- any production load test
- any deploy validation

## Final Call

If the launch target is **“soft launch with controlled traffic and close monitoring”**, YourNotDown is near-ready.

If the launch target is **“confidently handle ~500 concurrent users”**, the safer answer is **not yet**. The app needs indexing, backend image-delivery hardening, and basic traffic/abuse protections before that claim is credible.
