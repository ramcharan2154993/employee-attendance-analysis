# PROGRESS.md: Employee Attendance Analysis System

Last updated: 2026-10-16

## Current status (one line)
Project not started. Only the plan, context file and .gitignore exist.

## Phases
| Phase | Status | Evidence (real command and result) |
|---|---|---|
| 1. Project skeleton | In progress | |
| 2. Calculations and tests | Not started | |
| 3. Database (schema, db.py) | Not started | |
| 4. Sample data | Not started | |
| 5. Employees and attendance | Not started | |
| 6. Analysis (Pandas, NumPy) | Not started | |
| 7. Reports and charts | Not started | |
| 8. Menu (main.py) | Not started | |
| 9. README and final review | Not started | |

Status words: Not started / In progress / Implemented but not verified / Tested and passed / Blocked.
Only write "Tested and passed" when a real test run proves it, and paste the result line.

## Requirement tracker
FR-01 Not started | FR-02 Not started | FR-03 Not started | FR-04 Not started
FR-05 Not started | FR-06 Not started | FR-07 Not started | FR-08 Not started
FR-09 Not started | DA-01 Not started | DA-02 Not started | DA-03 Not started
DB-01 Not started | AC-01 Not started | AC-02 Not started | AC-03 Not started
NF-01 Not started | NF-02 Not started | NF-03 Not started

## Decisions made (by the project owner)
- D1 to D5 approved: holiday rows per employee, leave counts in the denominator, department % by total days, deactivate not delete, command-line menu. Details are in PROJECT_CONTEXT.md.
- D6 (changes D5): a Flask web interface is added after the menu; the command-line menu stays. Safety rules are in PROJECT_CONTEXT.md.

## Problems we hit and how we fixed them
(Add one line each time something breaks, with the cause and the fix.)

## Next step (exactly one)
Run Prompt 1 (project skeleton), then verify the output.

## Rebuild checklist (what is NOT in Git)
1. Install Python, MySQL and Git.
2. Clone the repository, open the folder in Antigravity.
3. Create the virtual environment (python -m venv venv), then run .\venv\Scripts\python.exe -m pip install -r requirements.txt
4. Create a limited MySQL user by hand (never root). Never paste its password into any chat.
5. Copy .env.example to .env and fill in the real values.
6. Create the databases, then run database/schema.sql and database/seed_data.py.
7. Run pytest.
(Steps 4 to 7 get exact commands as those phases are completed.)
