from datetime import timedelta

from utils.time_format import format_duration


def test_format_duration_under_a_minute():
    assert format_duration(timedelta(seconds=5)) == "5s"


def test_format_duration_under_an_hour():
    assert format_duration(timedelta(minutes=2, seconds=5)) == "2m 5s"


def test_format_duration_under_a_day():
    assert format_duration(timedelta(hours=1, minutes=3)) == "1h 3m"


def test_format_duration_a_day_or_more():
    assert format_duration(timedelta(days=2, hours=4)) == "2d 4h"


def test_format_duration_clamps_negative_to_zero():
    assert format_duration(timedelta(seconds=-900)) == "0s"
