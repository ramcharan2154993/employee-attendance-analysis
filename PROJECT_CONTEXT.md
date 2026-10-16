# PROJECT_CONTEXT.md: Employee Attendance Analysis System

## What this is
A beginner Python project. MySQL stores employees and daily attendance. Python reads it, Pandas groups and counts, NumPy does percentages, Matplotlib draws charts. Output: monthly report, employee attendance %, department summary, absenteeism chart. Interface: simple command-line menu (no web framework).

## Stack (do not add other packages without asking)
mysql-connector-python, pandas, numpy, matplotlib, python-dotenv, pytest. MySQL is the main database. No SQLite, no CSV as the main store. Load query results into Pandas from the cursor (fetchall), not with read_sql.

## Environment
Windows. Terminal: Antigravity terminal (PowerShell). A virtual environment lives in ./venv. Always run Python and pip through it, for example: .\venv\Scripts\python.exe script.py and .\venv\Scripts\python.exe -m pip install ... Do not rely on (venv) showing in the terminal. Do not change any PowerShell or Windows setting.

## Business rules (decided by the project owner, do not change)
- Statuses: Present, Absent, Leave, Holiday.
- Weekends: no rows, never working days.
- Holidays: a Holiday row for every active employee on that date, stored in the attendance table.
- Eligible working days = recorded Present + Absent + Leave rows. Holiday rows are excluded.
- Attendance % = Present / (Present + Absent + Leave) * 100.
- Absenteeism rate = Absent / (Present + Absent + Leave) * 100. Leave is NOT absenteeism.
- A missing row is NOT an absence. Only existing rows count.
- No eligible days: percentage is None (shown as "N/A"), never 0, never a division error.
- Rounding: display only, 2 decimals. Counts are never rounded.
- Department %: total Present / total eligible days across the department (NOT an average of employee percentages).
- Employees are never deleted. They are deactivated (is_active = FALSE). Employees with attendance cannot be deleted.
- Corrections: an explicit update changes a status. A second insert for the same employee and date is refused.
- The formula lives in ONE function in calculations.py. Nothing else may duplicate it.

## Database design
employees(employee_id INT AUTO_INCREMENT PK, employee_code VARCHAR(20) NOT NULL UNIQUE, employee_name VARCHAR(100) NOT NULL, department VARCHAR(50) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE)
attendance(attendance_id INT AUTO_INCREMENT PK, employee_id INT NOT NULL, attendance_date DATE NOT NULL, status ENUM('Present','Absent','Leave','Holiday') NOT NULL, UNIQUE KEY uq_employee_date (employee_id, attendance_date), FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT ON UPDATE RESTRICT)
Duplicates are blocked by MySQL's UNIQUE key, not only by Python.

## Folder structure (create a file only when its phase needs it)
README.md, requirements.txt, .env.example, .gitignore, config.py
database/schema.sql, database/seed_data.py
docs/rules.md
src/__init__.py, db.py, employees.py, attendance.py, calculations.py, analysis.py, reports.py, visualizations.py, main.py
tests/test_employees.py, test_attendance.py, test_calculations.py, test_reports.py
output/.gitkeep

## Environment variables (names only, values live in .env)
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_TEST_NAME

## Security rules
- Never hardcode, print, or log passwords. Never open, create, edit, or print the .env file.
- .env is never committed. Only .env.example (placeholders) is committed.
- Parameterized SQL only (never build SQL with f-strings or string joins).
- Never use the MySQL root account in the project.
- Sample data is clearly fake. No real people.

## Code rules
Beginner-friendly. Meaningful names. Type hints. A short docstring on every public function. Handle expected errors (duplicate, bad status, missing employee) with clear messages. Never hide an exception silently. Keep calculations free of database code so they can be tested alone. No unrequested features.

## Testing rules
pytest. Tests never touch real data: they refuse to run unless the database name ends with _test. Expected values are worked out by hand, not copied from program output.

## Working rules for the AI
1. Read this file before every task.
2. Touch only the files the task lists.
3. If anything is unclear or conflicts with these rules, ask me. Do not guess.
4. Do not run git add, git commit, or git push unless the task explicitly says so.
5. Run the verification commands and show real output. Never say "done" without it.
6. Report honestly: what was created, commands run, real results, errors, what is unfinished.
7. Stop when the task ends.

## Status (update honestly)
Nothing is built yet. All requirements: Not started. See PROGRESS.md for details.
