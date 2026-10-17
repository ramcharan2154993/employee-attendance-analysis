# Employee Attendance Analysis System

A system to record, analyze, and report employee attendance and absenteeism using MySQL, Python, Pandas, and Matplotlib.
It provides both an interactive command-line menu and a local Flask web interface sharing a unified business logic layer.

## What It Does
- **Employee Attendance %**: Aggregates individual employee metrics including present, absent, and leave counts with accurate attendance and absenteeism percentages.
- **Department Summary**: Calculates department-level attendance and absenteeism based on total days rather than an average of employee percentages.
- **Monthly Report**: Comprehensive monthly report containing individual and departmental summaries, category totals, and organization-wide attendance rates.
- **Absenteeism Ranking & Visual Charts**: Identifies staff ranked by absenteeism rates and exports visual bar charts (`absenteeism_YYYY-MM.png` and `monthly_attendance.png`) using Matplotlib.
- **Dual Interfaces**: An interactive command-line terminal menu (`src/main.py`) and a local Flask web dashboard (`src/web/`) that both call the exact same underlying modules without duplicate SQL or formulas.

## Requirements
- **Operating System**: Windows (tested on Windows PowerShell)
- **Python**: Python 3.x (built and validated with Python 3.14.6)
- **Database**: MySQL Server 8.0+
- **Version Control**: Git

## Setup Instructions

Follow these numbered steps in Windows PowerShell to set up and configure the project:

### 1. Clone Repository and Open Project Folder
```powershell
git clone <repository-url>
cd employee-attendance-analysis
```

### 2. Create Virtual Environment and Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Create MySQL Databases and Dedicated User
Log in to your local MySQL Server as root or administrative user, then create the production and test databases along with a dedicated limited user. Never use the root account in application configurations and never share the password:
```sql
CREATE DATABASE attendance_db;
CREATE DATABASE attendance_db_test;

CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Generate a secure random secret key for Flask using Python:
```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```
Edit `.env` to supply `DB_USER=attendance_user`, `DB_PASSWORD=ChooseAStrongPassword`, and `FLASK_SECRET_KEY=<generated-key>`.
Note: The `.env` file is git-ignored and must never be committed to source control.

### 5. Initialize Database Schema
Apply the database schema to the main database:
```powershell
.\venv\Scripts\python.exe -c "from src.db import apply_schema; apply_schema('attendance_db')"
```

### 6. Load Sample Seed Data
Load the standard September 2026 sample data (6 fake employees, 111 attendance rows):
```powershell
.\venv\Scripts\python.exe database/seed_data.py attendance_db
```

## Running the Application

### Command-Line Interface
Run the interactive console menu:
```powershell
.\venv\Scripts\python.exe -m src.main
```

### Web Interface
Start the local Flask web interface:
```powershell
.\venv\Scripts\python.exe -m src.web
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
*Note*: The console warning stating that this is a development server is normal and expected for local single-user execution.

## Running Tests
Run the automated pytest suite:
```powershell
.\venv\Scripts\python.exe -m pytest -v
```
All tests run strictly against `attendance_db_test`. The application test framework enforces that the test database name must end with `_test`, refusing execution otherwise. Before every test, existing rows in the test database tables are deleted to ensure total test isolation; `DB_TEST_NAME` must never point to a production database.

## Expected Sample Results (September 2026)
When analyzing the standard September 2026 seed dataset, expected outputs include:
- **Total Recorded Counts**:
  - Present: 80
  - Absent: 20
  - Leave: 5
  - Holiday: 6 (1 holiday on 2026-09-25 across 6 active employees)
  - Eligible Days: 105 (Present 80 + Absent 20 + Leave 5)
  - Overall Organization Attendance: 76.19%
- **Department Attendance**:
  - Engineering: 92.86%
  - Sales: 80.95%
  - HR: 33.33%
- **Zero Eligible Days**:
  - Employee `E006` (Frank Miller, newly joined with 0 eligible days) correctly displays `N/A`.

## Project Structure
```
employee-attendance-analysis/
├── .env.example
├── .gitignore
├── config.py
├── PROGRESS.md
├── PROJECT_CONTEXT.md
├── README.md
├── requirements.txt
├── database/
│   ├── .gitkeep
│   ├── schema.sql
│   └── seed_data.py
├── docs/
│   └── rules.md
├── output/
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── analysis.py
│   ├── attendance.py
│   ├── calculations.py
│   ├── db.py
│   ├── employees.py
│   ├── main.py
│   ├── reports.py
│   ├── visualizations.py
│   └── web/
│       ├── __init__.py
│       ├── __main__.py
│       ├── routes.py
│       ├── write_routes.py
│       └── templates/
│           ├── attendance.html
│           ├── attendance_form.html
│           ├── base.html
│           ├── charts.html
│           ├── deactivate.html
│           ├── employee_form.html
│           ├── employees.html
│           ├── error.html
│           ├── holiday_form.html
│           ├── index.html
│           └── text_report.html
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_analysis.py
    ├── test_attendance.py
    ├── test_calculations.py
    ├── test_employees.py
    ├── test_main.py
    ├── test_reports.py
    ├── test_web.py
    └── test_web_forms.py
```

## Rules and Business Logic
All calculation definitions, attendance conditions, constraints, and project owner decisions (D1–D6) are documented in detail in [docs/rules.md](docs/rules.md).

## Security Notes
- **Parameterized SQL**: All database operations use `%s` query placeholders; string interpolation and f-strings are never used to form queries.
- **Environment Secrets**: Credentials and configuration keys exist solely in `.env` and are never committed or printed.
- **Local Web Binding**: The Flask application binds strictly to `127.0.0.1:5000` with `debug = False`.
- **CSRF Defense**: All POST requests validate an anti-CSRF token against the server session using constant-time string comparison (`hmac.compare_digest`).
- **Input Sanitization & Output Escaping**: All input parameters are stripped; HTML templates rely on Jinja2 auto-escaping with no `|safe` filters or raw markup.
- **Security Headers**: Standard defense-in-depth HTTP response headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'self'`) are sent on every response.
- **No Deletions**: No SQL `DELETE` queries or delete endpoints exist in web or console application logic.

## Known Limitations
- The website has no login or authentication mechanism and must never be exposed to a local network or the public internet.
- It runs on Flask's built-in development server suited for local single-user operations.
- Single-user design: intended for one operator at a time.
- Attendance is recorded manually; there is no automated biometric or badge-swipe integration.
- Weekdays Monday to Friday are assumed to be working days and holidays must be recorded through the holiday option.
- Only recorded rows count (a missing row is not an absence).
- Employees can be deactivated but not reactivated or deleted.
- The sample data is fake and covers one month.
- No pagination for very large tables.
