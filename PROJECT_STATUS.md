## Current State

You're Not Down is Blake's nightlife and tourist discovery product focused on helping visitors quickly decide what to do tonight, with Nashville as the first market. The intended product shape remains lightweight and conversion-focused: hotel QR distribution, simple itinerary generation, and fast 1 to 4 step plans for tourists choosing bars, restaurants, and local activities.

The repo is currently on branch `main`. The only known worktree changes outside this documentation update are two unrelated untracked migration files: `migrations/copy_catalog_collections.py` and `migrations/import_via_production_admin_api.py`. They remain untouched.

## Latest Work Session

Latest local Hotel QR tracking + Audience simplification update:
- simplified the admin `Audience` tab so the top-line cards now answer the five main questions more directly:
  - `Email Captures`
  - `Marketing Opt-ins`
  - `Saved Moves`
  - `Returning Visitor Rate`
  - `Repeat Savers`
- kept the existing audience search, `All / Marketing opted in / Not opted in` filters, audience table, visitor status badges, and hardened empty/error states
- added Hotel QR tracking foundation without changing Tonight's Move generation logic:
  - `frontend/src/lib/qr.js` now captures a `qr` query param, stores `qr_slug` locally, and ensures `hotel_qr_scan` only fires once per session per slug
  - `frontend/src/lib/api.js` now automatically attaches `qr_slug` to analytics events alongside `visitor_id`
  - `frontend/src/pages/HomePage.jsx` now detects `?qr=<slug>` on the Nashville landing page, persists it, and fires `hotel_qr_scan`
  - `frontend/src/pages/TonightPage.jsx` now includes `qr_slug` on `POST /api/itinerary/save`
  - `backend/server.py` now accepts/stores `qr_slug` on:
    - `POST /api/analytics/track`
    - `POST /api/itinerary/save`
    - `saved_itineraries`
    - `audience_contacts`
    - `visitor_profiles`
- added admin-managed Hotel QR records in `db.hotel_qr_codes` with:
  - `id`
  - `name`
  - `slug`
  - `city_slug`
  - `destination_url`
  - `hotel_name`
  - `location_label`
  - `notes`
  - `active`
  - `created_at`
  - `updated_at`
  - `created_by_user_id`
- added admin Hotel QR endpoints:
  - `GET /api/admin/hotel-qr`
  - `POST /api/admin/hotel-qr`
  - `PATCH /api/admin/hotel-qr/{id}`
  - `POST /api/admin/hotel-qr/{id}/deactivate`
- Hotel QR admin analytics now summarize per slug:
  - scans
  - unique visitors
  - Tonight's Move views
  - Lock This In clicks
  - saved moves
  - email captures
  - marketing opt-ins
  - conversion rate from scan to saved move
- added a new `Hotel QR` admin tab in `frontend/src/pages/AdminDashboardPage.jsx` with:
  - create form
  - generated URL list
  - Copy URL actions
  - low-risk tracking-first approach without adding QR image generation yet
- current QR destination format:
  - `https://www.yournotdown.com?qr=<qr_slug>`
- added local QR preview/download in the admin `Hotel QR` table using the small `qrcode` frontend package:
  - each row now shows a QR preview
  - each row has a `Download QR` button that saves a PNG
  - no separate backend QR image endpoint was needed
- homepage QR attribution still works with the root URL format because:
  - `/` preserves `location.search` when redirecting into the Nashville flow
  - `frontend/src/pages/HomePage.jsx` still captures `?qr=<slug>` on the destination page
  - the stored `qr_slug` continues to flow into analytics events, saved itineraries, audience contacts, and visitor profiles
- local verification for this Hotel QR + Audience simplification pass:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`110` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `32` tests)

Latest local Tonight's Move card CTA hierarchy polish:
- made `Lock This In` the clear primary action on itinerary cards in `frontend/src/pages/TonightPage.jsx`
- unlocked state:
  - `Lock This In` is now lime-filled and visually dominant
  - utility actions like Website, Directions, Call, and Buy Tickets are now subdued secondary pills
- locked state:
  - `Locked in` remains lime-filled and visually active
  - `Unlock` remains available as a secondary control
- no analytics names, routing, lock/save/email behavior, or itinerary generation logic changed
- local verification for this styling-only pass:
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed

Latest local Tonight's Move CTA copy tweak:
- changed the visible Tonight page reroll CTA from `Another night.` to `Run it back.`
- kept product naming as `Tonight's Move`
- did not change:
  - analytics event names such as `another_night_click`
  - handler/function names
  - routing
  - itinerary generation behavior
  - lock/save/email behavior
- local verification for this copy-only pass:
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed

Latest local admin audience + sponsor-badge polish fix:
- fixed a real admin Audience tab blank-screen bug in `frontend/src/pages/AdminDashboardPage.jsx`
- root cause:
  - the Audience panel rendered a `Returning Visitors` stat card using `RotateCw`
  - `RotateCw` was not imported from `lucide-react`
  - that missing symbol caused a runtime render crash and blanked the Audience tab
- Audience tab hardening added on top of that fix:
  - added `audienceError` state
  - normalized the `/api/admin/audience` response before storing it in state
  - now safely falls back to `{ totals: {}, rows: [] }` if the API response is partial or malformed
  - the Audience table now treats `rows` defensively with `Array.isArray(...)`
  - added a clean inline error banner when the audience API fails
  - clean loading and empty states remain intact
- the all-time new/returning visitor metrics added in the prior audience pass still render in the Audience tab:
  - anonymous visitors
  - new visitors
  - returning visitors
  - returning visitor rate
  - repeat savers
  - repeat saver rate
- polished the Tonight's Move sponsor badge in `frontend/src/pages/TonightPage.jsx` without moving it above the title:
  - kept it adjacent to `MOVE`
  - slimmed the pill shape and reduced vertical bulk
  - softened the lime border/glow
  - tightened the logo/avatar treatment
  - made the `SPONSORED BY` line smaller and the sponsor name cleaner with better spacing
- local verification for this audience/sponsor-fix pass:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`105` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `28` tests)

Latest local visitor-stickness audience update:
- added anonymous `visitor_id` tracking to the audience/email-capture stack using a browser-local UUID stored in `localStorage`
- created `frontend/src/lib/visitor.js` so the public frontend now:
  - generates a random visitor id once
  - reuses it for later analytics/save requests
  - does not use fingerprinting or ask for extra user fields
- `frontend/src/lib/api.js` now automatically includes `visitor_id` on analytics events sent through `trackEvent(...)`
- `frontend/src/pages/TonightPage.jsx` now includes `visitor_id` in `POST /api/itinerary/save`
- `backend/server.py` now accepts `visitor_id` on:
  - `POST /api/analytics/track`
  - `POST /api/itinerary/save`
- saved-itinerary and audience records now store visitor context when available:
  - `saved_itineraries.visitor_id`
  - `audience_contacts.visitor_id`
- added `visitor_profiles` upsert logic keyed by `visitor_id` with:
  - first/last seen timestamps
  - first/last city
  - first/last vibe
  - event count
  - saved itinerary count
  - first/last saved itinerary ids
  - first email captured timestamp
  - linked normalized email
