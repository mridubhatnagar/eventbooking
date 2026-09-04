# Decisions

1. Organizers have a separate profile — company name, city, address, industry (fixed enum), PAN, and bank details are required at registration; GST is optional.
2. Past-dated events cannot be created or booked.
3. Reviews are only for confirmed bookings of events that have already taken place — an unpaid/pending booking can't be reviewed, even after the event date passes.
4. One review per booking, not per user/event — booking the same event twice allows two separate reviews.
5. Sensitive organizer fields (bank details, PAN, GST, address) are never exposed to customers — only company name, city, and industry appear on customer-facing event responses.
6. Organizer payouts are out of scope for now — bank details are captured for future use, but no disbursement flow is being built.
7. Booking cancellation is out of scope — no cancel/refund flow.
8. Event deletion is allowed only if the event has zero bookings — this avoids having to build cancellation/refund handling for events with paid bookings. `tickets_sold == 0` (equivalently, `capacity == capacity_remaining`) is the check.
9. JWT sessions have no revocation — tokens just expire naturally (default 2 days, configurable), no logout/blacklist mechanism.
10. Single-tenant payment gateway — one platform-level Razorpay account for everyone, not a separate gateway account per organizer; ruled out entirely, not just deferred.
11. `GET /events` supports filtering by `city` (exact match), `date_from`/`date_to` (inclusive range), and `industry` (matched via the event's organizer profile).
12. Free-text search (e.g. searching by event name) is out of scope for now — filters only, no search box.
17. Booking status is derived from `Payment.status`, never stored separately — `Payment` (`PENDING`/`REQUESTED` → `PROCESSED`|`FAILED`) is the single source of truth. `Booking.status` maps it: `PENDING` while payment is pending/requested, `CONFIRMED` once payment is `PROCESSED`, `FAILED` if payment is `FAILED`. The "Booking Confirmation" notification fires on **payment success** (`Payment.status == PROCESSED`), not at booking creation — a booking can sit at `PENDING` for a while (or end at `FAILED`) with no confirmation ever sent.
18. All events are paid events — `Event.price` is required on every event (a `0` price is technically allowed but there's no dedicated free-event path); every booking, regardless of price, goes through the full payment flow (`create_order` → `Payment` row → webhook confirmation).
19. All event dates are assumed **IST** (India-focused platform for now) — `app/timezone.py`'s `now_ist()` is the single source of truth for "now". Per-organizer/per-event timezone selection is deferred to v2.
20. Organizers aren't developers — `POST`/`PATCH /events` don't take a raw ISO datetime string. They take `event_date` (calendar date), `hour` (1-12), `minute`, and `meridiem` (`AM`/`PM`) as separate fields; timezone isn't asked for at all, it's fixed as IST (decision 19). This structurally eliminates the earlier timezone-aware-datetime crash (no ISO string means no offset can ever be sent) rather than just rejecting it at runtime. `PATCH /events/:id` requires all four date/time fields together if changing any of them — no partial merge with the existing value. `GET /events`'s `date_from`/`date_to` filters are likewise plain calendar dates, not datetimes (a customer picks a date range to browse, not a timestamp) — `date_to` is widened to end-of-day server-side so its whole day is included.

## Deferred to v2

Identified during a senior-engineer-level review of the core build. None of these block core functionality; they matter more at production scale than at current scope.

13. ~~Pagination on `GET /events` and `GET /bookings`~~ — **not deferred**, implemented on `feature/performance-improvements` (not yet merged): `?limit=`/`?offset=` on both endpoints, `total`/`limit`/`offset` in the response `meta`.
14. ~~Explicit DB indexes on filtered/joined columns~~ — **not deferred**, also implemented on `feature/performance-improvements`: `Event.city`, `Event.date`, `Event.user_id`, `Booking.user_id`, `Booking.event_id` (migration generated and applied against real Postgres). `OrganizerProfile.user_id` already had an index via its `unique=True` constraint.
15. A health-check endpoint for load balancer / orchestrator liveness/readiness probes.
16. Stronger password policy on registration — currently `min_length=1`, i.e. a one-character password is accepted.
