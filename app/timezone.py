from datetime import datetime, timedelta, timezone

# All event dates are assumed IST (India-focused platform for now) — per-event/
# per-organizer timezone selection is deferred to v2. Requests are expected to
# send naive datetimes (no offset); one is never sent today (see DEMO.md /
# DEMO_SCRIPT.md / bruno/), so a date with an offset is rejected outright
# rather than converted.
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    """Current time as a naive datetime in IST wall-clock terms."""
    return datetime.now(IST).replace(tzinfo=None)
