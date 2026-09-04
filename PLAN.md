# Event Booking System — Plan

## Tech Stack (frozen)
- **Framework**: Flask
- **Database**: PostgreSQL, queried via **SQLAlchemy** (used at the Repository layer)
- **Background jobs**: Celery, broker = Redis (frozen)
- **Containerization**: Docker / docker-compose
- **Auth**: JWT (Flask-JWT-Extended), required on all customer/organizer-facing endpoints. The Razorpay (mocked) webhook receiver is the one exception — signature-verified instead of JWT, matching how real gateway webhooks are secured.

## Conventions (frozen)
- Every table has `created_at` and `updated_at` timestamps.
- **Architecture**: layered — Controller (HTTP interaction) → Service (core business logic) → Repository (DB access).
- `RAZORPAY_MODE` confirmed as the env var name for test/prod credential switching.

## Roles (frozen)
- **Event Organizer** — manages events
- **Customer** — browses events, books tickets
- Access control enforced per-role on every endpoint

## Background Tasks (frozen)

### 1. Booking Confirmation
- Trigger: customer successfully books ticket(s)
- Action: simulate sending confirmation email (console log / print)
- Runs async via Celery, off the request path

### 2. Event Update Notification
- Trigger: organizer updates an event
- Action: notify all customers who booked tickets for that event (console log / print per customer)
- Runs async via Celery, off the request path

## Data Model — Customer Side (partial, relationships frozen)

- **User** — shared by both roles (frozen)
  - `id`, `email`, `phone`, `password_hash`, `role` (`customer` | `organizer`), `created_at`, `updated_at`
  - Auth: password-based only (no Google/OAuth sign-in — backend-only API, no frontend in scope, and OAuth is a frontend-driven flow anyway)
- **Event** — event catalog, managed by Organizer (frozen)
  - `id`, `user_id` (FK → User, the organizer who created it), `name`, `date`, `venue`, `city` (required — browsing is filtered by this), `capacity`, `tickets_sold`, `price`, `created_at`, `updated_at`. Remaining capacity = `capacity - tickets_sold`.
- **Booking** — resolves User↔Event many-to-many; one row = one user's booking for one event
  - `id`, `user_id` (FK → User), `event_id` (FK → Event), `quantity`, `created_at`, `updated_at`
  - No `status` field — derived via the relationship to `Payment.status` (`PROCESSED` → confirmed, `FAILED` → failed, else pending). `Payment.status` is the single source of truth, avoiding duplicate/driftable state.
- **Payment** — 1:1 with Booking (a booking is paid for exactly once)
  - `id`, `booking_id` (FK → Booking, unique), `amount`, `order_id` (gateway-issued reference, for correlating inbound webhook payloads back to this row), `gateway_status` (mirrors Razorpay: `created` → `captured`), `status` (internal: `PENDING` → `REQUESTED` → `PROCESSED` | `FAILED`), `created_at`, `updated_at` — frozen (see Payment Flow below for status semantics)

```
User (1)──< Booking >──(1) Event
                 |
              (1:1)
                 |
              Payment
```

## Payment Flow (mocked Razorpay, frozen)

No real payment gateway integration — Razorpay is simulated on both sides (outbound order creation and inbound webhook delivery), but the flow mirrors how a real integration would work so the webhook receiver and the order-creation caller are genuine, reusable code — only the two mock endpoints they talk to (`/mock/razorpay/orders`, `/mock/razorpay/simulate-webhook`) are throwaway.

Payment's status fields (`gateway_status`, `status`) and `order_id` are defined in the Data Model above.

**Flow**:
1. Booking created (sync, in-request) → calls `POST /mock/razorpay/orders` (mocked Razorpay Orders API, HTTP Basic Auth via `RAZORPAY_KEY_ID`/`KEY_SECRET` — same credentials a real `razorpay-python` client would use) to get a gateway-issued `order_id`, then creates the `Payment` row: `status=PENDING`, `gateway_status=created`. If the order-creation call fails, the whole booking rolls back (no partial state) and the API returns a clean `502`.
2. Celery Task A runs: sets `status=REQUESTED`, `gateway_status=captured` (simulates the request reaching the gateway). Schedules a follow-up trigger via `countdown=N` to simulate gateway processing latency.
3. On the delayed trigger firing, a **mock endpoint** (e.g. `POST /mock/razorpay/simulate-webhook`) builds a fake Razorpay event payload — including `order_id` and a fake signature — and calls the **real webhook receiver** via an actual HTTP request — this is the only throwaway piece.
4. **Webhook receiver** (e.g. `POST /webhooks/razorpay`) — genuine, reusable code (would be unchanged if a real Razorpay integration replaced the mock trigger later). Verifies the signature (not JWT), looks up `Payment` by `order_id`, updates `status` to `PROCESSED` or `FAILED` and `gateway_status` accordingly.
5. Only on `PROCESSED`: enqueues the **Booking Confirmation** Celery task (see Background Tasks above). `FAILED` leaves the booking unconfirmed, no email sent.

**Operational note**: the mock trigger's HTTP self-call means the Celery worker container needs network reachability to the app service (e.g. `http://app:5000/webhooks/razorpay` in docker-compose) — factor into Docker compose service design.

