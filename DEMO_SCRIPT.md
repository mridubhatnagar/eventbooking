# Demo Recording Script

Exact call sequence, endpoint, and payload for every step. See `DEMO.md` for prerequisites and rationale — this file is just the script to follow while recording.

Placeholders to fill in as you go: `{ORGANIZER_TOKEN}`, `{CUSTOMER_TOKEN}`, `{EVENT_ID_1}` (future event), `{EVENT_ID_2}` (past event), `{BOOKING_ID_1}`, `{BOOKING_ID_2}`.

---

**1. `POST /auth/register`** — organizer
```json
{
  "email": "organizer@demo.com",
  "phone": "1234567890",
  "password": "pass1234",
  "role": "organizer",
  "organizer_profile": {
    "company_name": "Demo Events Co",
    "city": "Bengaluru",
    "address": "123 MG Road, Bengaluru",
    "industry": "MUSIC",
    "pan_number": "ABCDE1234F",
    "bank_account_holder_name": "Demo Events Co",
    "bank_account_number": "000123456789",
    "bank_ifsc_code": "DEMO0001234",
    "bank_name": "Demo Bank"
  }
}
```

**2. `POST /auth/register`** — customer
```json
{"email": "customer@demo.com", "phone": "1234567891", "password": "pass1234", "role": "customer"}
```

**3. `POST /auth/login`** — organizer
```json
{"email": "organizer@demo.com", "password": "pass1234"}
```
→ copy `data.access_token` as `{ORGANIZER_TOKEN}`. Authorize with it.

**4. `POST /events`** — main event
```json
{"name": "Demo Concert", "date": "2026-12-01T18:00:00", "venue": "Main Hall", "city": "Bengaluru", "capacity": 50, "price": "25.00"}
```
→ copy `data.id` as `{EVENT_ID_1}`.

**5. `POST /events`** — past event (for the review demo)
```json
{"name": "Demo Past Show", "date": "2025-01-01T18:00:00", "venue": "Side Stage", "city": "Bengaluru", "capacity": 50, "price": "15.00"}
```
→ copy `data.id` as `{EVENT_ID_2}`.

**6. `PATCH /events/{EVENT_ID_1}`**
```json
{"venue": "Main Hall (Renovated)"}
```
→ no response to show; watch `docker compose logs -f worker` for the `[notification] ...` line.

**7. `PATCH /organizers/me`** — still authorized as organizer
```json
{"company_name": "Demo Events Co, Ltd"}
```

**8. `POST /auth/login`** — customer
```json
{"email": "customer@demo.com", "password": "pass1234"}
```
→ copy `data.access_token` as `{CUSTOMER_TOKEN}`. Re-authorize with it.

**9. `GET /events`** — no payload; optionally `?city=Bengaluru`
→ point out each event's `organizer` object (`company_name`, `city`, `industry`).

**10. `POST /bookings`** — book the main (future) event
```json
{"event_id": {EVENT_ID_1}, "quantity": 2}
```
→ copy `data.id` as `{BOOKING_ID_1}`. `status: "PENDING"`.

**11. `POST /bookings`** — book the past event
```json
{"event_id": {EVENT_ID_2}, "quantity": 1}
```
→ copy `data.id` as `{BOOKING_ID_2}`.

**12. Wait ~5 seconds** (`PAYMENT_GATEWAY_DELAY_SECONDS`) for the payment flow to complete for both bookings.

**13. `GET /bookings/{BOOKING_ID_1}`** — no payload
→ `status` now `"CONFIRMED"`.

**14. `GET /bookings/{BOOKING_ID_2}`** — no payload
→ `status` now `"CONFIRMED"`.

**15. `POST /bookings/{BOOKING_ID_1}/reviews`** — future event, expect `400`
```json
{"rating": 5, "review_text": "Can't wait!"}
```
→ rejected: event hasn't happened yet.

**16. `POST /bookings/{BOOKING_ID_2}/reviews`** — past event, expect `201`
```json
{"rating": 5, "review_text": "Great show!"}
```

**17. `GET /events/{EVENT_ID_2}/reviews`** — no payload
→ the review from step 16 appears.
