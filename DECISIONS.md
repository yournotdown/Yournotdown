## Decisions

- Date: 2026-07-04
  Decision: Treat Railway as the public production runtime, but treat Emergent as a still-active admin dependency.
  Reason: The customer-facing app now runs on Railway, but admin login still redirects through `auth.emergentagent.com`, backend `/api/auth/session` still exchanges against `demobackend.emergentagent.com`, and admin uploads may still depend on Emergent object storage.
  Tradeoff: The public production path is cleaner and no longer depends on Emergent for normal visitors, but operationally Emergent still cannot be removed without breaking new admin logins and possibly admin uploads.

- Date: 2026-07-04
  Decision: Do not delete or decommission Emergent auth/storage dependencies until first-party admin auth and storage replacements are complete and verified.
  Reason: Existing admin sessions are local and survive for up to 7 days, but any new admin login still depends on Emergent; storage replacement may also still be required for admin uploads.
  Tradeoff: This preserves admin continuity and avoids a lockout or upload regression, but it means Emergent remains a temporary operational dependency after the public Railway cutover.

- Date: 2026-07-04
  Decision: Sequence first-party admin auth/storage replacement after the current Ticketmaster and stale-event correctness work.
  Reason: Production event quality remains the highest immediate user-facing risk, while the Emergent admin dependency is important but currently bounded to admin access and admin uploads.
  Tradeoff: This keeps the highest-impact product issue first, but prolongs the period where Emergent must remain available for admin operations.

- Date: 2026-07-04
  Decision: The Railway production cutover is the current production baseline for You're Not Down.
  Reason: `www.yournotdown.com` and `yournotdown.com` now load correctly on Railway, Tonight's Move and photos are working, the Railway backend is healthy, and the Railway photo refresh cron exists.
  Tradeoff: The platform baseline is now cleaner and no longer depends on the previous frontend hosting path, but follow-up validation work shifts to event quality and residual infrastructure cleanup.

- Date: 2026-07-04
  Decision: Treat the Emergent frontend badge/script removal and Emergent-hosted asset cleanup as verified complete for the tested production pages.
  Reason: Network checks returned zero results for `assets.emergent`, `emergent-main`, `emergentcf`, `whatsyoudown.cluster`, and `static.prod-images.emergentagent.com` on tested pages, and the badge/script are removed.
  Tradeoff: Production is cleaner and less coupled to the prior hosting stack, but verification remains scoped to the tested surfaces rather than every possible route.

- Date: 2026-07-04
  Decision: Keep `Bastion`, `Santa's Pub`, and `The Bluebird Cafe` intentionally untouched for now.
  Reason: The approved image cleanup safely backfilled 7 Emergent-hosted image records, while these 3 remaining records still require separate handling and should not be changed opportunistically.
  Tradeoff: This leaves a small known cleanup tail, but avoids risky or ambiguous image changes during cutover closeout.

- Date: 2026-07-04
  Decision: The next product/ops priority order after cutover is events first, residual image cleanup later, and outbound IP hardening after that if still open.
  Reason: The biggest remaining user-facing risk is Ticketmaster events not showing in Tonight's Move and stale or outdated event data; admin event controls are the next leverage point for keeping production data trustworthy.
  Tradeoff: Event correctness gets immediate attention, while the final 3 image records and Mongo Atlas network hardening are deferred until the higher-impact production issues are understood.

- Date: 2026-07-03
  Decision: You're Not Down is positioned as a nightlife and tourist discovery product, starting with Nashville.
  Reason: The product needs a clear initial market and a direct use case for visitors deciding what to do tonight.
  Tradeoff: A narrow launch scope improves focus and execution, but delays expansion into broader geographies.

- Date: 2026-07-03
  Decision: The core experience should center on simple itinerary-style recommendations and 1 to 4 step plans.
  Reason: Tourists need a fast decision-making flow more than a deep browsing or social experience.
  Tradeoff: Simplicity improves usability and conversion, but limits customization compared with heavier planning tools.

- Date: 2026-07-03
  Decision: Distribution should prioritize hotel QR code entry points and simple tourist/hotel partner flows.
  Reason: Hotels are a direct channel to high-intent visitors who need immediate nightlife and activity suggestions.
  Tradeoff: Partner-led distribution can accelerate adoption, but may constrain early product design around hospitality use cases.

- Date: 2026-07-03
  Decision: Avoid building a bloated social app or complex account-heavy platform.
  Reason: The main job is to help someone quickly find a good move tonight, not manage a social graph.
  Tradeoff: Reduced complexity keeps the product focused, but excludes some engagement patterns common in consumer apps.

- Date: 2026-07-03
  Decision: Favor simple save and magic-link style flows over complex login systems.
  Reason: Low-friction access is better aligned with tourist usage and QR-driven discovery moments.
  Tradeoff: Simpler auth reduces friction, but may limit some advanced personalization and account management capabilities.

- Date: 2026-07-03
  Decision: Preserve a dark, playful, neon-lime, emoji-forward brand.
  Reason: The visual identity is part of the product differentiation and should feel fun, immediate, and nightlife-oriented.
  Tradeoff: A strong brand is memorable, but leaves less room for neutral enterprise-style presentation.
