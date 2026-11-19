"""Elapsed-time counter: whole calendar months, then days, then hours since a start time.

The start time and time zone come from the CLOCK_START and CLOCK_TZ environment
variables (repository secrets in GitHub Actions), so they are not stored in the
repo.

Months and days are counted on the local wall clock. The leftover hours are
measured in real elapsed time, so a daylight saving change never shifts the
answer by an hour.
"""
import argparse
import calendar
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

MARK_OPEN = "<!-- CLOCK:START -->"
MARK_CLOSE = "<!-- CLOCK:END -->"


def load_start():
    try:
        raw, tz_name = os.environ["CLOCK_START"], os.environ["CLOCK_TZ"]
    except KeyError as missing:
        raise SystemExit(f"{missing.args[0]} is not set")
    return datetime.fromisoformat(raw).replace(tzinfo=ZoneInfo(tz_name))


def add_months(dt, months):
    total = dt.year * 12 + (dt.month - 1) + months
    year, month = divmod(total, 12)
    day = min(dt.day, calendar.monthrange(year, month + 1)[1])
    return dt.replace(year=year, month=month + 1, day=day)


def elapsed(start, now):
    """Return (months, days, hours) between start and now."""
    tz = start.tzinfo
    now = now.astimezone(tz)
    if now < start:
        raise ValueError("now is before start")

    months = (now.year - start.year) * 12 + now.month - start.month
    if add_months(start, months) > now:
        months -= 1
    anchor = add_months(start, months)

    days = (now.date() - anchor.date()).days
    day_anchor = datetime.combine(anchor.date() + timedelta(days=days), anchor.time(), tz)
    if day_anchor > now:
        days -= 1
        day_anchor = datetime.combine(anchor.date() + timedelta(days=days), anchor.time(), tz)

    real = now.astimezone(timezone.utc) - day_anchor.astimezone(timezone.utc)
    hours = int(real.total_seconds() // 3600)
    return months, days, hours


def plural(n, unit):
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"


def describe(months, days, hours):
    return ", ".join(
        [plural(months, "month"), plural(days, "day"), plural(hours, "hour")]
    )


def update_readme(path, text):
    content = Path(path).read_text()
    head, _, rest = content.partition(MARK_OPEN)
    _, _, tail = rest.partition(MARK_CLOSE)
    if not rest:
        raise SystemExit(f"markers not found in {path}")
    Path(path).write_text(f"{head}{MARK_OPEN}\n{text}\n{MARK_CLOSE}{tail}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", help="rewrite the CLOCK block in this file")
    args = parser.parse_args()

    text = describe(*elapsed(load_start(), datetime.now(timezone.utc)))
    if args.readme:
        update_readme(args.readme, f"**{text}**")
    print(text)


if __name__ == "__main__":
    main()
