# Internal Sponsor Caveats

## Core Truth
The current YourNotDown sponsorship model is:

**boosted odds, not guaranteed inventory**

We can safely sell increased visibility and stronger odds of appearing in eligible Tonight's Move slots.

We cannot safely sell fixed delivery guarantees yet.

## What Sales Should Understand
The current engine combines:
- vibe fit
- category eligibility
- sponsor weighting

Current sponsor weighting:
- Normal: 1x
- Silver: 5x
- Gold: 10x
- Platinum: 20x

This improves odds, but it does not create guaranteed placement.

## Live Music / Ticketmaster Exceptions
Live Music is the biggest caveat.

Normal sponsorship weighting can be bypassed when:
- first load prefers Ticketmaster-backed live music
- every 4th Another Night refresh requests Ticketmaster-backed live music
- an admin-featured live music placement overrides the normal weighted picker

Sales should not imply that a sponsor automatically owns Live Music just because they are Silver, Gold, or Platinum.

## Current Limitations
- no guaranteed 1-in-X placement
- no guaranteed impression pacing
- no sponsor frequency caps
- no delivery ledger for promised appearances
- no guaranteed category ownership
- live music can bypass standard weighting
- user behavior like rerolls and locked cards can change short-term outcomes

## Local Nashville Estimated Odds
Latest local audit snapshot used:
- Dinner weighted pool: 56 venues
- Drinks weighted pool: 81 venues
- Late Night weighted pool: 88 venues
- Entertainment weighted fallback pool: 56 live-music-capable venues

If one average-fit sponsor existed in those pools today, estimated slot-level odds would be roughly:

### Dinner
- Silver: 8.3%
- Gold: 15.4%
- Platinum: 26.7%

### Drinks
- Silver: 5.9%
- Gold: 11.1%
- Platinum: 20.0%

### Late Night
- Silver: 5.4%
- Gold: 10.3%
- Platinum: 18.7%

### Entertainment / Live Music
- Silver: 8.3%
- Gold: 15.4%
- Platinum: 26.7%

Important: Entertainment / Live Music is less trustworthy as a sponsor-delivery estimate because Ticketmaster and featured live-music overrides can bypass the standard weighted picker.

## What Sales Must Avoid Promising
Avoid saying:
- "You'll appear 1 out of every X itineraries"
- "You'll be guaranteed tonight"
- "You'll own the Live Music slot"
- "You'll receive a fixed number of impressions"
- "You'll always beat non-sponsored venues"

Those claims are not supported by the current model.

## Safe Sales Language
Use language like:

- "boosted recommendation weight"
- "increased odds of appearing"
- "stronger share of voice in eligible categories"
- "priority weighting when your venue matches the user's vibe and slot"

Best master line:

"YourNotDown sponsorship increases your venue's odds of appearing in Tonight's Move when it is eligible for the guest's selected vibe and itinerary category. Placement is boosted, not guaranteed."

## What Would Be Needed For Guaranteed Inventory
If we want to sell guaranteed placement later, product/code changes would be required:

- sponsor pacing logic
- per-slot impression accounting
- guaranteed delivery targets
- frequency caps
- deterministic sponsor rotation or auction logic
- separate treatment for Ticketmaster/live music overrides
- reporting against guaranteed sponsor commitments

## Recommended Near-Term Packaging
For now, the cleanest packaging is:

- Silver = meaningful boosted visibility
- Gold = stronger boosted visibility
- Platinum = highest standard boosted visibility

Keep guaranteed products as a future premium roadmap item, not a current promise.
