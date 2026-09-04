# Event Booking System

A backend-only REST API for booking event tickets, with two roles — **Event Organizer** (manages events) and **Customer** (browses events, books tickets, pays via a mocked Razorpay flow). No frontend in scope.

Full design rationale (data model, payment flow, deferred items) lives in [`PLAN.md`](PLAN.md). Architecture and coding conventions live in [`CLAUDE.md`](CLAUDE.md).

## Tech Stack

- **Framework**: Flask
- **Validation**: Pydantic, wired through [spectree](https://github.com/0b01001001/spectree) — request schemas double as the OpenAPI spec
- **Database**: PostgreSQL via SQLAlchemy
- **Background jobs**: Celery, broker = Redis
- **Auth**: JWT (Flask-JWT-Extended), stateless, 2-day default expiry (configurable)
- **Containerization**: Docker / docker-compose

## Architecture

Layered — **Controller** (HTTP) → **Service** (business logic) → **Repository** (DB access) — organized **domain-first**: each domain (`app/users/`, `app/events/`, `app/bookings/`, `app/payments/`, `app/jobs/`) owns its own `model.py`, `dao_interface.py`, `repository.py`, `service.py`, `controller.py`.

```
app/
├── users/       registration, login, JWT issuance
├── events/      event catalog (organizer-managed, browsable by city)
├── bookings/    ticket booking, capacity enforcement
├── payments/    real webhook receiver + gateway_client.py (calls the mock service below)
└── jobs/        Celery task audit log (DB-only, no API)
```

The mock Razorpay API (`app/payments/mock_controller.py`) runs as its own service (`mock-razorpay`, entrypoint `mock_razorpay_app.py`) rather than living inside the main app. `POST /bookings` and the async payment flow make real outbound HTTP calls to it (order creation, payment capture, webhook delivery) — if it lived in the same process as the API, that self-call would deadlock a single-worker gunicorn (the one worker would be both the caller and the callee). Running it as a separate service also just mirrors reality: the real Razorpay is a separate company's servers, never the same process as your app.

## Running it

```bash
cp .env.example .env.local   # fill in real values
docker compose up --build -d db redis mock-razorpay
docker compose run --rm app flask --app run db upgrade   # explicit, manual — see below
docker compose up --build
```

This starts `app` (API, port 5000), `worker` (Celery), `mock-razorpay` (the mocked gateway, internal only — no host port), `flower` (Celery monitoring, port 5555), `db` (Postgres), and `redis`.

### Database migrations

Everything runs through docker compose — there's no local Python environment for this project.

```bash
# after changing a model: generate a new migration (bind-mounts migrations/ so the
# generated file lands on your host filesystem, not just inside the container — this
# mount is scoped to this one-off command, not a standing volume in docker-compose.yml)
docker compose run --rm --volume "$(pwd)/migrations:/app/migrations" app flask --app run db migrate -m "description"

# apply it — a separate, manual, explicit step, deliberately NOT wired into the
# app service's boot command: upgrading is tied to whether a new migration exists,
# not to the app process's lifecycle, so it shouldn't fire on every container start
docker compose run --rm app flask --app run db upgrade
```

## API Docs

Once running, the OpenAPI spec is auto-generated from the Pydantic schemas — no hand-maintained spec to drift out of sync:

- Swagger UI: `/apidoc/swagger/`
- ReDoc: `/apidoc/redoc/`
- Raw spec: `/apidoc/openapi.json`

### Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/register` | — | `role`: `customer` \| `organizer` |
| POST | `/auth/login` | — | returns JWT |
| POST | `/events` | JWT, organizer | create event |
| GET | `/events` | JWT | list/browse, optional `?city=` filter |
| GET | `/events/:id` | JWT | event detail |
| PATCH | `/events/:id` | JWT, organizer (own events) | triggers event-update notification |
| POST | `/bookings` | JWT, customer | checks capacity, kicks off payment flow |
| GET | `/bookings` | JWT, customer | own bookings |
| GET | `/bookings/:id` | JWT, customer | own booking detail |
| POST | `/webhooks/razorpay` | HMAC signature | real webhook receiver |

Three more endpoints exist as throwaway stand-ins for Razorpay's own servers, deliberately excluded from the docs above since they aren't part of this API — they run on the separate `mock-razorpay` service, not `app`:
- `POST /mock/razorpay/orders` (HTTP Basic Auth via `RAZORPAY_KEY_ID`/`KEY_SECRET`) — mocks Razorpay's real Orders API, called by `POST /bookings` to get an `order_id` before creating the booking's payment record
- `POST /mock/razorpay/payments/capture` (same Basic Auth) — mocks Razorpay's Payment Capture API, called by the async payment flow
- `POST /mock/razorpay/simulate-webhook` (`x-api-key` protected) — mocks Razorpay delivering a webhook back to `app`'s real `/webhooks/razorpay`

## Testing

```bash
docker compose run --rm test
```

Runs via a dedicated `test` service (`Dockerfile.test`, profile-gated so `docker compose up` never starts it) — no local Python needed. It deliberately doesn't use `.env.local`, so it falls back to `tests/conftest.py`'s own isolated defaults (sqlite in-memory, fresh every run) instead of hitting the real dev Postgres/Redis.

Unit tests use pytest with parametrization, plus in-memory fake repositories for isolating service-layer logic from the database.