- the admin `Audience` section now includes all-time visitor stickiness stats:
  - total anonymous visitors
  - new visitors
  - returning visitors
  - returning visitor rate
  - repeat savers
  - repeat saver rate
- the audience table now also shows visitor status (`New`, `Returning`, or `Unknown`) per captured email when visitor data exists
- current limitation kept intentionally simple for this chunk:
  - new/returning visitor metrics are all-time only
  - different visitor ids are not merged by email yet
- local verification for this visitor-tracking pass:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`105` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `27` tests)

Latest local audience / email captures update:
- added `marketing_opt_in` to the Tonight's Move save flow so the locked-itinerary overlay still sends the saved move email either way, while optionally capturing consent for future Nashville picks and YourNotDown updates
- `frontend/src/pages/TonightPage.jsx` now includes:
  - an optional marketing opt-in checkbox in the `You're Locked In` overlay
  - helper text clarifying that the saved move sends regardless of marketing preference
  - no first-name, last-name, or phone fields
- `backend/server.py` now:
  - stores `marketing_opt_in` on `db.saved_itineraries`
  - upserts `db.audience_contacts` by normalized lowercase email
  - preserves `marketing_opt_in=true` once an email has opted in
  - increments `saved_itinerary_count` on repeat saves
  - tracks first/last vibe, first/last saved itinerary ids, locked slots, and last saved timestamp
- added a new admin-only audience endpoint:
  - `GET /api/admin/audience`
  - returns summary totals plus audience rows
  - supports email search and `all` / `opted_in` / `not_opted_in` filtering
- `frontend/src/pages/AdminDashboardPage.jsx` now includes a new `Audience` tab with:
  - summary cards for total contacts, marketing opted-in contacts, non-marketing contacts, saved itineraries, and recent captures
  - search by email
  - filter pills for all / marketing opted in / not opted in
  - an audience table with email, opt-in status, city, last vibe, saved count, last saved date, and source
- local verification for this audience-capture pass:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`103` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` needed one source-contract assertion fix for JSX apostrophe escaping before passing locally
- still unverified:
  - manual admin QA of the new Audience tab against live saved-itinerary traffic
  - any future CSV export, unsubscribe flow, or outbound marketing sends (not part of this chunk)

Latest local revoke-flow polish update:
- tightened the admin-side business-owner access panel so it re-reads the authoritative backend state after invite and revoke instead of trusting stale inline modal state
- `frontend/src/pages/AdminDashboardPage.jsx` now has a shared `loadOwnerAccess()` helper and:
  - re-fetches `/api/admin/businesses/{business_id}/owner-access` after sending an invite
  - re-fetches `/api/admin/businesses/{business_id}/owner-access` immediately after revoke
  - clears the invite email field after revoke so the panel no longer appears to retain an active/pending owner by mistake
- backend revoke/summary behavior remains aligned with the prior fix:
  - `_owner_access_summary()` only returns pending invites and active owners
  - revoke marks active owners as revoked, revokes pending invites, and revokes active owner sessions
- local verification for this revoke-flow pass:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`101` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `22` tests)

Latest local owner-access follow-up update:
- fixed a real revoke-state bug in the business-owner scaffold:
  - `backend/server.py` `_owner_access_summary()` now only returns pending invites and active owners
  - `POST /api/admin/businesses/{business_id}/owner-access/revoke` now stamps `revoked_at` on active owners in addition to revoking pending invites and active owner sessions
  - `frontend/src/pages/AdminDashboardPage.jsx` now clears the local owner email field immediately after revoke instead of leaving stale invite text in the panel
- improved owner-facing auth failure copy:
  - `frontend/src/pages/BusinessClaimPage.jsx` no longer surfaces raw `Not authenticated` / `Invalid session` text directly to invited businesses
  - `frontend/src/pages/BusinessDashboardPage.jsx` now maps missing/revoked owner-session failures to cleaner business-facing messages
- important architecture finding remains:
  - secure HTTP-only owner-cookie auth is still cross-site today because the frontend runs on `yournotdown.com` while the backend API is still on the Railway hostname
  - that means owner-session cookies can still be unreliable or blocked in stricter browsers, especially Safari, even though the code path itself is now cleaner
  - for reliable cross-browser owner access, the backend should move behind a same-site custom domain such as `api.yournotdown.com`, with the frontend `REACT_APP_BACKEND_URL` updated to that domain
- local verification for this owner-access follow-up:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`99` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `22` tests)

Latest local business-owner hotfix update:
- patched the owner invite / claim flow after real QA exposed two issues in Chunk C: business-facing copy said `MVP`, and a successful invite claim could still land on `/business/dashboard` with `Not authenticated`
- removed internal product-development wording from business-facing owner surfaces:
  - `backend/business_owner_email.py` now says `Use the secure link below to create your business portal access. No password required.`
  - `frontend/src/pages/BusinessDashboardPage.jsx` now uses customer-facing loading / summary copy instead of `being prepared` language
- hardened owner-session establishment for cross-origin production requests:
  - `backend/server.py` no longer uses credentialed wildcard CORS
  - CORS now uses explicit allowed origins for `yournotdown.com`, `www.yournotdown.com`, and local dev origins, with optional `PUBLIC_SITE_URL` / `FRONTEND_PUBLIC_URL` additions
  - `frontend/src/pages/BusinessClaimPage.jsx` now waits for `POST /api/business/claim`, immediately verifies the new owner session via `GET /api/business/me`, and only then redirects with a full-page `window.location.replace("/business/dashboard")`
- likely root cause of the live `Not authenticated` issue:
  - the initial cross-origin claim request had no existing cookie, and the backend was using `allow_origin_regex=".*"` with `allow_credentials=True`
  - that wildcard credentialed CORS setup is unsafe for first-time session establishment and could prevent the browser from persisting the new HTTP-only owner cookie on the claim response
- local regression results for the hotfix:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed

Latest local frontend polish update:
- replaced the generic browser-tab icon with a local branded SVG favicon in `frontend/public/favicon.svg`
- `frontend/public/index.html` now explicitly prefers `%PUBLIC_URL%/favicon.svg`, so the YND lime-on-black mark takes precedence over the default browser globe
- moved Tonight's Move sponsorship placement out of the pre-headline area and into the `MOVE` line itself in `frontend/src/pages/TonightPage.jsx`
- the sponsor treatment is now a larger lime-accent pill with optional logo, `Sponsored by` label, sponsor name link, and optional tagline
- mobile behavior remains safe because the sponsor badge stacks under the `MOVE` line on small screens and shifts inline to the right on larger screens
- local verification for this polish pass:
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `21` tests)

The immediate production issue is no longer cron execution. Ticketmaster sync and the Railway cron are verified working in production, and the current local follow-up is correcting how today/tonight event data is filtered and rendered in the customer-facing product.

Latest local analytics foundation update:
- implemented Chunk A of sponsor-grade analytics tracking without changing itinerary selection, auth, billing, or owner-account behavior
- `backend/server.py` now treats `ticket_click`, `step_locked`, and `saved_itinerary_business` as business-scoped analytics events, stamps `slot` plus `sponsor_tier` for new business-scoped events going forward, and preserves backward compatibility for older analytics rows that lack `slot`
- `/api/itinerary/generate` now writes `business_appearance` events with `slot`, `category_slug`, and `source_surface="tonight_page"`
- `/api/itinerary/save` now writes one `saved_itinerary_business` analytics event per saved step/business, but does not let analytics write failures break the save-email flow
- `frontend/src/pages/TonightPage.jsx` now fires `step_locked` exactly on lock clicks and includes richer `ticket_click` payload fields (`slot`, `category_slug`, `event_id`, `event_source`, `source_surface`)
- admin/business analytics backend responses now include `step_locked`, `saved_itinerary_business`, `ticket_click`, and computed `total_engagement`; admin summary also exposes additive top-business arrays for total engagement, locked-in, and ticket-click performance
- local regression results for this chunk:
  - `python3 -m unittest backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`86` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `14` tests)
