"""Tests for analysis and aggregation functions."""

import datetime
import numpy as np
import pandas as pd
import pytest
from src.analysis import (
    absenteeism_ranking,
    department_summary,
    employee_summary,
    load_attendance_df,
    monthly_summary,
)
from src.attendance import record_attendance
from src.employees import add_employee


def _create_sample_df() -> pd.DataFrame:
    """Helper creating hand-built test DataFrame with known attendance counts."""
    rows = []
    # E001 (Engineering): 15 Present, 3 Absent, 2 Leave, 2 Holiday
    for _ in range(15):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 1),
            "status": "Present",
        })
    for _ in range(3):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 2),
            "status": "Absent",
        })
    for _ in range(2):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 3),
            "status": "Leave",
        })
    for _ in range(2):
        rows.append({
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 14),
            "status": "Holiday",
        })

    # E002 (Engineering): 5 Present, 5 Absent, 0 Leave, 0 Holiday
    for _ in range(5):
        rows.append({
            "employee_code": "E002",
            "employee_name": "Ravi Kumar",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 1),
            "status": "Present",
        })
    for _ in range(5):
        rows.append({
            "employee_code": "E002",
            "employee_name": "Ravi Kumar",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 2),
            "status": "Absent",
        })

    # E003 (HR): 1 Holiday only
    rows.append({
        "employee_code": "E003",
        "employee_name": "Divya Menon",
        "department": "HR",
        "is_active": True,
        "attendance_date": datetime.date(2026, 9, 14),
        "status": "Holiday",
    })

    return pd.DataFrame(rows)


def test_pure_employee_summary():
    """E001: eligible 20, attendance 75.0, absenteeism 15.0; E002: 10, 50.0, 50.0; E003: 0, NaNs, holiday 1."""
    df = _create_sample_df()
    es = employee_summary(df)

    # E001
    e1 = es[es["employee_code"] == "E001"].iloc[0]
    assert e1["eligible_days"] == 20
    assert e1["attendance_pct"] == 75.0
    assert e1["absenteeism_pct"] == 15.0
    assert e1["holiday"] == 2

    # E002
    e2 = es[es["employee_code"] == "E002"].iloc[0]
    assert e2["eligible_days"] == 10
    assert e2["attendance_pct"] == 50.0
    assert e2["absenteeism_pct"] == 50.0

    # E003
    e3 = es[es["employee_code"] == "E003"].iloc[0]
    assert e3["eligible_days"] == 0
    assert e3["holiday"] == 1
    assert np.isnan(e3["attendance_pct"])
    assert np.isnan(e3["absenteeism_pct"])


def test_pure_department_summary():
    """Engineering: 20 present, 8 absent, 2 leave, 30 eligible, attendance ~66.6667 (NOT 62.5); HR eligible 0, NaNs."""
    df = _create_sample_df()
    dept = department_summary(df)

    eng = dept[dept["department"] == "Engineering"].iloc[0]
    assert eng["present"] == 20
    assert eng["absent"] == 8
    assert eng["leave"] == 2
    assert eng["eligible_days"] == 30
    assert pytest.approx(66.6667, abs=1e-4) == eng["attendance_pct"]
    assert eng["attendance_pct"] != 62.5  # Must not be the wrong average-of-percentages answer

    hr = dept[dept["department"] == "HR"].iloc[0]
    assert hr["eligible_days"] == 0
    assert np.isnan(hr["attendance_pct"])
    assert np.isnan(hr["absenteeism_pct"])


def test_pure_monthly_summary():
    """Monthly summary with dates in 2026-09 and 2026-10."""
    rows = [
        {
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 9, 30),
            "status": "Present",
        },
        {
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 10, 1),
            "status": "Absent",
        },
        {
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 10, 2),
            "status": "Present",
        },
        {
            "employee_code": "E001",
            "employee_name": "Asha Rao",
            "department": "Engineering",
            "is_active": True,
            "attendance_date": datetime.date(2026, 10, 5),
            "status": "Leave",
        },
    ]
    df = pd.DataFrame(rows)
    m = monthly_summary(df)

    # 2026-09: eligible 1, attendance 100.0
    m_sep = m[m["month"] == "2026-09"].iloc[0]
    assert m_sep["eligible_days"] == 1
    assert m_sep["attendance_pct"] == 100.0

    # 2026-10: eligible 3, attendance ~33.3333, absenteeism ~33.3333
    m_oct = m[m["month"] == "2026-10"].iloc[0]
    assert m_oct["eligible_days"] == 3
    assert pytest.approx(33.3333, abs=1e-4) == m_oct["attendance_pct"]
    assert pytest.approx(33.3333, abs=1e-4) == m_oct["absenteeism_pct"]


def test_pure_absenteeism_ranking():
    """Absenteeism ranking order for the three employees: E002 (50.0), E001 (15.0), E003 (NaN last)."""
    df = _create_sample_df()
    es = employee_summary(df)
    rank = absenteeism_ranking(es)

    assert list(rank["employee_code"]) == ["E002", "E001", "E003"]
    assert rank.iloc[0]["absenteeism_pct"] == 50.0
    assert rank.iloc[1]["absenteeism_pct"] == 15.0
    assert np.isnan(rank.iloc[2]["absenteeism_pct"])


def test_pure_empty_dataframe_handling():
    """Empty DataFrame passed to all four functions returns an empty DataFrame, no error."""
    empty_df = pd.DataFrame()
    assert employee_summary(empty_df).empty
    assert department_summary(empty_df).empty
    assert monthly_summary(empty_df).empty
    assert absenteeism_ranking(empty_df).empty


def test_db_load_attendance_and_summaries(conn):
    """Database tests: load_attendance_df, summaries, and date filters."""
    add_employee(conn, "E001", "Asha Rao", "Engineering")
    add_employee(conn, "E002", "Ravi Kumar", "Engineering")
    record_attendance(conn, "E001", datetime.date(2026, 9, 1), "Present")
    record_attendance(conn, "E001", datetime.date(2026, 9, 2), "Absent")
    # E002 has no rows

    # load_attendance_df returns 3 rows
    df = load_attendance_df(conn)
    assert len(df) == 3

    # employee_summary gives E001 attendance 50.0 and E002 eligible 0 with NaN percentage
    es = employee_summary(df)
    e1 = es[es["employee_code"] == "E001"].iloc[0]
    assert e1["attendance_pct"] == 50.0
    e2 = es[es["employee_code"] == "E002"].iloc[0]
    assert e2["eligible_days"] == 0
    assert np.isnan(e2["attendance_pct"])

    # load_attendance_df with start_date and end_date both 2026-09-02 still lists E002, and E001 shows only Absent row
    df_filtered = load_attendance_df(
        conn,
        start_date=datetime.date(2026, 9, 2),
        end_date=datetime.date(2026, 9, 2),
    )
    assert len(df_filtered) == 2
    e1_filt = df_filtered[df_filtered["employee_code"] == "E001"]
    assert len(e1_filt) == 1
    assert e1_filt["status"].values[0] == "Absent"
    e2_filt = df_filtered[df_filtered["employee_code"] == "E002"]
    assert len(e2_filt) == 1
    assert pd.isna(e2_filt["status"].values[0])


def test_db_load_attendance_empty_table(conn):
    """With no employees at all, load_attendance_df returns an empty DataFrame with the 6 columns."""
    df_empty = load_attendance_df(conn)
    assert len(df_empty) == 0
    assert list(df_empty.columns) == [
        "employee_code",
        "employee_name",
        "department",
        "is_active",
        "attendance_date",
        "status",
    ]
