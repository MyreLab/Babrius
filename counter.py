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


def plural(n, unit):
    return f"{n} {unit}" if n == 1 else f"{n} {unit}s"


def describe(months, days, hours):
    return ", ".join(
        [plural(months, "month"), plural(days, "day"), plural(hours, "hour")]
    )


PALETTES = {
    "light": {"fill": "#f6f8fa", "stroke": "#d0d7de", "number": "#1f2328", "label": "#656d76", "accent": "#1a7f37"},
    "dark": {"fill": "#161b22", "stroke": "#30363d", "number": "#e6edf3", "label": "#8b949e", "accent": "#3fb950"},
}
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def card_svg(months, days, hours, theme):
    c = PALETTES[theme]
    columns = [(months, "month"), (days, "day"), (hours, "hour")]
    cells = []
    for i, (n, unit) in enumerate(columns):
        x = 90 + i * 150
        label = unit if n == 1 else unit + "s"
        cells.append(
            f'  <text x="{x}" y="86" text-anchor="middle" font-size="42" font-weight="600" fill="{c["number"]}">{n}</text>\n'
            f'  <text x="{x}" y="110" text-anchor="middle" font-size="13" fill="{c["label"]}">{label}</text>'
        )
    dividers = "\n".join(
        f'  <line x1="{x}" y1="52" x2="{x}" y2="112" stroke="{c["stroke"]}"/>' for x in (165, 315)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="130" viewBox="0 0 480 130" role="img" font-family="{FONT}">
  <title>{describe(months, days, hours)}</title>
  <rect x="1" y="1" width="478" height="128" rx="12" fill="{c["fill"]}" stroke="{c["stroke"]}"/>
  <text x="24" y="32" font-size="14" font-weight="600" fill="{c["accent"]}">Elapsed</text>
{dividers}
""" + "\n".join(cells) + "\n</svg>\n"


def write_cards(counts, directory=ASSETS):
    directory = Path(directory)
    directory.mkdir(exist_ok=True)
    for theme in PALETTES:
        (directory / f"clock-{theme}.svg").write_text(card_svg(*counts, theme))


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

    counts = elapsed(load_start(), datetime.now(timezone.utc))
    text = describe(*counts)
    if args.card:
        write_cards(counts)
    if args.readme:
        block = picture_block(text) if args.card else f"**{text}**"
        update_readme(args.readme, block)
    print(text)


if __name__ == "__main__":
    main()