- attempted to run existing pytest-based backend analytics integration tests, but the active local Python environment does not have `pytest` installed, so those remain unverified in this workspace until pytest is available

Latest local admin analytics update:
- implemented Chunk B of sponsor-grade admin analytics on top of the Chunk A event model without changing sponsorship weighting, business-owner auth, billing, or public-site behavior
- `/api/admin/analytics/summary` now stays backward compatible while adding filtered leaderboard support with `days=7|30|90|all` plus optional `vibe` and `slot` filters
- admin analytics summary now returns additive `totals`, `filters`, `slot_leaderboards`, `vibe_breakdown`, `top_locked_in_businesses`, `top_saved_in_final_move_businesses`, `top_website_click_businesses`, `top_directions_click_businesses`, `top_ticket_click_businesses`, `top_phone_click_businesses`, `top_click_through_businesses`, and `top_sponsor_businesses`
- total engagement is now computed consistently across admin analytics as:
  - `business_appearance`
  - `business_view`
  - `step_locked`
  - `saved_itinerary_business`
  - `website_click`
  - `directions_click`
  - `ticket_click`
  - `phone_click`
- sponsor performance tier rows now include appearances, locked-in, saved-in-final-move, click metrics, total engagement, and a safe `engagement_rate`
- `frontend/src/pages/AdminDashboardPage.jsx` now has a richer admin-only analytics tab with:
  - top stat cards
  - date-range selector
  - vibe filter
  - slot filter
  - category-winner tables for Dinner / Drinks / Entertainment / Late Night
  - winner tables for Locked In, Saved in Final Move, Click-Through, Total Engagement
  - separate click-leader tables for Website / Directions / Buy Tickets / Phone
  - sponsor performance and sponsor leader tables
  - vibe breakdown table
- `frontend/src/pages/AdminBusinessAnalyticsPage.jsx` now exposes the new metrics per business: Locked In, Saved in Final Move, Buy Tickets, and Total Engagement
- local regression results for Chunk B:
  - `python3 -m unittest backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`88` tests)
- `cd frontend && npm run build` passed
- `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `15` tests)

Latest local business-owner scaffold update:
- implemented Chunk C of the business-owner invite and magic-link access foundation without changing public Tonight's Move behavior, sponsorship weighting, or billing
- `backend/server.py` now includes:
  - admin owner-access status endpoint
  - admin owner-invite send endpoint
  - admin owner-access revoke endpoint
  - public business claim endpoint
  - owner-only `GET /api/business/me`
  - owner-only `GET /api/business/analytics`
  - separate business-owner auth middleware using its own secure cookie and session collection
- added secure token/session scaffolding:
  - invite tokens are generated with `secrets.token_urlsafe(...)`
  - only `token_hash` / `session_token_hash` are stored
  - owner invite expiry is `7` days
  - owner sessions are separate from admin sessions and currently expire after `30` days
- added `backend/business_owner_email.py` for a branded Resend-backed invite email with `YND / EST. 26`, business name, create-account CTA, and 7-day expiration messaging
- if Resend env vars are missing, owner-invite creation now returns a truthful `provider_unconfigured` delivery status instead of crashing or pretending the email was sent
- `frontend/src/pages/AdminDashboardPage.jsx` now includes a Business Owner Access section in the existing business edit modal with:
  - owner email input
  - invite send action
  - invite/portal status display
  - revoke access action
- added owner routes and shells:
  - `/business/claim/:token`
  - `/business/dashboard`
- the business dashboard remains intentionally lightweight for now: business identity, sponsor tier, and basic metrics from the existing analytics model; deeper dashboard buildout is still deferred to Chunk D
- local regression results for Chunk C:
  - `python3 -m unittest backend.tests.test_business_owner_contract backend.tests.test_analytics_contract backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit` passed (`94` tests)
  - `cd frontend && npm run build` passed
  - `cd frontend && CI=true npm test -- --watchAll=false` passed (`3` suites, `19` tests)

Verified production Ticketmaster cron/apply summary:
- `status=ok`
- `mode=apply`
- `dates=2026-07-05,2026-07-06`
- `fetched=16`
- `after_dedupe=16`
- `matched=8`
- `unmatched=8`
- `upserted=9`
- `deleted_expired=5`
- `errors=0`

Investigated user-facing event paths and root causes:
- `frontend/src/pages/CategoryDetailPage.jsx` was fetching `/api/events/today` for every category and rendering a city-wide event list, not matched venue events for Live Music.
- `frontend/src/pages/TonightPage.jsx` already rendered attached event data when the itinerary business matched `city_events`, but the CTA label/time display needed cleanup.
- public `/api/businesses` results were still exposing static event-like catalog rows such as `Tomato Art Fest`, `Live On The Green`, and `CMA Fest`, plus imported `Musicians Corner`, even when they were outside the today/tonight window.
- `Musicians Corner` is currently coming from approved imported business data, not from a Ticketmaster `city_events` row.
- `Tomato Art Fest` is currently coming from legacy seeded business data migrated from the removed `events` category into `night-out`, not from Ticketmaster.
- no reliable structured field currently distinguishes those rows from normal public business/venue rows after import and category migration; generic suppression will require schema/data cleanup rather than name matching.
- no static frontend fixtures or prompt text were found to be injecting those names into the public experience; the leakage was from public business catalog reads.
- the actual public Tonight product surface is `/:citySlug/tonight?vibe=...`, which calls only `POST /api/itinerary/generate` plus the same call again for the “Another Night” refresh flow.
- `CategoryDetailPage.jsx` is still publicly routed at `/:citySlug/c/:slug`, but it is not the real Tonight flow and should not be treated as the primary event-surfacing path.

