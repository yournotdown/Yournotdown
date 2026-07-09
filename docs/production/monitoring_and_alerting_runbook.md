# YourNotDown Monitoring And Alerting Runbook

Date: 2026-07-08

## Purpose

This runbook defines how to watch YourNotDown during launch, how to detect trouble quickly, and what to do first when something breaks.

It is written for the current production shape:

- public frontend on `www.yournotdown.com`
- backend API on `api.yournotdown.com`
- Railway runtime
- Mongo as the primary database
- Resend for transactional email
- Ticketmaster sync in the existing cron/admin flow

This is an operational guide, not a deploy guide. Do not deploy from this document.

## 1. Launch Monitoring Checklist

Watch these continuously during launch windows:

- Backend health:
  - `GET https://api.yournotdown.com/api/health`
  - `GET https://api.yournotdown.com/api/ready`
- Frontend health:
  - homepage loads
  - `/nashville/vibe` loads
  - `/nashville/tonight` generates a move
- 5xx errors:
  - Railway request logs
  - browser console/network on manual spot checks
- Backend restarts:
  - Railway service restarts
  - crash loops
- Latency spikes:
  - request latency in Railway if available
  - manual timing for itinerary generation if dashboard visibility is thin
- Mongo slow queries:
  - slow query panel / profiler
  - spikes on `analytics_events`, `saved_itineraries`, `visitor_profiles`, `audience_contacts`
- Mongo connection pressure:
  - connection count
  - sudden upward drift during traffic pushes
- Resend email failures:
  - saved itinerary emails
  - business owner invites
- Saved itinerary failures:
  - saves returning failure in browser/manual QA
  - Resend delivery failures after save
- Business owner invite failures:
  - provider failures
  - 4xx/5xx on invite send
- Ticketmaster cron failures / 429s:
  - rate-limited syncs
  - failed cron runs
  - zero-event syncs when events should exist
- Hotel QR tracking failures:
  - QR scan activity missing from admin Hotel QR
  - downstream save/opt-in attribution missing
- Admin analytics failures:
  - admin summary/business/audience/hotel QR pages erroring or timing out

## 2. Key URLs To Check

Public / API:

- `https://api.yournotdown.com/api/health`
- `https://api.yournotdown.com/api/ready`
- `https://www.yournotdown.com`
- `https://www.yournotdown.com/nashville/vibe`
- `https://www.yournotdown.com/nashville/tonight`

Admin manual checks:

- Admin Analytics:
  - `GET /api/admin/analytics/summary` via the admin dashboard
- Admin Audience:
  - `GET /api/admin/audience` via the admin dashboard
- Admin Hotel QR:
  - `GET /api/admin/hotel-qr` via the admin dashboard

Business-owner manual check:

- `/business/dashboard`

## 3. Railway Monitoring

Watch the backend service in Railway for:

- CPU:
  - sustained high usage during traffic pushes
  - sudden spikes tied to itinerary generation or image proxy load
- Memory:
  - sustained growth
  - restart-causing pressure
- Restarts:
  - any unexpected restart is notable during launch
  - repeated restarts are urgent
- Deploy health:
  - latest deploy healthy
  - no failed startup / health-check loops
- Logs:
  - 4xx bursts that indicate abuse or broken frontend behavior
  - 5xx bursts that indicate real service failure
  - repeated Mongo, Resend, Google Places photo, or Ticketmaster warnings/errors
- Request latency if Railway exposes it:
  - watch median and tail latency
  - focus on sustained P95 degradation, not one-off spikes

What to search for in logs:

- `saved_itinerary_business analytics write failed`
- `Mongo readiness ping failed`
- `Google Places photo proxy is unavailable`
- `Google Places photo request failed`
- `Ticketmaster sync failed`

## 4. Mongo Monitoring

Watch Mongo for:

- Connection count:
  - sustained upward movement during a traffic push
  - abrupt ceiling pressure
