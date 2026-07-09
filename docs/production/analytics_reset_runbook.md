## Analytics Reset Runbook

This runbook is for the final pre-launch analytics reset so launch metrics start from zero.

Warning:
- This is destructive.
- This deletes documents only, not collections.
- Indexes remain intact.
- Do not run this until all QA and manual cleanup are complete.
- Do not browse or test public flows after reset unless you accept new non-zero analytics.

## Approved Reset Collections

Required:
- `analytics_events`
- `visitor_profiles`
- `audience_contacts`
- `saved_itineraries`

Optional, not recommended for launch analytics reset:
- `itineraries`

## Collections Not To Touch

Do not modify:
- `businesses`
- `city_events`
- `admin_sponsorships`
- `hotel_qr_codes`
- `business_owners`
- `business_owner_invites`
- `business_owner_sessions`
- `business_owner_login_links`
- `user_sessions`
- `users`
- `contact_inquiries`
- `admin_featured_events`
- `cities`
- `categories`
- `tags`
- any other config or reference collections

## Backup Confirmation

Before any destructive step:
1. Confirm a fresh production Mongo backup or snapshot exists.
2. Record the backup timestamp.
3. Record who is running the reset and when.

## Launch Order

Run this in this order:
1. Finish all public QA.
2. Finish all admin QA.
3. Finish all owner portal QA.
4. Clean up test/fake admin data:
   - archive test contact inquiries
   - remove or deactivate test Hotel QR rows
   - revoke fake/test owner access
   - verify sponsor settings are intentional
   - verify bad/stale events are not showing
5. Confirm backup/snapshot.
6. Run the dry-run counts below.
7. Manually confirm the destructive step.
8. Run the approved `deleteMany({})` commands.
9. Run the after-count checks.
10. Do minimal admin-only verification.
11. Stop testing and wait for launch traffic.

Analytics reset should be run last before launch.

## Manual Confirmation Gate

Before the destructive section, manually type this confirmation phrase:

`I UNDERSTAND THIS CLEARS LAUNCH ANALYTICS`

## Connection Placeholder

Use your normal production Mongo access method, but do not paste secrets into this runbook.

Example placeholders only:

```bash
mongosh "<MONGO_URI>"
```

```javascript
use <DB_NAME>
```

Do not store real URI values, database names, usernames, or passwords in this document.

## Dry-Run Counts

Run these first:

```javascript
db.analytics_events.countDocuments({})
db.visitor_profiles.countDocuments({})
db.audience_contacts.countDocuments({})
db.saved_itineraries.countDocuments({})
```

Optional:

```javascript
db.itineraries.countDocuments({})
```

## Before-Count Block

Copy/paste:

```javascript
print("=== BEFORE COUNTS ===")
print("analytics_events:", db.analytics_events.countDocuments({}))
print("visitor_profiles:", db.visitor_profiles.countDocuments({}))
print("audience_contacts:", db.audience_contacts.countDocuments({}))
print("saved_itineraries:", db.saved_itineraries.countDocuments({}))
print("itineraries (optional, not required):", db.itineraries.countDocuments({}))
```

## Destructive Reset Commands

Run only after:
- backup confirmation
- QA completion
- manual cleanup
- manual confirmation phrase

Required reset:

```javascript
db.analytics_events.deleteMany({})
db.visitor_profiles.deleteMany({})
db.audience_contacts.deleteMany({})
db.saved_itineraries.deleteMany({})
```

Optional, not recommended for launch analytics reset:

```javascript
db.itineraries.deleteMany({})
```

Reminder:
- This deletes documents only.
- This does not drop collections.
- Indexes remain intact.

## After-Count Block

Copy/paste:

```javascript
print("=== AFTER COUNTS ===")
print("analytics_events:", db.analytics_events.countDocuments({}))
print("visitor_profiles:", db.visitor_profiles.countDocuments({}))
print("audience_contacts:", db.audience_contacts.countDocuments({}))
print("saved_itineraries:", db.saved_itineraries.countDocuments({}))
print("itineraries (optional):", db.itineraries.countDocuments({}))
```

## Post-Reset Verification

Immediately verify:
- Admin Analytics loads and shows zeroed usage totals.
- Audience loads and shows zeroed or empty analytics-driven stats.
- Hotel QR definitions still exist.
- Hotel QR analytics counts are zero.
- Business owner login still works.
- Businesses and sponsorships still exist.
- Contact inquiries still exist.

## Final Warnings

- Do not browse the public app after reset unless you accept non-zero analytics.
- Do not run Ticketmaster sync as part of this reset.
- Do not clear configuration, auth, sponsorship, Hotel QR definition, owner access, or contact inquiry collections.
