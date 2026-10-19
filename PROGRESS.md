# PROGRESS.md: Employee Attendance Analysis System

Last updated: 2026-10-19

## Current status (one line)
Phase 1, Phase 2, and Phase 3 (Final UI/UX Redesign, Searchable Selectors, and Navigation Enhancements) completed and verified with 127 automated tests passing.

## Phases
| Phase | Status | Evidence (real command and result) |
|---|---|---|
| 1. Project skeleton | Tested and passed | Commit aee5d53; directory structure and baseline configuration verified |
| 2. Calculations and tests | Tested and passed | Commit 0379d51; pytest tests/test_calculations.py (10 passed in 0.16s) |
| 3. Database (schema, db.py) | Tested and passed | Commit 9bb1a12; apply_schema, sanitize_password, and connection tests verified |
| 4. Sample data | Tested and passed | Commit a2c519a; seed_data.py loaded 6 employees and 111 attendance rows |
| 5. Employees and attendance | Tested and passed | Commit 0e1a3d9; pytest tests/test_employees.py tests/test_attendance.py (19 passed in 2.15s) |
| 6. Analysis (Pandas, NumPy) | Tested and passed | Commit 90dd0a4; pytest tests/test_analysis.py (7 passed in 0.38s) |
| 7. Reports and charts | Tested and passed | Commit 09956b9; pytest tests/test_reports.py (10 passed in 1.95s) |
| 8. Menu (main.py) | Tested and passed | Commit 875b518; pytest tests/test_main.py (17 passed in 1.92s) |
| W1. Flask read-only pages | Tested and passed | Commit d16c399; pytest tests/test_web.py (13 passed in 6.32s) |
| W2. Flask forms | Tested and passed | Commit 05c0998; pytest tests/test_web_forms.py (14 passed in 5.61s) |
| 9. Phase 1 - Migration & Rules | Tested and passed | pytest: 105 passed in 12.25s (joining dates, department helpers, migration recovery) |
| 10. Phase 2 - Bulk Attendance & UI/UX | Tested and passed | pytest: 124 passed in 11.73s (department batch attendance, atomic rollback, conflict checks, UI redesign, CLI menu) |
| 11. Phase 3 - Final UI/UX & Searchable Selectors | Tested and passed | pytest: 127 passed in 13.45s (active navigation indicators, searchable employee selectors, reports subnav & defaults, responsive containers) |


Status words: Not started / In progress / Implemented but not verified / Tested and passed / Blocked.
Only write "Tested and passed" when a real test run proves it, and paste the result line.

## Requirement tracker
- FR-01: Tested and passed (employees.py verified with tests/test_employees.py, tests/test_main.py, tests/test_web_forms.py)
- FR-02: Tested and passed (attendance.py verified with tests/test_attendance.py)
- FR-03: Tested and passed (UNIQUE key uq_employee_date verified by tests/test_attendance.py:test_duplicate_record_refused and MySQL error 1062)
- FR-04: Tested and passed (calculations.py verified with tests/test_calculations.py)
- FR-05: Tested and passed (analysis.py verified with tests/test_analysis.py)
- FR-06: Tested and passed (reports.py verified with tests/test_reports.py)
- FR-07: Tested and passed (analysis.py verified with tests/test_analysis.py)
- FR-08: Tested and passed (reports.py and visualizations.py verified with tests/test_reports.py)
- FR-09: Tested and passed (attendance.py verified with tests/test_attendance.py)
- DA-01: Tested and passed (analysis.py verified with tests/test_analysis.py)
- DA-02: Tested and passed (calculations.py and analysis.py verified with tests/test_calculations.py, tests/test_analysis.py)
- DA-03: Tested and passed (visualizations.py verified with tests/test_reports.py)
- DB-01: Tested and passed (database/schema.sql and src/db.py applied schema verified)
- AC-01: Tested and passed (UNIQUE key uq_employee_date verified by tests and MySQL error 1062)
- AC-02: Implemented but not verified (until project owner reads documents)
- AC-03: Tested and passed (tests/test_reports.py:test_db_reconciliation verified totals match components)
- NF-01: Tested and passed (git ls-files proved no .env or secrets committed, git grep confirmed only placeholders used)
- NF-02: Tested and passed (full pytest suite: 90 passed in 10.21s)
- NF-03: Implemented but not verified (until project owner reads documents)

## Decisions made (by the project owner)
- D1 to D5 approved: holiday rows per employee, leave counts in the denominator, department % by total days, deactivate not delete, command-line menu. Details are in PROJECT_CONTEXT.md.
- D6 (changes D5): a Flask web interface is added after the menu; the command-line menu stays. Safety rules are in PROJECT_CONTEXT.md.
- D7: a login for head users is added (full access, no public pages), and the site may be hosted publicly with fake data. Power BI was considered and is not needed.

## Problems we hit and how we fixed them
- ENUM strict mode: see final check result: SELECT @@sql_mode returned ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION (STRICT_TRANS_TABLES is active; invalid ENUM values are strictly rejected by MySQL).
- MySQL transaction isolation during web testing: In test_web_forms.py, MySQL's default REPEATABLE READ isolation kept previous SELECT snapshots active in the fixture connection; resolved by enabling autocommit on the verification connection.
- Production schema migration synchronization: The test database was migrated during Phase 1 testing, but `attendance_db` still lacked `joining_date`, causing 1054 Unknown column errors on startup; resolved cleanly by executing `migrate_schema(conn)` on `attendance_db`, backfilling earliest attendance dates (2026-09-01 / 2026-09-14) without data loss or record resets.

## Next step (exactly one)
Project owner reads README.md and docs/rules.md, then pushes to GitHub.

## Rebuild checklist (what is NOT in Git)
1. Clone the repository and open the project directory:
   ```powershell
   git clone <repository-url>
   cd employee-attendance-analysis
   ```
2. Create virtual environment and install dependencies:
   ```powershell
   python -m venv venv
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. In MySQL, create databases and limited user:
   ```sql
   CREATE DATABASE attendance_db;
   CREATE DATABASE attendance_db_test;
   CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
   GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
   GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
4. Configure `.env` from `.env.example`:
   ```powershell
   Copy-Item .env.example .env
   .\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
   ```
   Set `DB_USER=attendance_user`, `DB_PASSWORD=ChooseAStrongPassword`, and `FLASK_SECRET_KEY=<generated-key>`.
5. Initialize the database schema:
   ```powershell
   .\venv\Scripts\python.exe -c "from src.db import apply_schema; apply_schema('attendance_db')"
   ```
6. Load the fake sample seed data (September 2026, 6 employees, 111 rows):
   ```powershell
   .\venv\Scripts\python.exe database/seed_data.py attendance_db
   ```
7. Run the test suite:
   ```powershell
   .\venv\Scripts\python.exe -m pytest -v
   ```
