# EventBooking Demo — Bruno Collection

Same walkthrough as `DEMO.md` / `DEMO_SCRIPT.md`, as a runnable Bruno collection instead of Swagger UI. Request bodies are pre-filled; tokens and ids are captured automatically into collection variables as you go, so nothing needs to be copy-pasted by hand.

## Setup

1. Open Bruno → **Open Collection** → select this `bruno/` folder.
2. Select the **Local** environment (top right) — sets `baseUrl` to `http://localhost:5000` and `reviewEventOffsetSeconds` to `45`.
3. Make sure the stack is up (`docker compose up --build`) and migrations are applied (`docker compose run --rm app flask --app run db upgrade`).

## Run order

Folders are numbered to match the demo sequence — run requests top to bottom within each folder, in this folder order:

1. **auth** — register organizer → register customer → login organizer (captures `organizerToken`) → login customer (captures `customerToken`)
2. **events** — create main event (captures `eventId1`) → create review demo event (captures `eventId2`, date computed as now + `reviewEventOffsetSeconds`) → update main event → list events
3. **organizers** — update organizer profile
4. **bookings** — book main event (captures `bookingId1`) → book review demo event (captures `bookingId2`) → wait ~5s → get booking 1 → get booking 2
5. **reviews** — review future event (expect 400) → wait until the review demo event's date passes → review review-demo event (expect 201) → list event reviews

No manual copy-pasting of tokens/ids is needed — each request that needs one reads it from a variable set by an earlier request's `vars:post-response` block. If you re-run the collection from scratch, re-run `auth` first so the tokens refresh.
