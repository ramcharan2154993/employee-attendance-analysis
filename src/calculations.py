"""Attendance and absenteeism calculation functions."""


def _validate_counts(present: int, absent: int, leave: int) -> None:
    """Validate that attendance counts are non-negative integers."""
    if present < 0:
        raise ValueError(f"Present count cannot be negative: {present}")
    if absent < 0:
        raise ValueError(f"Absent count cannot be negative: {absent}")
    if leave < 0:
        raise ValueError(f"Leave count cannot be negative: {leave}")


def _percentage(numerator: int, denominator: int) -> float | None:
    """Calculate percentage from numerator and denominator, or None if denominator is 0."""
    if denominator == 0:
        return None
    return (numerator / denominator) * 100


def eligible_days(present: int, absent: int, leave: int) -> int:
    """Calculate total eligible working days (Present + Absent + Leave)."""
    _validate_counts(present, absent, leave)
    return present + absent + leave


def calculate_attendance_percentage(
    present: int, absent: int, leave: int
) -> float | None:
    """Calculate attendance percentage based on eligible working days."""
    _validate_counts(present, absent, leave)
    return _percentage(present, eligible_days(present, absent, leave))


def calculate_absenteeism_percentage(
    present: int, absent: int, leave: int
) -> float | None:
    """Calculate absenteeism percentage based on eligible working days."""
    _validate_counts(present, absent, leave)
    return _percentage(absent, eligible_days(present, absent, leave))


def format_percentage(value: float | None) -> str:
    """Format a percentage float to two decimal places with a % symbol, or 'N/A' if None."""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"