Verified production platform state still preserved:
- `www.yournotdown.com` works on the Railway frontend
- `yournotdown.com` now forwards and loads correctly to the clean app path
- Tonight's Move loads
- photos load
- the Emergent badge and script are removed
- network checks on tested pages returned zero results for `assets.emergent`, `emergent-main`, `emergentcf`, `whatsyoudown.cluster`, and `static.prod-images.emergentagent.com`
- the Railway backend is healthy
- the Railway photo refresh cron exists
- 7 Emergent-hosted image records were safely backfilled
- 3 remaining image records are intentionally untouched for now: `Bastion`, `Santa's Pub`, and `The Bluebird Cafe`

Known remaining Emergent dependencies:
- Emergent is no longer the public production runtime for the customer-facing app; public traffic is on Railway.
- Admin login still depends on Emergent Google OAuth redirect/exchange flow (`auth.emergentagent.com` and backend session exchange against `demobackend.emergentagent.com`).
- After login, admin sessions are stored locally in Mongo for 7 days, but new admin logins still depend on Emergent being available.
- Emergent object storage may still remain an admin upload dependency and should be treated as active until replaced.
- Do not delete or fully decommission Emergent dependencies until first-party admin auth and storage replacements are in place.

Operational constraints preserved in this session:
- no deploy
- no merge
- no delete
- no migrations run
- no Railway service creation
- no secret changes
- no staging or commit
- no local or production apply sync execution from the new cron entrypoint

Latest local patch state:
- implemented Chunk 2B of the Tonight's Move save flow by wiring real Resend delivery on top of the existing saved-itinerary scaffold
- `backend/server.py` now renders transactional text + HTML Tonight's Move email content, calls Resend via HTTPS when `RESEND_API_KEY` and `RESEND_FROM_EMAIL` are configured, stores `email_provider="resend"`, `provider_message_id`, `sent_at`, and `delivery_error`, and preserves the prior `provider_unconfigured` fallback when env vars are missing
- extracted the saved-itinerary email rendering into `backend/saved_itinerary_email.py` and upgraded the template from a raw system email to a premium mobile-first YourNotDown transactional email with a neon-lime text wordmark fallback, branded header/hero, city and vibe chips, numbered itinerary cards, email-safe action buttons, friendly vibe labels, friendly event time formatting, a clean text fallback, and HTML escaping for venue/event strings
- refined the transactional email header to match the approved hotel-QR sign direction more closely by replacing the `YOURNOTDOWN` HTML wordmark with a premium text treatment of `YND / EST. 26`, keeping the black background, muted secondary mark, and a thin neon-lime accent divider without introducing any image dependency
- fixed the Tonight page `Another Night` UX so a successful reroll now schedules a smooth `window.scrollTo({ top: 0, behavior: "smooth" })` on the next animation frame after the new itinerary response is applied, which keeps locked cards, Ticketmaster cadence, and the all-locked save overlay logic intact while bringing the refreshed itinerary back to the top of the page
- tightened the desktop `/:citySlug/vibe` layout so all four vibe cards fit cleanly above the fold on standard desktop screens using a more compact 2x2 grid, lighter desktop vertical spacing, slightly smaller headline scaling, shorter desktop card heights, and reduced desktop emoji/caption sizing while preserving the mobile layout and YND / EST. 26 branding
- tightened the desktop `/:citySlug/vibe` layout again for shorter viewport heights by reducing desktop top/bottom content padding further, shrinking the desktop headline max size, narrowing the desktop grid width, tightening desktop row/column gaps, and making the desktop cards shorter/wider (`lg:aspect-[9/5]`, `lg:max-h-[210px]`) so the bottom row is more likely to stay fully visible around 900px-tall browser viewports without changing mobile classes
- the save endpoint now updates `db.saved_itineraries` after send attempts so the persisted snapshot reflects `sent`, `failed`, or `provider_unconfigured` accurately without mutating `db.itineraries`
- `frontend/src/pages/TonightPage.jsx` now distinguishes all three delivery outcomes honestly:
  - `sent` -> `Sent — check your email.`
  - `provider_unconfigured` -> `Your move is saved. Email sending is not configured yet.`
  - `failed` -> `Saved, but the email could not be sent. Try again.`
