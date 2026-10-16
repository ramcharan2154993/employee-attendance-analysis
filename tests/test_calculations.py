"""Tests for attendance calculation functions."""

import pytest
from src.calculations import (
    calculate_absenteeism_percentage,
    calculate_attendance_percentage,
    eligible_days,
    format_percentage,
)


def test_standard_case():
    """15 Present, 3 Absent, 2 Leave: eligible_days = 20, attendance = 75.0, absenteeism = 15.0."""
    assert eligible_days(15, 3, 2) == 20
    assert calculate_attendance_percentage(15, 3, 2) == 75.0
    assert calculate_absenteeism_percentage(15, 3, 2) == 15.0


def test_perfect_attendance():
    """10 Present, 0 Absent, 0 Leave: attendance = 100.0, absenteeism = 0.0."""
    assert calculate_attendance_percentage(10, 0, 0) == 100.0
    assert calculate_absenteeism_percentage(10, 0, 0) == 0.0


def test_all_absent():
    """0 Present, 5 Absent, 0 Leave: attendance = 0.0, absenteeism = 100.0."""
    assert calculate_attendance_percentage(0, 5, 0) == 0.0
    assert calculate_absenteeism_percentage(0, 5, 0) == 100.0


def test_mixed_days():
    """8 Present, 1 Absent, 1 Leave: attendance = 80.0, absenteeism = 10.0."""
    assert calculate_attendance_percentage(8, 1, 1) == 80.0
    assert calculate_absenteeism_percentage(8, 1, 1) == 10.0


def test_zero_eligible_days():
    """0, 0, 0: attendance is None, absenteeism is None (no error raised)."""
    assert eligible_days(0, 0, 0) == 0
    assert calculate_attendance_percentage(0, 0, 0) is None
    assert calculate_absenteeism_percentage(0, 0, 0) is None


def test_raw_value_unrounded_and_formatted():
    """1, 1, 1: format_percentage(attendance) == '33.33%' (and the raw value is NOT rounded)."""
    attendance = calculate_attendance_percentage(1, 1, 1)
    assert attendance is not None
    assert attendance != 33.33
    assert attendance == (1 / 3) * 100
    assert format_percentage(attendance) == "33.33%"


def test_format_percentage_none():
    """format_percentage(None) == 'N/A'."""
    assert format_percentage(None) == "N/A"


def test_format_percentage_float():
    """format_percentage(75.0) == '75.00%'."""
    assert format_percentage(75.0) == "75.00%"


def test_negative_counts_raise_value_error():
    """A negative count raises ValueError (test all three parameters)."""
    # Negative present
    with pytest.raises(ValueError):
        eligible_days(-1, 0, 0)
    with pytest.raises(ValueError):
        calculate_attendance_percentage(-1, 0, 0)
    with pytest.raises(ValueError):
        calculate_absenteeism_percentage(-1, 0, 0)

    # Negative absent
    with pytest.raises(ValueError):
        eligible_days(0, -1, 0)
    with pytest.raises(ValueError):
        calculate_attendance_percentage(0, -1, 0)
    with pytest.raises(ValueError):
        calculate_absenteeism_percentage(0, -1, 0)

    # Negative leave
    with pytest.raises(ValueError):
        eligible_days(0, 0, -1)
    with pytest.raises(ValueError):
        calculate_attendance_percentage(0, 0, -1)
    with pytest.raises(ValueError):
        calculate_absenteeism_percentage(0, 0, -1)
