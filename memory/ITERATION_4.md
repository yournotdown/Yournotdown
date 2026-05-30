## Iteration 4 — Pivot to Recommendation Engine

- Itinerary engine: POST /api/itinerary/generate returns a 4-step night (Dinner → Drinks → Entertainment → Late Night)
- Sponsor weighting: none=1, silver=5, gold=10, platinum=20 (weighted random per slot)
- "Give Me Another Night" sends accumulated seen_ids as excludes for variety
- New events: itinerary_generated, itinerary_view, business_appearance, another_night_click
- Sponsor performance breakdown in admin analytics
- Admin form: sponsor_tier select + 4-slot multi-checkbox; tier badge in row
- Per-business analytics page now uses business_appearance as primary metric
- Public flow is now: / → /vibe → /tonight (no more categories in the user UX)
