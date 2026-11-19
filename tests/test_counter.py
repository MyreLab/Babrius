import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))
from counter import CARD_WIDTH, PALETTES, card_svg, describe, elapsed, picture_block, total_days  # noqa: E402

LA = ZoneInfo("America/Los_Angeles")
# A made-up start time, only used to exercise the maths.
T0 = datetime(2020, 1, 15, 9, 30, tzinfo=LA)


def at(*args):
    return datetime(*args, tzinfo=LA)


class ElapsedTests(unittest.TestCase):
    def test_moment_of_start(self):
        self.assertEqual(elapsed(T0, T0), (0, 0, 0))

    def test_first_hour_boundary(self):
        self.assertEqual(elapsed(T0, at(2020, 1, 15, 10, 29)), (0, 0, 0))
        self.assertEqual(elapsed(T0, at(2020, 1, 15, 10, 30)), (0, 0, 1))

    def test_month_rolls_over_at_start_time(self):
        self.assertEqual(elapsed(T0, at(2020, 2, 15, 9, 29)), (0, 30, 23))
        self.assertEqual(elapsed(T0, at(2020, 2, 15, 9, 30)), (1, 0, 0))

    def test_ordinary_day(self):
        self.assertEqual(elapsed(T0, at(2020, 7, 4, 12, 0)), (5, 19, 2))

    def test_month_end_is_clamped(self):
        start = datetime(2020, 1, 31, 9, 30, tzinfo=LA)
        self.assertEqual(elapsed(start, at(2020, 2, 29, 9, 29)), (0, 28, 23))
        self.assertEqual(elapsed(start, at(2020, 2, 29, 9, 30)), (1, 0, 0))

    def test_hours_use_real_elapsed_time_across_dst(self):
        # Clocks jumped forward at 2am on 2020-03-08, so there are 18 real
        # hours between Mar 7 09:30 and Mar 8 05:00, not 19.
        self.assertEqual(elapsed(T0, at(2020, 3, 8, 5, 0)), (1, 21, 18))

    def test_plural(self):
        self.assertEqual(describe(1, 1, 1), "1 month, 1 day, 1 hour")
        self.assertEqual(describe(5, 26, 20), "5 months, 26 days, 20 hours")

    def test_before_start_raises(self):
        with self.assertRaises(ValueError):
            elapsed(T0, at(2020, 1, 15, 9, 29))


class TotalDaysTests(unittest.TestCase):
    def test_counts_whole_days_on_the_wall_clock(self):
        self.assertEqual(total_days(T0, T0), 0)
        self.assertEqual(total_days(T0, at(2020, 1, 16, 9, 29)), 0)
        self.assertEqual(total_days(T0, at(2020, 1, 16, 9, 30)), 1)
        self.assertEqual(total_days(T0, at(2020, 7, 4, 12, 0)), 171)


class CardTests(unittest.TestCase):
    def squares(self, svg):
        return ET.fromstring(svg).findall(".//{http://www.w3.org/2000/svg}g/{http://www.w3.org/2000/svg}rect")

    def test_both_themes_are_valid_svg_with_one_square_per_day(self):
        for theme in PALETTES:
            svg = card_svg(5, 26, 20, 186, theme)
            self.assertTrue(ET.fromstring(svg).tag.endswith("svg"))
            self.assertEqual(len(self.squares(svg)), 187)
            self.assertIn("5 months, 26 days, 20 hours", svg)

    def test_today_is_the_only_outlined_square(self):
        outlined = [r for r in self.squares(card_svg(0, 3, 1, 3, "light")) if r.get("fill") == "none"]
        self.assertEqual(len(outlined), 1)

    def test_grid_stays_inside_the_card_as_it_grows(self):
        for total in (0, 1, 186, 365, 800):
            for rect in self.squares(card_svg(0, 0, 0, total, "dark")):
                right = float(rect.get("x")) + float(rect.get("width"))
                self.assertLessEqual(right, CARD_WIDTH - 20)

    def test_picture_block_carries_the_text_as_alt(self):
        block = picture_block("5 months, 26 days, 20 hours")
        self.assertIn('alt="5 months, 26 days, 20 hours"', block)
        self.assertIn("prefers-color-scheme: dark", block)


if __name__ == "__main__":
    unittest.main()
