# CLAUDE.md

Event Booking System — backend-only REST API (no frontend in scope). Two roles: Event Organizer (manages events) and Customer (browses/books). Full design lives in `PLAN.md` — read it before implementing; this file is a quick-reference summary.

## Tech Stack
- **Framework**: Flask
- **Request validation**: Pydantic (per-domain `schemas.py`, see Key Conventions)
- **Database**: PostgreSQL, queried via **SQLAlchemy** (Repository layer)
- **Background jobs**: Celery, broker = Redis
- **Containerization**: Docker / docker-compose (`web`, `worker`, `flower`, `db`, `redis` services)

## Architecture
Layered: **Controller** (HTTP interaction) → **Service** (core business logic) → **Repository** (DB access).

**Folder structure is domain-first, not layer-first**: each domain (`app/users/`, `app/events/`, `app/bookings/`, `app/payments/`, `app/jobs/`) is self-contained with its own `model.py`, `dao_interface.py`, `repository.py`, `service.py`, `controller.py` inside it — not one global `models/`/`services/`/`controllers/` folder each holding every domain's files. `app/config.py`, `app/extensions.py`, `app/base.py` (shared `TimestampMixin`), `app/decorators.py` (`role_required` RBAC guard), `app/dao_interface.py` (`BaseDAO`) stay at the `app/` root since they're app-wide, not domain-specific. Cross-domain ORM relationships (e.g. `Booking.payment`) are resolved via class-name strings to avoid direct imports between domain modules.

**Repository/DAO pattern is two-tier**: `app/dao_interface.py` defines `BaseDAO` (ABC, generic `create`/`update`/`list`). Each domain's `dao_interface.py` defines `IDAO(BaseDAO)`, adding domain-specific abstract methods (e.g. `get_by_email` for Users). Each domain's `repository.py` implements that domain's `IDAO` (e.g. `UserRepository(IDAO)`). Follow this pattern for every new domain's repository.

## Engineering Principles
Follow software engineering best practices — **YAGNI** (don't build for hypothetical future needs), **KISS** (prefer the simplest solution that works), and **DRY** (don't duplicate logic — reuse via the Service/Repository layers). Implement exactly what's in `PLAN.md`, nothing more.

## Key Conventions
- Every table has `created_at` and `updated_at`.
- Auth: JWT (Flask-JWT-Extended), stateless, no revocation (natural expiry only), default expiry 2 days (configurable via env var). Password-based login only — no OAuth/Google sign-in.
- `Payment.status` is the single source of truth for booking/payment outcome — `Booking` has no separate `status` field, it's derived via the relationship.
- Env vars: `RAZORPAY_MODE` (test/prod switching), `RAZORPAY_WEBHOOK_SECRET` (webhook HMAC signing). Secrets live in `.env.local` (dev, git-ignored, protected by a PreToolUse hook) / `.env.prod` (prod overrides).
- The Razorpay webhook receiver (`POST /webhooks/razorpay`) uses signature verification (HMAC-SHA256, `X-Razorpay-Signature` header), not JWT. The mock trigger endpoint (`POST /mock/razorpay/simulate-webhook`) uses `x-api-key`, also not JWT. It's a test-only stand-in for Razorpay's servers, not a real API surface, so it deliberately skips `@api.validate` (manual `WebhookRequest.model_validate()` + `pydantic.ValidationError` → `400` instead) so it's excluded from the OpenAPI/Swagger docs — see API Docs below.
- The `jobs` table (generic Celery task audit log) is DB-queryable only — never expose it via an API endpoint.
- **Never hardcode status/role string literals.** All of them (`Role`, `PaymentStatus`, `GatewayStatus`, `BookingStatus`, `JobStatus`, `WebhookEvent`) live in `app/enums.py` (`StrEnum`) and must be imported from there — in models, services, tasks, controllers, everywhere.
- **Request validation uses Pydantic via spectree, not manual `request.get_json()` + field checks.** Each domain has a `schemas.py` with its request models (e.g. `app/events/schemas.py: CreateEventRequest`). Controllers decorate the view with `@api.validate(json=SchemaCls, tags=[...])` (`api` from `app/docs.py`) and read the validated instance from `request.context.json`. This also auto-generates OpenAPI docs — every endpoint with a body must have this decorator (add `@api.validate(tags=[...])` with no `json=` for GET-only endpoints too, so they're still documented). Validation failures return `400` (configured via `validation_error_status` in `app/docs.py`, matching the rest of the API's error convention).
- **Celery `.delay()`/`.apply_async()` failures must be loud, never silently swallowed.** Every call site that enqueues a task after a DB write is already committed wraps the call in try/except and re-raises as `app.exceptions.TaskEnqueueError` (see `app/__init__.py`'s error handler — returns a clean `503` JSON response, not a raw traceback). Follow this pattern for any new task trigger.

## API Docs
OpenAPI spec auto-generated from the Pydantic schemas via **spectree** — no separate hand-maintained spec. Live at `/apidoc/openapi.json`, with Swagger UI at `/apidoc/swagger/` (also ReDoc at `/apidoc/redoc/` and Scalar at `/apidoc/scalar/`, bundled by spectree by default). `api = SpecTree(..., mode="strict")` (`app/docs.py`) — in strict mode only routes decorated with `@api.validate` appear in the spec at all (spectree's default `"normal"` mode would otherwise still list *undecorated* routes, just without docs). This is how `/mock/razorpay/simulate-webhook` stays a real, reachable, `x-api-key`-protected route while being fully absent from the public API docs. Any future internal/test-only endpoint should follow the same pattern: skip `@api.validate`, validate manually with the Pydantic model if needed.

## Testing
Unit tests use **pytest** with **parametrization** (`@pytest.mark.parametrize`), plus manual testing.

See `PLAN.md` for the full design (data model, payment flow, endpoint list, Docker Compose layout, deferred items).
