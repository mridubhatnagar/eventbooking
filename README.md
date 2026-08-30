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
├── payments/    mocked Razorpay flow, webhook receiver
└── jobs/        Celery task audit log (DB-only, no API)
```

## Running it

```bash
cp .env.example .env.local   # fill in real values
docker compose up --build
```

This starts `web` (API, port 5000), `worker` (Celery), `flower` (Celery monitoring, port 5555), `db` (Postgres), and `redis`.

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

`POST /mock/razorpay/simulate-webhook` also exists (`x-api-key` protected) as a throwaway stand-in for Razorpay's servers during local/dev testing — it's deliberately excluded from the docs above since it isn't a real API surface.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Unit tests use pytest with parametrization, plus in-memory fake repositories for isolating service-layer logic from the database.
