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

## Deferred to v2

Identified during a senior-engineer-level review of the core build. None of these block core functionality; they matter more at production scale than at current scope.

13. Pagination on `GET /events` and `GET /bookings` — both currently return unbounded result sets.
14. Explicit DB indexes on filtered/joined columns without one today: `Event.city`, `Event.date`, `Event.user_id`, `Booking.user_id`, `Booking.event_id`, `OrganizerProfile.user_id`.
15. A health-check endpoint for load balancer / orchestrator liveness/readiness probes.
16. Stronger password policy on registration — currently `min_length=1`, i.e. a one-character password is accepted.