- Slow queries:
  - especially on hot collections
- CPU / load:
  - sustained pressure during write spikes
- Storage growth:
  - overall growth
  - sudden growth from analytics writes or saves
- `analytics_events` growth:
  - expected to grow fastest
  - watch write rate and storage growth
- `saved_itineraries` growth:
  - watch save spikes and failures
- `audience_contacts` growth:
  - confirm growth tracks real save traffic
- `visitor_profiles` growth:
  - confirm visitor updates stay healthy

Priority collections to inspect first:

- `analytics_events`
- `itineraries`
- `saved_itineraries`
- `audience_contacts`
- `visitor_profiles`
- `hotel_qr_codes`
- `user_sessions`
- `business_owner_invites`
- `business_owner_sessions`

What counts as a problem:

- connection spikes that do not settle
- repeated slow-query alerts on hot public/admin collections
- CPU saturation during modest traffic
- write latency spikes tied to `analytics_events` or `saved_itineraries`

## 5. Resend Monitoring

Watch Resend for:

- Delivery failures
- Rejected sends
- Rate limits
- Domain verification status
- Correct `from` address in use

Highest-priority flows:

- saved itinerary email
- business owner invite email

What counts as a problem:

- saved-itinerary sends failing repeatedly
- owner invites failing repeatedly
- rate-limited sends during normal traffic
- verification/domain drift that breaks all mail

Immediate checks:

- confirm the sending domain is still verified
- confirm the configured `from` address is valid
- inspect recent failed sends for a common pattern

## 6. Ticketmaster Monitoring

Watch Ticketmaster sync for:

- cron success
- 429 rate limits
- zero-event syncs
- stale `city_events`
- poor live-music variety in the public flow

Where to look:

- Railway cron/job logs
- admin sync/report output if used for inspection
- public Tonight flow manual spot checks

What counts as a problem:

- repeated `429`/rate-limited syncs
- repeated failed cron runs
- zero-event syncs on nights when events should exist
- public live music going stale or becoming obviously repetitive

Important incident rule:

- do not run Ticketmaster sync manually during an incident unless there is a specific, approved reason
- avoid adding more external API pressure while the system is unstable

## 7. What Counts As Urgent

Treat these as urgent launch issues:

- backend health endpoint fails
- repeated `5xx` errors, especially on public flow endpoints
- unexpected backend restarts
- sustained P95 latency over `3s` under real traffic
- saved-itinerary email failures
- Hotel QR scans stop tracking
- admin becomes inaccessible
- Mongo slow-query or connection spike that affects public/admin use

Escalate immediately if any of these happen:

- homepage or vibe page fails to load
- `/nashville/tonight` cannot generate a move
- save flow returns failure or mail stops sending
- owner invites stop sending during partner onboarding
- admin analytics/audience/hotel QR all error at once

## 8. Manual Launch Watch Plan

Run this routine at launch start, then every `30` to `60` minutes during the first meaningful traffic push.

1. Check health:
   - load `https://api.yournotdown.com/api/health`
   - load `https://api.yournotdown.com/api/ready`
2. Check public flow:
   - load `https://www.yournotdown.com`
   - open `/nashville/vibe`
   - generate a move on `/nashville/tonight`
3. Check save email:
   - save a locked move to a controlled inbox
   - confirm the API response is healthy
   - confirm the email arrives
4. Check Audience:
   - confirm the save appears in Admin Audience
5. Check Hotel QR:
   - use a known QR slug or test scan
   - confirm scan and downstream attribution appear
6. Check Railway logs:
   - look for 5xx spikes, restarts, repeated warnings/errors
7. Check Mongo dashboard:
   - connections
   - slow queries
   - CPU/load
8. Check Resend dashboard:
   - recent deliveries/failures
9. Repeat every `30` to `60` minutes during the first traffic push

## 9. Emergency Actions

### Frontend rollback