**Tenancy (frozen)**: single-tenant — one platform-level Razorpay account (one `RAZORPAY_KEY_ID`/`SECRET` pair per environment: test/prod), matching how real aggregator platforms typically work (aggregator holds the single gateway link; organizer payout is routed internally, not via per-organizer gateway accounts). Organizer settlement/payout (internal ledger/balance tracking) is **deferred** — out of scope for the core build.

## Job Tracking (frozen)

- **`jobs` table** — generic, permanent record of every Celery task run in the system (booking confirmation, event update notification, all payment-flow steps). Complements Flower (Flower = live/ephemeral ops visibility; `jobs` table = permanent app-level audit record) — not a replacement.
- **Fields (frozen)**: `id`, `task_id` (Celery's UUID), `task_name`, `status`, `event_id`, `payment_id`, `created_at`, `updated_at`. `event_id`/`payment_id` are plain FKs, not unique — many `jobs` rows can reference the same event or payment (one row per task execution, e.g. every event update creates a new row; a payment's multi-step flow creates several).
- **No API exposure (frozen)**: `jobs` is DB-queryable only — no endpoint, not customer/organizer-facing. Internal/debugging use only.

## JWT (frozen)
- Expiry: **configurable** (env var, not hardcoded), default value **2 days**
- Revocation: **none** — token just naturally expires, confirmed

## Mock Trigger Endpoint Auth (frozen)
- `POST /mock/razorpay/simulate-webhook` protected via **x-api-key** header (separate from JWT, since this isn't a customer/organizer-facing endpoint)

## Booking Rules (frozen)
- Always check capacity **before** allowing a booking
- On successful booking, update `Event`'s sold count / remaining capacity

## Testing (frozen)
- Unit tests (pytest, using parametrization) + manual testing for now

## Endpoint List (frozen)

**Auth**
- `POST /auth/register` — create `User` (role in body: `customer` | `organizer`)
- `POST /auth/login` — email + password → JWT

**Events**
- `POST /events` — create event (organizer only)
- `GET /events` — list events (browse, both roles), optional filters: `?city=` (exact match), `?date_from=`/`?date_to=` (inclusive date range), `?industry=` (via the event's organizer profile) — no free-text search
- `GET /events/:id` — event detail
- `PATCH /events/:id` — update event (organizer only, own events) — triggers Event Update Notification task
- `DELETE /events/:id` — delete event (organizer only, own events) — only allowed if the event has zero bookings (`tickets_sold == 0`); `409` otherwise, to avoid needing cancellation/refund handling

**Bookings**
- `POST /bookings` — book an event (customer only) — checks capacity, creates `Booking` + `Payment`, kicks off payment flow
- `GET /bookings` — list own bookings (customer only)
- `GET /bookings/:id` — booking detail (customer only, own booking)
- Cancellation: **out of scope** (confirmed)

**Payment (system-facing, not JWT)**
- `POST /webhooks/razorpay` — real webhook receiver, signature-verified (see Webhook Signature Scheme below)
- `POST /mock/razorpay/simulate-webhook` — mock trigger, `x-api-key` protected
- `POST /mock/razorpay/orders` — mocked Razorpay Orders API, HTTP Basic Auth (`RAZORPAY_KEY_ID`/`KEY_SECRET`)

## Webhook Signature Scheme (frozen)
Mirrors real Razorpay: HMAC-SHA256 over the raw request body, shared secret from env var `RAZORPAY_WEBHOOK_SECRET`, signature sent/verified via the `X-Razorpay-Signature` header.

## Docker Compose Services (frozen)

- **`app`** — Flask app (Gunicorn), exposes the API. Needs network reachability from `worker` (for the mock trigger's self-call to `/webhooks/razorpay`).
- **`worker`** — Celery worker, runs all background tasks (booking confirmation, event update notification, payment flow steps).
- **`flower`** — Celery monitoring dashboard (dev/ops visibility only, per Job Tracking above).
- **`db`** — PostgreSQL.
- **`redis`** — Celery broker.
- Env: `.env.local` for dev (git-ignored, protected by the existing PreToolUse hook), `.env.prod` overrides for production.

## Deferred (out of scope for core build)
- **Organizer settlement/payout ledger** — planned for v2, not this build.
- **Razorpay Route / true multi-tenant per-organizer gateway accounts** — dropped entirely, not planned at all (single-tenant is the permanent design, not just a v1 stopgap).
- **Free-text search on events** — filters only (`city`, `date_from`/`date_to`, `industry`); planned for v2.
- **Pagination** on `GET /events` and `GET /bookings` — planned for v2.
- **Explicit DB indexes** on `Event.city`/`date`/`user_id`, `Booking.user_id`/`event_id`, `OrganizerProfile.user_id` — planned for v2, ahead of any real scale.
- **Health-check endpoint** for load balancer / orchestrator probes — planned for v2.
- **Stronger password policy** on registration — planned for v2.

---
*Core plan fully frozen — nothing left in Open/To Be Frozen. Only the Deferred items above remain out of scope by design. Ready to move to implementation.*
