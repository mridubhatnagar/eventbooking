# Demo: Full API Flow via Swagger UI

The full customer-facing flow — register, login, create an event, edit it, browse, book, watch the payment complete, and leave a review — can be demonstrated entirely through Swagger UI. Booking creation triggers the mocked payment flow (order creation → capture → webhook → confirmation) automatically in the background; nothing else needs to be touched by hand.

## Prerequisites

```bash
cp .env.example .env.local   # fill in real values, see README.md
docker compose up --build -d db redis mock-razorpay
docker compose run --rm app flask --app run db upgrade   # manual, explicit — see CLAUDE.md
docker compose up --build
```

Swagger UI: `http://localhost:5000/apidoc/swagger/` (adjust the port if overridden locally, e.g. via `docker-compose.override.yml`).

## Walkthrough

1. `POST /auth/register` — register an organizer. `organizer_profile` is required for `role: "organizer"`:
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
2. `POST /auth/register` again — register a customer:
   ```json
   {"email": "customer@demo.com", "phone": "1234567891", "password": "pass1234", "role": "customer"}
   ```
3. `POST /auth/login` as the organizer → copy `data.access_token` from the response.
4. Click **Authorize** (lock icon, top right), paste the organizer's token, click Authorize, close the dialog.
5. `POST /events` — create the main demo event:
   ```json
   {"name": "Demo Concert", "date": "2026-12-01T18:00:00", "venue": "Main Hall", "city": "Bengaluru", "capacity": 50, "price": "25.00"}
   ```
6. `POST /events` again — a **second** event dated in the past, solely to demonstrate reviews (a review can only be left once the event has actually happened — see step 14):
   ```json
   {"name": "Demo Past Show", "date": "2025-01-01T18:00:00", "venue": "Side Stage", "city": "Bengaluru", "capacity": 50, "price": "15.00"}
   ```
7. `PATCH /events/{id}` on the main event (e.g. change the venue) — triggers the Event Update Notification task. Nothing to check in Swagger for this one; watch `docker compose logs -f worker` for the `[notification] ...` line.
8. `PATCH /organizers/me` — organizer edits their own profile (e.g. `{"company_name": "Demo Events Co, Ltd"}`). Still authorized as the organizer.
9. `POST /auth/login` as the customer → copy their token.
10. Click **Authorize** again, replace with the customer's token.
11. `GET /events` (optionally `?city=Bengaluru`) — browse events. Each event's response now includes an `organizer` object (`company_name`, `city`, `industry`) — note that bank/GST/PAN/address never appear here.
12. `POST /bookings` — book the main (future) event:
    ```json
    {"event_id": 1, "quantity": 2}
    ```
    Returns `201` with `status: "PENDING"`.
13. `POST /bookings` — book the past-dated event too, so it can be reviewed:
    ```json
    {"event_id": 2, "quantity": 1}
    ```
14. Wait ~5 seconds per booking (`PAYMENT_GATEWAY_DELAY_SECONDS`) — behind the scenes: order creation on `mock-razorpay` → capture → simulated webhook → real `/webhooks/razorpay` receiver → confirmation email logged by the worker. Then `GET /bookings/{id}` for each — `status` has flipped to `"CONFIRMED"`.
15. `POST /bookings/{id}/reviews` — using the booking for the **past** event (from step 13) once it's confirmed:
    ```json
    {"rating": 5, "review_text": "Great show!"}
    ```
    Returns `201`. Trying this on the booking from step 12 (the future-dated event) instead returns `400` — the event hasn't happened yet, which is a good thing to show off deliberately.
16. `GET /events/{id}/reviews` — using the past event's id — see the review returned.

## What's not driven through Swagger

The three mock Razorpay endpoints (`/mock/razorpay/orders`, `/mock/razorpay/payments/capture`, `/mock/razorpay/simulate-webhook`) live on the separate `mock-razorpay` service and are deliberately excluded from the OpenAPI docs — they aren't part of this API, they impersonate Razorpay's own servers. The real `/webhooks/razorpay` receiver *is* listed in Swagger but requires a valid HMAC signature that the UI can't compute, so it isn't practical to call by hand either. Neither needs to be touched manually — steps 12–13 above trigger the whole chain automatically.
