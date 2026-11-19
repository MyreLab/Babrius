import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))
from counter import describe, elapsed  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
