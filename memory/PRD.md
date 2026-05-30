# You're Not Down — Product Requirements Document

## Original Problem Statement
Build "You're Not Down" — a city-agnostic, mobile-first discovery platform that helps users find what to do in a city. Nashville is the launch city. Architecture must support adding cities later.

## Brand & Design
- Modern, Dark, Premium, Playful, Mysterious, Addictive, Social
- Mix of Spotify / TikTok / Airbnb Experiences / luxury nightlife concierge
- Single accent: electric pink #FF2A5F on near-black #050505
- Typography: Clash Display (headings) + Manrope (body)
- City-agnostic (no Nashville/country/cowboy aesthetics)

## User Personas
1. **Curious local/tourist** — opens homepage, clicks the big "I'M DOWN" button, picks a category, opens a business action (call/website/directions).
2. **Admin** — Google-authed. Manages businesses, categories, images, featured placements, reorders, and views analytics.

## Core Flows
1. **Discovery**: `/` → "I'M DOWN NASHVILLE" → `/categories` → `/c/:slug` → business action
2. **Admin**: `/admin/login` → Google OAuth → `/admin` (dashboard with CRUD + analytics)

## Data Model (MongoDB)
- `cities`: slug, name, default
- `categories`: slug, name, emoji, order
- `businesses`: id, name, description, image_path, image_url, website, phone, address, category_slug, city_slug, featured, order, created_at
- `analytics_events`: id, event_type, business_id?, category_slug?, city_slug?, ip, user_agent, timestamp
- `leads`: id, business_id, email, message, created_at
- `users`: user_id, email, name, picture, role
- `user_sessions`: user_id, session_token, expires_at

## Tech Stack
- Backend: FastAPI + Motor (Mongo) + Emergent Object Storage + Emergent Google OAuth
- Frontend: React 19 + React Router 7 + Framer Motion + Tailwind + shadcn/ui

## Implemented (Iteration 1 — Feb 2026)
- Public homepage with giant CTA
- Category picker with emoji pills
- Business list per category with Website/Directions/Call action buttons
- Admin dashboard: Google OAuth, business CRUD, image upload (object storage), feature toggle, reorder, analytics dashboard
- Analytics tracking for: homepage visit, im-down click, category click, business view, website click, directions click, phone click
- Seeded ~3-5 Nashville businesses per category
- ADMIN_EMAILS allowlist (or first-user bootstrap)
- City-aware architecture (cities collection, multi-city ready)

## Implemented (Iteration 2 — Feb 2026)
- ADMIN_EMAILS locked down to blakealansing@gmail.com (allowlist now strictly enforced, no bootstrap)
- Auth re-evaluates admin role from allowlist on every login (demotes if removed)
- New endpoint GET /api/admin/analytics/business/{id}?days=N returning totals + daily timeline
- New page /admin/business/:id — per-business deep-dive with 4 metric cards (Impressions, Website clicks, Phone calls, Directions), 7d/30d/90d range selector, recharts area chart, owner-ready copy/paste snippet
- "View analytics" icon on each business row + clickable rows in analytics summary
- De-duplicated business_view tracking on category detail page

## Backlog (P1/P2)
- P1: Lead capture per business (form on card)
- P1: Per-business analytics page (412 views / 87 website / 31 calls / 54 directions style)
- P1: City switcher UI (when 2nd city added)
- P2: Hours of operation, price tier badges
- P2: Editorial collections ("Best rooftops this weekend")
- P2: Drag-to-reorder UI in admin
- P2: Business owner self-serve portal

## Next Action Items
- Add more cities (just insert into `cities` collection)
- Per-business analytics deep-dive page in admin
- Optional: small lead-capture form on each business card