- use the hosting platform’s rollback/redeploy controls to move back to the last known good frontend build
- prefer rollback over emergency code edits during live traffic if the issue is clearly frontend-only

### Backend rollback

- use Railway’s previous deploy rollback if the issue is backend-only and recent
- confirm `/api/health` and `/api/ready` recover after rollback

### Services not to touch during an incident unless necessary

- do not run migrations
- do not rotate secrets
- do not run manual Ticketmaster sync just to “see if it helps”
- do not make ad hoc Mongo schema/data changes without a clear incident reason

### Disable a bad sponsor

- use the admin sponsorship controls to clear or deactivate the problematic sponsorship
- avoid code changes if the issue is specific to one sponsor configuration

### Deactivate a bad Hotel QR

- use the admin Hotel QR `Deactivate` action
- prefer deactivation over deletion during an incident so historical analytics stay intact

### Stop owner invites temporarily

- operationally stop sending new invites from admin if Resend or owner-claim flow is unstable
- if the incident is email-provider-related, do not keep retrying invites blindly

### Avoid running Ticketmaster sync manually during an incident

- a live incident is the wrong time to add extra write/API pressure unless the root cause is specifically a stale-event emergency and the path is well understood

## 10. Logging Gaps

Current code review shows the following visibility gaps.

### Itinerary generation failure

Gap:

- `generate_itinerary` has no surrounding error logging for unexpected failures
- a backend exception would surface as a failed request, but there is no explicit structured log line for itinerary generation failure context

Recommendation:

- small code change recommended later
- add a concise failure log with city, vibe, and request path context

### Save itinerary failure

What exists:

- saved-step analytics write failure is logged:
  - `saved_itinerary_business analytics write failed`

Gap:

- Resend send failure inside `save_itinerary` is converted into a response payload but is not explicitly logged
- broader save failure before response is not explicitly logged with context

Recommendation:

- small code change recommended later
- log Resend failure and top-level save exceptions with minimal context

### Resend send failure

Gap:

- `_send_resend_email` and `_send_business_owner_invite_email` rely on request exceptions and return-state updates
- there is no direct log line when Resend fails for save or owner invite

Recommendation:

- small code change recommended later
- add warning-level logs for save-email and owner-invite email failures

### Owner invite failure

Gap:

- `admin_business_owner_invite` updates delivery state on failure, but does not log the failure explicitly
- repeated partner onboarding problems may be visible only through UI state unless someone inspects DB rows

Recommendation:

- small code change recommended later
- add warning-level logging on invite send failure

### Hotel QR create/delete failure

Gap:

- Hotel QR admin create/update/deactivate/delete endpoints do not currently log failure context
- failures would rely on request status/log platform capture only

Recommendation:

- small code change recommended later
- add concise warning/error logs on admin write failures if those become noisy during launch

### Ticketmaster cron failure

What exists:

- `admin_ticketmaster_sync` logs `Ticketmaster sync failed: <ExceptionType>`
- `backend/ticketmaster_sync_job.py` prints structured summary/error output, including rate-limited cases

Gap:

- cron visibility is better than several other flows, but still depends on someone watching logs/output
- zero-event but technically successful syncs still require human attention

Recommendation:

- no urgent code change required for this runbook task
- operationally monitor cron outputs and zero-event runs closely

## First Response Order

If something breaks during launch, use this order:

1. Confirm whether the public flow is broken or just an admin/partner surface.
2. Check Railway health, restarts, and recent 5xx logs.
3. Check Mongo connections and slow queries.
4. Check Resend if the failure involves save email or owner invite.
5. Check Ticketmaster cron/logs only if live-music freshness is the issue.
6. Roll back the smallest surface possible if the issue clearly maps to a recent deploy.

## Notes

- This runbook assumes the current production baseline and should be updated after any meaningful infra change.
- If the backend runtime changes from a single process to multiple instances, the write-rate-limit notes and alert interpretation should be updated as well.
