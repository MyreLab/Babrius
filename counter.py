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

ASSETS = Path(__file__).parent / "assets"
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


def total_days(start, now):
    """Whole days since start, counted on the local wall clock."""
    now = now.astimezone(start.tzinfo)
    days = (now.date() - start.date()).days
    return days - 1 if now.time() < start.time() else days


def plural(n, unit):
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"


def describe(months, days, hours):
    return ", ".join(
        [plural(months, "month"), plural(days, "day"), plural(hours, "hour")]
    )


PALETTES = {
    "light": {
        "fill": "#f8f6fd", "stroke": "#e0d9f2", "square": "#7f6bd0",
        "heading": "#6f58c4", "label": "#7a7491",
    },
    "dark": {
        "fill": "#1c1830", "stroke": "#352f52", "square": "#b8a4f0",
        "heading": "#c7b6f7", "label": "#a79fc4",
    },
}
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
CARD_WIDTH, CARD_HEIGHT, PAD, GRID_TOP, MAX_PITCH = 480, 160, 24, 56, 13


def card_svg(months, days, hours, total, theme):
    """One square per day, column by column. Today is outlined."""
    c = PALETTES[theme]
    cols = max(1, -(-(total + 1) // 7))
    pitch = min(MAX_PITCH, (CARD_WIDTH - 2 * PAD) / cols)
    size = round(pitch * 0.77, 2)
    squares = []
    for i in range(total + 1):
        x = round(PAD + (i // 7) * pitch, 2)
        y = round(GRID_TOP + (i % 7) * pitch, 2)
        if i < total:
            opacity = round(0.35 + 0.65 * (i / max(total - 1, 1)), 2)
            squares.append(
                f'    <rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill-opacity="{opacity}"/>'
            )
        else:
            squares.append(
                f'    <rect x="{x + 0.5}" y="{y + 0.5}" width="{round(size - 1, 2)}" height="{round(size - 1, 2)}" rx="2" '
                f'fill="none" stroke="{c["square"]}"/>'
            )
    text = describe(months, days, hours)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" font-family="{FONT}">
  <title>{text}</title>
  <desc>{plural(total, "day")} elapsed, one square per day</desc>
  <rect x="1" y="1" width="{CARD_WIDTH - 2}" height="{CARD_HEIGHT - 2}" rx="12" fill="{c["fill"]}" stroke="{c["stroke"]}"/>
  <text x="{PAD}" y="34" font-size="14" font-weight="600" fill="{c["heading"]}">Elapsed</text>
  <text x="{CARD_WIDTH - PAD}" y="34" font-size="13" text-anchor="end" fill="{c["label"]}">{text}</text>
  <g fill="{c["square"]}">
""" + "\n".join(squares) + """
  </g>
</svg>
"""


def write_cards(counts, total, directory=ASSETS):
    directory = Path(directory)
    directory.mkdir(exist_ok=True)
    for theme in PALETTES:
        (directory / f"clock-{theme}.svg").write_text(card_svg(*counts, total, theme))


def picture_block(text):
    return (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" srcset="assets/clock-dark.svg">\n'
        f'  <img alt="{text}" src="assets/clock-light.svg" width="480">\n'
        "</picture>"
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
    parser.add_argument(
        "--card", action="store_true", help="also draw the SVG cards and use them in the README"
    )
    args = parser.parse_args()

    start, now = load_start(), datetime.now(timezone.utc)
    counts = elapsed(start, now)
    text = describe(*counts)
    if args.card:
        write_cards(counts, total_days(start, now))
    if args.readme:
        block = picture_block(text) if args.card else f"**{text}**"
        update_readme(args.readme, block)
    print(text)


if __name__ == "__main__":
    main()
