from datetime import datetime, timedelta, timezone

# All event dates are assumed IST (India-focused platform for now) — per-event/
# per-organizer timezone selection is deferred to v2.
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    """Current time as a naive datetime in IST wall-clock terms."""
    return datetime.now(IST).replace(tzinfo=None)


def to_naive_ist(dt):
    """Normalize any datetime (aware or naive) to naive IST wall-clock time.

    A naive input is assumed to already be IST. An aware input is converted
    to IST first — this is what prevents comparing a naive `now` against an
    aware client-supplied date (which raises TypeError).
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(IST)
    return dt.replace(tzinfo=None)