- no secrets were added and no SMS path was implemented
- added dependency-free coverage in `backend/tests/test_saved_itinerary_contract.py` for mocked Resend success, failure-path source handling, provider-unconfigured fallback, persisted provider fields, premium HTML/text content shape, friendly vibe labels, button rendering, friendly event time formatting, and HTML escaping
- the premium email tests now assert the updated `YND` and `EST. 26` header treatment instead of the older all-text `YOURNOTDOWN` header while preserving the Resend/provider behavior checks
- added lightweight frontend source-contract coverage in `frontend/src/pages/pages.contract.test.js` for the new Tonight scroll-to-top behavior and the compact desktop vibe-grid sizing while also asserting the four vibe options still exist
- updated the same frontend source-contract coverage to assert the more aggressive desktop-only `/vibe` sizing classes used for the shorter above-the-fold layout target
- updated Tonight page source contract coverage to assert the `sent` / `provider_unconfigured` / `failed` frontend response handling branches
- validated locally with `python3 -m unittest backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit`, which passed (`82` tests) after the premium email-template update
- validated the frontend locally with `cd frontend && npm run build` and `cd frontend && CI=true npm test -- --watchAll=false`, both of which passed after the premium email-template update
- validated the frontend locally again after the Tonight/vibe UX fixes with `cd frontend && npm run build` and `cd frontend && CI=true npm test -- --watchAll=false`, which passed (`3` suites, `13` tests)
- implemented Chunk 2A of the Tonight's Move save flow without adding any real email provider integration or SMS
- `frontend/src/pages/TonightPage.jsx` now auto-detects when all four visible Tonight's Move steps are locked, opens a `You're Locked In` overlay once per all-locked cycle, supports `Keep editing`, preserves locked cards after dismiss, and posts the final itinerary snapshot to `POST /api/itinerary/save`
- the save overlay tracks email input, submit loading, validation error, request failure, and post-save success state without altering `Another Night`, lock/unlock behavior, or the existing Ticketmaster cadence logic
- added `POST /api/itinerary/save` in `backend/server.py`; it accepts `email`, `city_slug`, `vibe`, `source_itinerary_id`, `steps`, and `locked_slots`, validates email, sanitizes the saved step snapshots, writes to `db.saved_itineraries`, and currently returns `delivery_status=provider_unconfigured` when no provider env/config is present
- the saved itinerary snapshot document shape is now `{id, source_itinerary_id, city_slug, vibe, email, steps, locked_slots, delivery_channel, delivery_status, delivery_error, email_provider, created_at, sent_at}`
- no real email is sent in the current repo/runtime path; the scaffold is intentionally honest and reports `provider_unconfigured` until a real provider integration is added later
- added dependency-free coverage in `backend/tests/test_saved_itinerary_contract.py` for save persistence shape, invalid email rejection, provider-unconfigured behavior, and saved step snapshot structure
- updated Tonight page source contract coverage to assert the new all-locked overlay text and `/itinerary/save` call shape
- validated locally with `python3 -m unittest backend.tests.test_saved_itinerary_contract backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit`, which passed (`76` tests)
- validated the frontend locally with `cd frontend && npm run build` and `cd frontend && CI=true npm test -- --watchAll=false`, both of which passed from the stabilized repo-managed dependency state
- stabilized the frontend dependency/toolchain path for the Chunk 1 lockable Tonight's Move work
- updated `frontend/package.json` to keep `date-fns` at `4.1.0`, upgrade `react-day-picker` from `8.10.1` to `9.11.1` for React 19 compatibility, and add explicit `ajv` / `ajv-keywords` entries so the CRA/CRACO webpack toolchain no longer depends on a local-only patch
- created an intended `frontend/package-lock.json` from a clean `npm install`
- verified from scratch with `rm -rf frontend/node_modules && npm install --no-audit --no-fund --cache /tmp/ynd-npm-cache`, which completed successfully and produced a reproducible lockfile
- verified the frontend build locally with `cd frontend && npm run build`, which now passes from the clean repo-managed dependency state without any ad hoc `--no-save` AJV patch
- verified the frontend Jest suite locally with `cd frontend && CI=true npm test -- --watchAll=false`, which passed (`2` suites, `10` tests)
- the lockable Tonight's Move frontend source now appears build-clean under the repo-managed dependency state; remaining launch validation is manual browser QA rather than dependency/toolchain repair
- implemented Chunk 1 of the locked Tonight's Move work without adding the save-email flow
- extended `POST /api/itinerary/generate` request handling to accept slot-keyed `locked_steps`
- backend itinerary generation now preserves locked step snapshots, seeds `chosen_ids` with locked business ids, skips featured/Ticketmaster live-music generation when `entertainment` is locked, and safely returns stale locked snapshots instead of crashing
- `frontend/src/pages/TonightPage.jsx` now maintains `lockedSteps` state by slot, renders per-card `Lock this in` / `Unlock` controls, visually marks locked cards, and rerolls only unlocked slots on `Another Night`
- locked live-music/Ticketmaster cards now preserve their event snapshot across rerolls while first-load `ticketmaster_preferred`, every-4th `ticketmaster`, no-standalone-shows, and sports/baseball exclusion behavior remain covered by tests
- added dependency-free locked-step coverage in `backend/tests/test_locked_steps_contract.py` and updated Tonight/server contract coverage for `locked_steps`
- validated locally with `python3 -m unittest backend.tests.test_locked_steps_contract backend.tests.test_tonight_page_contract backend.tests.test_city_events_filtering_contract backend.tests.test_ticketmaster_events_unit`, which passed (`71` tests)
- frontend build/test remains unverified locally because `frontend/node_modules` is missing and `craco` is unavailable in this workspace
- added `backend/import_nashville_take_it_easy_approved_10.py`, a production-safe importer for only the approved Take It Easy 10 that defaults to dry-run, requires `--apply --confirm IMPORT_NASHVILLE_TAKE_IT_EASY_10` for real inserts, validates input before any write, checks duplicates by `google_place_id`, exact name, normalized name, and normalized name+address, inserts only non-duplicates into `db.businesses`, and never updates or deletes rows
- added focused unit coverage in `backend/tests/test_import_nashville_take_it_easy_approved_10_unit.py`
- validated the new importer locally with `python3 -m unittest backend.tests.test_import_nashville_take_it_easy_approved_10_unit`, which passed (`5` tests)
- added `backend/enrich_nashville_take_it_easy_approved_10.py`, a narrow Google Places enrichment script for only the approved Take It Easy 10 that reuses the prior Nashville photo-enrichment pattern, fetches Place Details by existing `google_place_id`, and regenerates enriched JSON/CSV/report outputs without touching Mongo or any importer
- generated `backend/discovery_reports/nashville_take_it_easy_approved_10_import_ready_enriched.json`, `.csv`, and `..._enrichment_report.txt`
- the enriched approved-only Take It Easy dry run still lands at `10` rows, now with `10/10` websites found and `10/10` photo sets found, while keeping `0` core Business-schema errors and `0` local duplicate hits against the `v5` deduped catalog
- the approved Take It Easy 10 batch is now structurally and metadata-wise much closer to the prior Nashville 54 validated standard; remaining review concerns are about fit/readiness notes rather than missing Google metadata
- added `backend/build_nashville_take_it_easy_approved_10_import_ready.py`, a dry-run transformer that promotes only the 10 approved Take It Easy supplement rows into the current Business import shape, enriches them from existing local candidate sources, checks duplicates against the `v5` deduped catalog, and emits import-ready JSON/CSV plus a validation report without touching Mongo or creating any importer
- generated `backend/discovery_reports/nashville_take_it_easy_approved_10_import_ready.json`, `.csv`, and `..._validation_report.txt`
- the approved-only Take It Easy import-ready dry run currently lands at `10` rows with `0` core Business-schema errors and `0` local duplicate hits by `google_place_id`, exact name, normalized name, or normalized name+address against the `v5` deduped catalog
- all 10 approved rows still have missing website and missing photo metadata in the current local artifact set, so the batch is structurally safe for a future production dry-run import exercise but still metadata-thin for any actual apply/import decision
- added `backend/build_nashville_take_it_easy_supplement_human_review.py`, a stricter dry-run review-sheet builder over the Take It Easy supplement candidates that keeps everything local, assigns `approve / maybe / reject` recommendations, and emits a Blake-ready human-review CSV plus summary report without creating any import-ready artifact
- generated `backend/discovery_reports/nashville_take_it_easy_supplement_human_review.csv` and `..._human_review_report.txt`
- the stricter human-review pass currently lands at `10 approve`, `5 maybe`, and `5 reject`; the safest approvals are `Park Cafe`, `The Cookery`, `Lockeland Table`, `Caffe Nonna`, `Epice`, `Once Upon A Time In France`, `Koré`, `Sirocco`, `ButterFLY Garden Brunch`, and `Germantown Café`
- highest-risk current candidates are `The Chloe Nashville Restaurant & Bar` (very low review count and event/hotel signal), `Chateau West` / `Sadie's` / `Peninsula` (may lean more `down` than `just_vibing`), and the rejected generic-risk set `Milk & Honey Gulch`, `Frothy Monkey`, `1 Kitchen`, `Bungalow 10 Dining`, and `Twenty First`
- added `backend/build_nashville_take_it_easy_supplement.py`, a dry-run local-artifact builder that merges the current Nashville candidate sources, dedupes them against the `v5` deduped catalog preview, excludes current-catalog rows plus user-rejected / Broadway / nightlife-heavy / chain / fast-casual rows, and emits a curated `Take It Easy` supplement shortlist without touching Mongo or runtime selection
- generated `backend/discovery_reports/nashville_take_it_easy_supplement_candidates.json`, `.csv`, and `..._report.txt`
- the Take It Easy supplement dry run currently recommends `20` additional Nashville candidates and projects `just_vibing` from `15` to `35` if all were later approved/imported; the top 15 alone would likely bring the catalog into roughly the `25-30` range
- strongest dry-run Take It Easy additions are currently `Park Cafe`, `The Cookery`, `Lockeland Table`, `Caffe Nonna`, `Epice`, `Once Upon A Time In France`, `Chateau West`, `Koré`, `Sirocco`, `ButterFLY Garden Brunch`, `The Chloe Nashville Restaurant & Bar`, `Tantísimo`, `Sadie's`, `Germantown Café`, and `Milk & Honey Gulch`
- the supplement builder also reports `92` source duplicates collapsed before review, `54` current-catalog overlaps excluded against the `v5` deduped business set, and balanced rejection samples across user-rejected rows, Broadway/tourist traps, nightlife-heavy rows, chain/generic brands, and fast-casual rows
- added `backend/build_nashville_vibe_affinity_backfill_preview_v5.py`, a fifth-pass dry-run wrapper over `v4` that first audits raw-source integrity, collapses same-venue duplicates by canonicalized name/address before scoring, rebuilds example lists from unique business names, stops counting successfully inferred rows as `empty_tags`, and then applies one more narrow `just_vibing` calibration pass
- generated `backend/discovery_reports/nashville_vibe_affinity_backfill_preview_v5.json`, `.csv`, `..._report_v5.txt`, and `..._manual_review_v5.csv`
- the `v5` integrity pass confirmed the prior `Attaboy` reporting issue was caused by true duplicate local source rows rather than a pure example-list bug; `Attaboy`, `Exit/In`, `The Basement East`, `Ryman Auditorium`, `L.A. Jackson`, and `Skull's Rainbow Room` are now collapsed before scoring when seed/import rows resolve to the same canonical venue address
- `v5` also confirms a smaller set of same-name different-address rows that remain intentionally distinct for now: `Old Glory`, `The Patterson House`, and `Tin Roof`
- the current `v5` preview lands at `169` scored businesses after dedupe, with primary-vibe distribution `65 down`, `64 very_down`, `25 send_it`, `15 just_vibing`, plus `21` conflicting rows, `0` all-affinities-too-close rows, `8` event/sports-like rows, and `0` empty-tag rows because `Ocean Prime` and `Ofelia` now rely on inferred tags rather than staying flagged as empty
- `v5` fixes the duplicate/example integrity issue and keeps `send_it`, `down`, and `very_down` in the requested bands, but it still undershoots the requested `just_vibing` floor (`15` vs target `18-30`), so the preview is still not yet ready for final admin review
- added `backend/build_nashville_vibe_affinity_backfill_preview_v4.py`, a fourth-pass dry-run wrapper over the `v3` scorer that keeps runtime untouched while tightening `send_it` to true edge/late-night cases, promoting more low-pressure scenic/polished dinner rows into `just_vibing`, improving empty-tag inference for `Ocean Prime` and `Ofelia`, and preserving the narrow event/sports guard from `v3`
- generated `backend/discovery_reports/nashville_vibe_affinity_backfill_preview_v4.json`, `.csv`, `..._report_v4.txt`, and `..._manual_review_v4.csv`
- the current `v4` preview is the best calibrated dry-run so far but is still not fully ready for admin review under the requested targets: sequential output lands at `175` scored businesses with primary-vibe distribution `68 down`, `66 very_down`, `26 send_it`, `15 just_vibing`, plus `20` conflicting rows, `0` all-affinities-too-close rows, `8` event/sports-like rows, and the same `2` empty-tag source rows (`Ocean Prime`, `Ofelia`)
- `v4` materially improves `send_it` calibration versus `v3`; the edgy cocktail/speakeasy set now looks much closer to intent, event/sports-like rows remain tightly contained to the expected records, and the manual-review list is concentrated on those event rows plus rooftop/conflict edge cases
- `v4` still undershoots the requested `just_vibing` floor (`15` vs target `18-30`), so one more narrow pass is still needed if the preview must fully meet the requested review distribution before any admin-facing rollout
- added `backend/build_nashville_vibe_affinity_backfill_preview_v3.py`, a third-pass dry-run local-source preview builder that narrows false `event_or_sports_like_record` detection, reduces automatic `very_down` pull from broad rooftop/popular/live-music signals, applies stronger anti-flattening/tiebreak rules, and shapes final affinity profiles so `down`, `very_down`, and `send_it` separate more cleanly without changing runtime itinerary selection
- generated `backend/discovery_reports/nashville_vibe_affinity_backfill_preview_v3.json`, `.csv`, `..._report_v3.txt`, and `..._manual_review_v3.csv`
- the current `v3` preview is materially better than `v1` and `v2` but still not good enough for admin review: sequential dry-run output lands at `175` scored businesses with primary-vibe distribution `62 very_down`, `55 down`, `47 send_it`, `11 just_vibing`, plus only `8` conflicting rows, `0` all-affinities-too-close rows, `8` event/sports-like rows, and the same `2` empty-tag rows (`Ocean Prime`, `Ofelia`)
- `v3` fixes the broad false-positive event/sports flagging from `v2`; the manual-review list is now concentrated on the intended event/sports-like records (`Nissan Stadium`, `CMA Fest`, `Bridgestone Arena`, `Geodis Park`, `Tomato Art Fest`, `Live On The Green`) plus rooftop edge cases and the two empty-tag rows
- `v3` still undershoots `just_vibing` and slightly undershoots `down` while keeping `send_it` a bit too large, so another calibration pass is still needed before treating the preview as admin-ready
- added `backend/build_nashville_vibe_affinity_backfill_preview_v2.py`, a second-pass dry-run preview builder that keeps the local-source-only approach but adds stronger bucket priors, empty-tag inference, anti-flattening/archetype reinforcement, and explicit conflict flags such as `all_affinities_too_close`, `high_send_it_without_nightlife_tags`, `high_just_vibing_with_late_night_slot`, `event_or_sports_like_record`, and `rooftop_edge_case`
- generated `backend/discovery_reports/nashville_vibe_affinity_backfill_preview_v2.json`, `.csv`, `..._report_v2.txt`, and `..._manual_review_v2.csv`
- the current `v2` preview is still not good enough for admin review: sequential dry-run output lands at `175` scored businesses with primary-vibe distribution `135 very_down`, `20 down`, `10 send_it`, `10 just_vibing`, plus `115` conflicting rows and the same `2` empty-tag rows (`Ocean Prime`, `Ofelia`)
- `v2` did improve the explicit surfacing of edge cases and manual-review flags, but it over-corrected toward `very_down`; rooftop/live-music/night-out imports are still being pulled too aggressively into the high-energy bucket
- added `backend/build_nashville_vibe_affinity_backfill_preview.py`, a dry-run local-source preview builder that scores proposed `vibe_affinity` for Nashville businesses using existing `slots`, `tags`, `category_slug`, `google_types`, `google_rating`, `google_user_rating_count`, and curated `vibe_tags` from the validated Nashville 54 artifacts without touching Mongo or runtime selection
- generated `backend/discovery_reports/nashville_vibe_affinity_backfill_preview.json`, `.csv`, and `..._report.txt` covering the current local Nashville catalog union of 175 businesses (`30` seed catalog + `91` current import catalog + `54` validated import-ready candidates)
- the current preview distribution is heavily `down`-leaning (`126 down`, `39 very_down`, `6 just_vibing`, `4 send_it`), with `111` conflicting-affinity rows, `2` empty-tag rows (`Ocean Prime`, `Ofelia`), and an initial manual-review list led by rooftop/live-music/event-like edge cases
- fixed a frontend runtime crash on `/:citySlug/tonight` and `/:citySlug/vibe` follow-throughs by moving the derived `sponsorship` binding below the `itinerary` state declaration in `frontend/src/pages/TonightPage.jsx`, eliminating the `Cannot access 'c' before initialization` temporal-dead-zone failure reported from the production bundle
- added a focused source contract assertion in `backend/tests/test_tonight_page_contract.py` to keep `const sponsorship = itinerary?.tonight_move_sponsorship;` ordered after `const [itinerary, setItinerary] = useState(null);`
- added shared city-event eligibility logic for public event reads and itinerary event attachment
- excluded `cancelled`, `canceled`, and `offsale` event statuses from public/today eligibility
- added same-day stale filtering with a configurable grace window via `EVENT_START_GRACE_MINUTES` defaulting to 60
- kept `local_time == null` events eligible for now unless status is excluded
- added shared public business filtering so `/api/businesses`, `/api/businesses/{id}`, and itinerary generation all use the same today/tonight event context
- attached matched `city_events` onto public business responses as `event`, preserving `title`, `venue_name`, `local_date`, `local_time`, `ticket_url`, and `venue_business_id`
- updated Tonight’s Move step cards to show attached event title, formatted show time, and a `Buy Tickets` button when `ticket_url` exists
- removed the temporary name-based suppression for event-like business rows because it was not generic or data-driven enough to keep
- identified follow-up schema/data work still needed if those rows should be hidden from today/tonight public business discovery without relying on names
- removed the standalone Tonight page “Live Music / Tonight’s Shows” section after confirming it was the wrong product surface
- updated itinerary generation so the numbered `LIVE MUSIC` step now prefers eligible Ticketmaster music events only, using Ticketmaster `classification_segment == Music` when present and falling back to approved live-music venue metadata when older synced rows lack stored classifications
- excluded sports/baseball Ticketmaster rows from the numbered `LIVE MUSIC` step
- updated “Another Night” to send `exclude_event_ids` so Ticketmaster-backed live-music steps can rotate to a different eligible show when available
- kept the numbered `LIVE MUSIC` step pinned to normal live-music venues when no eligible Ticketmaster music event exists, instead of falling through to arbitrary non-music entertainment businesses
- updated the Tonight step hero image preference to use the matched venue/business image first and the event image only as fallback
- fixed the Another Night exhaustion bug by stopping the frontend from accumulating itinerary business/event exclusions forever; the refresh payload now sends only the immediately previous itinerary ids
- updated live-music event picking to relax event/business exclusions when they exhaust the eligible Ticketmaster music pool, so the numbered `LIVE MUSIC` step does not get stuck without Ticketmaster forever
- updated the `/:citySlug` landing page desktop hero sizing so the headline and `I'M DOWN` CTA sit inside a centered max-width composition instead of scaling aggressively across wide desktop viewports
- updated the `/:citySlug/vibe` page desktop layout so the headline and 2x2 card grid sit inside a controlled-width container with constrained card heights and calmer desktop emoji scaling
- preserved mobile-first defaults for those pages and left `TonightPage.jsx` untouched in this session
- updated Tonight’s Move refresh cadence so the frontend now explicitly requests `live_music_event_mode` and only asks for a Ticketmaster-backed `LIVE MUSIC` step every fourth `Another Night` refresh
- updated the Tonight page first load to request `ticketmaster_preferred` mode so the initial `LIVE MUSIC` step uses an eligible Ticketmaster music event when available, without requiring four refreshes first
- changed normal Tonight refreshes to rotate standard live-music venues without forcing Ticketmaster event rendering into the numbered `LIVE MUSIC` step
- kept Ticketmaster event rendering only inside the numbered `LIVE MUSIC` step and preserved the removal of any standalone Tonight page “Tonight’s Shows” section
- added admin-only `itinerary_buckets` visibility derived from canonical business `slots`, plus matching admin filters and bucket badges for Dinner, Drinks, Live Music, and Late Night auditing
- added admin-managed featured live music overrides backed by a separate `admin_featured_events` collection, with helper logic that prioritizes an active featured live-music event above Ticketmaster and normal cadence when its active window and local date are valid for tonight
- moved Featured Live Music controls out of the Businesses tab and into a dedicated admin Sponsorships tab
- added admin-managed Tonight’s Move page sponsorships backed by a separate `admin_sponsorships` collection, including active-window and priority resolution plus public itinerary response support via `tonight_move_sponsorship`
- added admin dashboard controls to view, save, activate/deactivate, and clear both Featured Live Music and Tonight’s Move Sponsorship records using `image_url` / `sponsor_logo_url` and `ticket_url` / `sponsor_url` fields without modifying existing business data
- added Tonight page sponsor rendering near the header so active Tonight’s Move sponsorships display independently from the itinerary-selection logic
- hardened `backend/ticketmaster_sync_job.py` for Ticketmaster HTTP 429 rate limiting so cron logs emit `status=rate_limited` plus optional `retry_after`, skip deletes/writes on failed fetches, and exit cleanly instead of surfacing an expected rate limit as a crash
- added one bounded Ticketmaster client backoff path for HTTP 429 using `Retry-After` when present, capped to a short wait so the cron does not hammer the API
- added a new dry-run Google Places discovery script at `backend/discover_ynd_candidates.py` that excludes the current local catalog by `google_place_id` and normalized name/address, scores candidates for Dinner / Drinks / Live Music / Late Night fit, and writes local CSV/JSON reports without touching Mongo
- generated a Nashville discovery report at `backend/discovery_reports/nashville_next_candidates.json` and `.csv` covering ZIP codes `37201`, `37203`, `37204`, `37205`, `37206`, `37207`, `37208`, `37209`, `37210`, `37211`, and `37212`
- added a second-stage curation script at `backend/curate_ynd_candidates.py` that rebuilds the full dry-run candidate pool when needed, applies stronger YND taste filters, assigns curation metadata, and writes balanced `top60`, `maybe`, and `rejected` review files without importing anything
- generated balanced curation outputs at `backend/discovery_reports/nashville_next_candidates_balanced_top60.json`, `.csv`, `..._maybe.csv`, and `..._rejected.csv`; current balanced result lands at `56` candidates with a remaining live-music shortfall of `4`
- hard-rejected `Dee's Country Cocktail Lounge` across the Nashville discovery workflow so it is excluded from supplement/import-ready outputs and retained only in `nashville_next_candidates_rejected.csv` with `user_rejected; outside_target_zip; not_ynd_fit`
- added `backend/build_nashville_import_ready.py` and generated `backend/discovery_reports/nashville_import_ready_approved_55.json` plus `.csv`, containing the current 54 approved balanced candidates plus `Jane's Hideaway`; validation is clean for duplicates/place IDs/addresses, with 6 missing-website rows and 2 mild concern rows (`3rd & Lindsley Bar & Grill`, `The Row Kitchen & Pub`)
- hard-rejected `Jane's Hideaway` as `user_rejected; closed`, removed it from the balanced selected set, human-review approved rows, live-music supplement approved rows, and import-ready outputs, and regenerated the import-ready set as `backend/discovery_reports/nashville_import_ready_approved_54.json` plus `.csv`
- added `backend/validate_nashville_import_ready.py` and generated `backend/discovery_reports/nashville_import_ready_approved_54_validated.json` plus `..._validation_report.txt`; the dry-run transform now maps the 54 approved candidates into the current `Business` schema, confirms JSON/CSV source consistency, finds zero duplicate/schema errors, flags 6 rows missing websites, and keeps 2 mild-concern live-music rows
- added `backend/enrich_nashville_import_ready_photos.py` and used the existing `google_place_id` values to fetch Google Place Details for only `Pelato - Nashville`, `iggy’s`, `The Amsterdamian`, and `BigShotz`; all 4 now have 10 `photo_references` in the import-ready payload and 10 `google_photo_names` in the validated payload, reducing `missing_photo_rows` from 4 to 0 without writing to Mongo or applying any import
- regenerated `backend/discovery_reports/nashville_import_ready_approved_54.json`, `.csv`, `..._validated.json`, and `..._validation_report.txt` after the photo enrichment pass; local validation stayed clean, and the importer dry-run was not attempted because `MONGO_URL` was not available in the runtime environment used for the script
- added `backend/import_nashville_approved_candidates.py`, a production-safe importer for the approved Nashville 54 that defaults to dry-run, requires `--apply --confirm IMPORT_NASHVILLE_APPROVED_54` for real writes, inserts only non-duplicates into `db.businesses`, never updates or deletes rows, and is covered by focused unit tests
- kept the safe Ticketmaster alias `Ole Red - Nashville` -> `Ole Red`
- did not add First Horizon Park itinerary matching
- did not add broad aliases for venues missing approved business records
- did not touch cron config, deploy, run migrations, run apply sync, or modify secrets

