"""Tests for main command-line interface module."""

from pathlib import Path
from src.main import run_menu


def _make_io(inputs: list[str]):
    it = iter(inputs)
    outputs: list[str] = []

    def input_fn(prompt: str = "") -> str:
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    def output_fn(msg: str = "") -> None:
        outputs.append(str(msg))

    return input_fn, output_fn, outputs


def test_exit_immediately(conn):
    """Choosing 0 right away exits, and the output contains 'Employee Attendance Analysis System'."""
    inp, out, collected = _make_io(["0"])
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "Employee Attendance Analysis System" in full_text


def test_invalid_choices(conn):
    """Choice '99' prints 'Invalid choice' and then '0' exits. Choice 'abc' also prints 'Invalid choice'."""
    inp, out, collected = _make_io(["99", "abc", "0"])
    run_menu(conn, input_fn=inp, output_fn=out)
    assert collected.count("Invalid choice") == 2


def test_eof_exits_cleanly(conn):
    """Input that ends early (raises EOFError) exits without an error."""
    inp, out, collected = _make_io([])
    run_menu(conn, input_fn=inp, output_fn=out)
    assert "Employee Attendance Analysis System" in "\n".join(collected)


def test_add_and_list_employee(conn):
    """Add employee via ['1','E001','Asha Rao','Engineering','2','n','0']: output contains 'E001 | Asha Rao | Engineering | Active'."""
    inp, out, collected = _make_io(
        ["1", "E001", "Asha Rao", "Engineering", "2", "n", "0"]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "E001 | Asha Rao | Engineering | Active" in full_text


def test_add_duplicate_employee_error(conn):
    """Adding E001 a second time prints a line starting 'Error:' and menu continues."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "1",
            "E001",
            "Duplicate Rao",
            "Sales",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    error_lines = [line for line in collected if line.startswith("Error:")]
    assert len(error_lines) >= 1


def test_blank_employee_name_error(conn):
    """A blank employee name prints 'Error:' and adds nothing (check the database)."""
    inp, out, collected = _make_io(["1", "E001", "   ", "Engineering", "0"])
    run_menu(conn, input_fn=inp, output_fn=out)
    error_lines = [line for line in collected if line.startswith("Error:")]
    assert len(error_lines) >= 1

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees")
    assert cur.fetchone()[0] == 0
    cur.close()


def test_deactivate_flow(conn):
    """Deactivate with 'no' cancels; with 'YES' deactivates and listing hides without inactive and shows with 'y'."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "5",
            "E001",
            "no",
            "5",
            "E001",
            "YES",
            "2",
            "n",
            "2",
            "y",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "Cancelled." in full_text
    assert "Employee E001 deactivated." in full_text
    assert "E001 | Asha Rao | Engineering | Inactive" in full_text


def test_record_attendance_and_view(conn):
    """Record attendance for E001 on 2026-09-01 as 'present' works; viewing shows '2026-09-01 | E001 | Present'."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "6",
            "E001",
            "2026-09-01",
            "present",
            "8",
            "",
            "",
            "",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "2026-09-01 | E001 | Present" in full_text


def test_record_weekend_error(conn):
    """Recording on Saturday 2026-09-05 prints 'Error:' and no row exists."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "6",
            "E001",
            "2026-09-05",
            "present",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    error_lines = [line for line in collected if line.startswith("Error:")]
    assert len(error_lines) >= 1

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM attendance")
    assert cur.fetchone()[0] == 0
    cur.close()


def test_invalid_date_error(conn):
    """An invalid date '2026-13-45' prints 'Error:' and no row exists."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "6",
            "E001",
            "2026-13-45",
            "present",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    error_lines = [line for line in collected if line.startswith("Error:")]
    assert len(error_lines) >= 1

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM attendance")
    assert cur.fetchone()[0] == 0
    cur.close()


def test_correct_attendance(conn):
    """Correct attendance changes Present to Absent on 2026-09-01 (view shows Absent)."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "6",
            "E001",
            "2026-09-01",
            "Present",
            "7",
            "E001",
            "2026-09-01",
            "Absent",
            "8",
            "",
            "",
            "",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "2026-09-01 | E001 | Absent" in full_text


def test_view_attendance_start_after_end_error(conn):
    """View attendance with start 2026-09-03 and end 2026-09-01 prints 'Error:'."""
    inp, out, collected = _make_io(
        [
            "8",
            "",
            "2026-09-03",
            "2026-09-01",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    error_lines = [line for line in collected if line.startswith("Error:")]
    assert len(error_lines) >= 1


def test_record_holiday_menu(conn):
    """Holiday option on 2026-09-10 (a Thursday) with 2 active employees inserts 2 Holiday rows."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "1",
            "E002",
            "Ravi Kumar",
            "Engineering",
            "9",
            "2026-09-10",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM attendance WHERE status = 'Holiday'")
    assert cur.fetchone()[0] == 2
    cur.close()


def test_monthly_report_menu(conn):
    """Monthly report for 2026-09 with E001 Present and Absent rows contains '50.00%' and 'Overall attendance: 50.00%'."""
    inp, out, collected = _make_io(
        [
            "1",
            "E001",
            "Asha Rao",
            "Engineering",
            "6",
            "E001",
            "2026-09-01",
            "Present",
            "6",
            "E001",
            "2026-09-02",
            "Absent",
            "13",
            "2026",
            "9",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "50.00%" in full_text
    assert "Overall attendance: 50.00%" in full_text


def test_monthly_report_invalid_inputs(conn):
    """Monthly report with month '13' prints 'Error:'; with month 'x' prints 'Error:'."""
    inp, out, collected = _make_io(
        [
            "13",
            "2026",
            "13",
            "13",
            "2026",
            "x",
            "0",
        ]
    )
    run_menu(conn, input_fn=inp, output_fn=out)
    error_lines = [line for line in collected if line.startswith("Error:")]
    assert len(error_lines) == 2


def test_no_delete_in_menu_text(conn):
    """The menu text never contains the word 'delete' (case-insensitive)."""
    inp, out, collected = _make_io(["0"])
    run_menu(conn, input_fn=inp, output_fn=out)
    full_text = "\n".join(collected)
    assert "delete" not in full_text.lower()


def test_no_sql_keywords_in_main_file():
    """The module src/main.py contains no SQL keywords SELECT, INSERT, UPDATE or DELETE."""
    content = Path("src/main.py").read_text(encoding="utf-8")
    for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
        assert keyword not in content