## Last Known Focus

The immediate focus has shifted from cron verification to customer-facing event correctness:
1. verify the patched `/api/businesses`, `/api/businesses/{id}`, `/api/events/today`, and `/api/itinerary/generate` behavior against the real local/prod-like data shape
2. confirm the numbered `LIVE MUSIC` step on `/:citySlug/tonight?vibe=...` now shows matched Ticketmaster music events, formatted show times, and Ticketmaster purchase CTAs without a separate standalone shows section
3. design a schema/data cleanup for event-like business rows so today/tonight public suppression can become generic and data-driven without relying on business names
4. keep `First Horizon Park` and `Grand Ole Opry House` intentionally unmatched unless approved business records or rules change
5. after event-surface verification, return to the backend-local cron entrypoint validation and later Railway cron service creation only after Blake approves that infra step
6. after the Ticketmaster/event correctness work, plan first-party admin auth replacement and a storage replacement path so Emergent can be removed safely
7. fix desktop responsiveness on the landing page and vibe selection page without redesigning the Tonight’s Move results page or altering backend logic

## Prior Session Notes

Before this cron-entrypoint update, the repo had local-only tooling prepared for Emergent-image cleanup, Google photo refresh support, and admin-triggered Ticketmaster sync support. That work is now partially reflected in production outcomes:
- the 7 approved Emergent-hosted image records were safely backfilled
- the 3 exception records remain intentionally unresolved pending later review
- the Railway photo refresh cron exists and the backend is healthy
- manual Ticketmaster apply sync in production is now verified successful

Verification completed in this local patching session:
- `python3 backend/build_nashville_vibe_affinity_backfill_preview_v2.py` passed and regenerated the Nashville `vibe_affinity` preview `v2` JSON/CSV/TXT/manual-review outputs without writing to Mongo
- `python3 backend/build_nashville_vibe_affinity_backfill_preview.py` passed and regenerated the Nashville `vibe_affinity` preview JSON/CSV/TXT outputs without writing to Mongo
- `python3 -m unittest backend.tests.test_tonight_page_contract` passed (`6` tests) after the Tonight page TDZ fix
- `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract` passed (`45` tests)
- Python AST parse check passed for `backend/server.py` and `backend/ticketmaster_events.py`
- after the Tonight-flow patch, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract` passed again (`49` tests)
- after the Live Music step correction, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract` passed (`57` tests)
- after the Another Night exhaustion fix, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract` passed again (`59` tests)
- after the live-music cadence plus admin bucket audit update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract backend.tests.test_itinerary_buckets_unit backend.tests.test_admin_dashboard_contract` passed (`66` tests)
- after the first-load Ticketmaster preference plus admin featured live music override update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_featured_live_music_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract backend.tests.test_itinerary_buckets_unit backend.tests.test_admin_dashboard_contract` passed (`74` tests)
- after the admin Sponsorships tab plus Tonight’s Move sponsorship update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_featured_live_music_unit backend.tests.test_tonight_move_sponsorship_unit backend.tests.test_city_events_filtering_contract backend.tests.test_tonight_page_contract backend.tests.test_itinerary_buckets_unit backend.tests.test_admin_dashboard_contract` is the required rerun target
- after the Ticketmaster cron rate-limit hardening update, `python3 -m unittest backend.tests.test_ticketmaster_events_unit backend.tests.test_ticketmaster_sync_job_unit backend.tests.test_ticketmaster_sync_endpoint_unit` passed (`72` tests)
- `python3 backend/discover_ynd_candidates.py --report-template` passed locally and a full dry-run report was generated via Google Places without writing to Mongo
- `python3 backend/curate_ynd_candidates.py --allow-refresh` rebuilt the full candidate pool from Google Places and generated the balanced curation review files without writing to Mongo

Unverified in this local patching session:
- no Mongo writes or import dry-run against a real database were performed for the enriched Take It Easy 10 package; readiness here is limited to local artifact validation plus successful Google Places metadata fetches
- the Take It Easy supplement is based only on existing local discovery/import artifacts and the `v5` deduped catalog preview; it did not perform any live Google Places fetch or Mongo read/write
- no browser/manual QA was run on the supplement candidates; candidate fit, duplicate risk, and import readiness still need human review before any future import step
- no Mongo-backed read was used for the `vibe_affinity` preview; the dry-run preview used local catalog artifacts only (`seed_data.py`, `frontend/public/downloads/nashville_imports_only.json`, and the validated/import-ready Nashville 54 reports)
- frontend Jest was not runnable locally because workspace JS dependencies are not installed and `craco` is unavailable on PATH
- frontend build/lint was not runnable locally because `frontend/node_modules` is missing and neither `craco` nor `react-scripts` is available in the workspace
- no browser/manual QA was run here
- no production changes were made
- `python3 -m py_compile backend/ticketmaster_events.py backend/ticketmaster_sync_job.py` was not a useful validation signal locally because macOS Python cache writes are blocked in this sandbox (`PermissionError` under `~/Library/Caches/com.apple.python`)
