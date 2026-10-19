# Employee Attendance Analysis System

An enterprise-grade Human Resources attendance tracking, compliance, and absenteeism intelligence system built with **Python 3.14**, **Flask**, **MySQL 8.0+**, **Pandas**, **NumPy**, and **Matplotlib**.

The system provides dual interfaces—a local **Flask web application** and an interactive **console CLI menu**—sharing a unified, strictly tested business logic layer with zero duplicated SQL or calculation logic.

**Current Implementation Status**: **Phase 3 Complete & Fully Verified** (127 automated tests passing, 100% pass rate).

---

## Table of Contents
1. [Project Purpose & Problem Statement](#1-project-purpose--problem-statement)
2. [Technology Stack](#2-technology-stack)
3. [Directory & File Structure](#3-directory--file-structure)
4. [Application Architecture & Interaction Flow](#4-application-architecture--interaction-flow)
5. [Database Schema, Constraints & Migrations](#5-database-schema-constraints--migrations)
6. [Core System Features](#6-core-system-features)
7. [Authoritative Business Rules & Calculation Formulas](#7-authoritative-business-rules--calculation-formulas)
8. [Workflows & Page-by-Page User Guide](#8-workflows--page-by-page-user-guide)
9. [UI/UX Design System & Searchable Selectors](#9-uiux-design-system--searchable-selectors)
10. [Step-by-Step PowerShell Setup & Run Guide](#10-step-by-step-powershell-setup--run-guide)
11. [Testing Suite & Test Isolation Safeguards](#11-testing-suite--test-isolation-safeguards)
12. [Benchmark Dataset & Calculations (September 2026)](#12-benchmark-dataset--calculations-september-2026)
13. [Security Architecture & Defensive Measures](#13-security-architecture--defensive-measures)
14. [Troubleshooting Guide](#14-troubleshooting-guide)
15. [Known Limitations & Future Roadmap](#15-known-limitations--future-roadmap)
16. [Git & GitHub Backup Instructions](#16-git--github-backup-instructions)
17. [Disaster Recovery Runbook](#17-disaster-recovery-runbook)
18. [Instructions for the Next AI Coding Agent](#18-instructions-for-the-next-ai-coding-agent)
19. [Supporting Documentation Links](#19-supporting-documentation-links)

---

## 1. Project Purpose & Problem Statement

### Problem Statement
Traditional spreadsheet-based or naive attendance tracking systems suffer from critical mathematical, transactional, and data-integrity flaws:
1. **The Averaging Trap**: Computing department or organization attendance rates by taking the simple arithmetic mean of individual employee percentages distorts metrics by treating an employee with 1 scheduled day the same as someone with 22 scheduled days.
2. **Conflating Leave and Absenteeism**: Treating authorized medical or annual leave as absenteeism penalizes compliant employees, while omitting leave entirely from the denominator inflates attendance rates.
3. **Partial Batch Failures**: When recording department-wide attendance, partial failures or unhandled duplicate record insertions leave the database in an inconsistent state.
4. **Historical Distortion**: Deleting departed staff destroys audit trails, while recording attendance on dates prior to an employee's employment commencement corrupts historical baselines.

### Goals & Solution
This system provides an auditable, mathematically sound solution:
- **Strict Working Day Denominators**: Excludes public holidays from eligible working days while counting approved leave in the scheduled denominator without penalizing absenteeism.
- **Aggregate Day Totals**: Computes department and company-wide percentages by summing raw days across cohorts rather than averaging percentages.
- **Atomic Batch Attendance**: Department bulk submissions execute in an all-or-nothing transaction with automated rollback on any duplicate key conflict.
- **Audit-Safe Lifecycle**: Mandates employee `joining_date`, enforces deactivation instead of deletion (`ON DELETE RESTRICT`), and validates weekend restrictions.

---

## 2. Technology Stack

| Technology | Version / Component | Role in System |
|---|---|---|
| **Python** | `3.14.6` (3.10+ supported) | Core backend language, business logic, CLI, and analytical runtime. |
| **Flask** | `3.1.0` | Lightweight WSGI web framework for local HTTP routing and template dispatch. |
| **MySQL Server** | `8.0+` (InnoDB Engine) | Relational database enforcing ACID transactions, foreign keys, and unique indexes. |
| **mysql-connector-python** | `9.2.0` | Official pure-Python/C-ext database driver utilizing parameterized SQL exclusively. |
| **Pandas** | `2.2.3` | In-memory data aggregation, pivot analysis, group-by operations, and summary generation. |
| **NumPy** | `2.2.3` | High-performance numerical operations and IEEE `NaN` handling for zero-day states. |
| **Matplotlib** | `3.10.0` | Headless data visualization generating monthly ranking and attendance comparison PNGs. |
| **pytest** | `9.0.2` | Comprehensive automated testing framework managing 127 integration/unit tests. |
| **python-dotenv** | `1.0.1` | Secure environment variable management isolating database credentials and session secrets. |
| **HTML5 & Vanilla CSS** | Semantic Standards | High-contrast Dark Slate user interface with zero external JS frameworks. |

---

## 3. Directory & File Structure

```
c:\employee-attendance-analysis\
├── .env.example                 # Configuration template with environment placeholders
├── .gitignore                    # Prevents committing .env, venv/, __pycache__, and artifacts
├── config.py                    # Environment variable loader and type-safe configuration constants
├── PROGRESS.md                  # Chronological phase verification log and test evidence
├── PROJECT_CONTEXT.md           # Business background, stakeholder constraints, and approved decisions
├── README.md                    # Master documentation, architecture specification, and recovery guide
├── requirements.txt             # Pinned pip dependencies
│
├── database/
│   ├── .gitkeep                 # Preserves directory in version control
│   ├── schema.sql               # Baseline DDL script defining employees and attendance tables
│   └── seed_data.py             # Deterministic seed script populating September 2026 sample data
│
├── docs/                        # In-depth architectural, database, and rule specifications
│   ├── ARCHITECTURE.md          # Complete three-tier architectural specification and data flow
│   ├── BUSINESS_RULES.md        # Authoritative business rules, calculation proofs, and benchmarks
│   ├── DATABASE.md              # Database schema, constraints, migrations, and user permissions
│   ├── DEVELOPMENT.md           # Local development, PowerShell setup, commands, and troubleshooting
│   ├── PROJECT_STATUS.md        # Feature completion matrix, verified tests, and future roadmap
│   ├── RECOVERY.md              # Fast-track disaster recovery runbook and diagnostic scripts
│   └── rules.md                 # Baseline stakeholder rules (preserved for audit consistency)
│
├── output/
│   ├── .gitkeep                 # Preserves directory for exported visual chart PNGs
│   ├── absenteeism_2026-09.png  # Generated horizontal bar chart of employee absenteeism ranking
│   └── monthly_attendance.png   # Generated monthly department attendance comparison bar chart
│
├── src/
│   ├── __init__.py              # Core application package marker
│   ├── analysis.py              # SQL-to-Pandas DataFrame transformations, summaries, and rankings
│   ├── attendance.py            # Business logic: single/bulk attendance, conflict checks, holidays
│   ├── calculations.py          # Pure mathematical percentage formulas, display strings, N/A handling
│   ├── db.py                    # Connection factory, test database guard, schema application & migration
│   ├── employees.py             # Employee master logic: create, search, update, deactivate, roster filter
│   ├── main.py                  # Standalone interactive 15-option console menu interface
│   ├── reports.py               # Formatted plaintext report generation and chart export orchestrator
│   ├── visualizations.py        # Matplotlib chart drawing functions
│   └── web/                     # Flask web application package
│       ├── __init__.py          # App factory (`create_app`), security headers, teardown, error handlers
│       ├── __main__.py          # Entrypoint for running web interface via `python -m src.web`
│       ├── routes.py            # Read-only GET routes (Dashboard, Directory, Logs, Reports, Charts)
│       ├── write_routes.py      # State-changing GET/POST routes with anti-CSRF token validation
│       └── templates/           # Semantic Jinja2 HTML templates (Dark Slate Design System)
│           ├── attendance.html              # Attendance log table with multi-field filter form
│           ├── attendance_form.html         # Record/Correct attendance with searchable datalist selector
│           ├── base.html                    # Master layout with active nav indicators, CSS tokens, badges
│           ├── charts.html                  # Visual analytics display with sub-tabs & month selector
│           ├── deactivate.html              # Explicit employee deactivation confirmation screen
│           ├── department_attendance.html   # Bulk department roster with radio groups & conflict warnings
│           ├── employee_form.html           # Add/Edit employee form with department datalist & joining date
│           ├── employees.html               # Staff directory table with status pills & filter controls
│           ├── error.html                   # Generic 400/404/405/500 error display
│           ├── holiday_form.html            # Organization holiday creation form
│           ├── index.html                   # Executive dashboard with KPI metric cards & quick actions
│           └── text_report.html             # Preformatted text report view with persistent subnav tabs
│
└── tests/                       # Automated pytest suite (127 tests targeting attendance_db_test)
    ├── __init__.py              # Test package marker
    ├── conftest.py              # Test fixtures, client initialization, and test database setup
    ├── test_analysis.py         # Tests for Pandas transformations and summary calculations
    ├── test_attendance.py       # Tests for attendance validation, bulk batching, atomic rollback
    ├── test_calculations.py     # Pure tests for mathematical percentage formulas and edge cases
    ├── test_employees.py        # Tests for employee master CRUD, joining dates, and SQL safety
    ├── test_main.py             # Interactive CLI menu automation tests (mocking stdin/stdout)
    ├── test_migration.py        # Idempotent schema migration and partial-failure recovery tests
    ├── test_reports.py          # Plaintext report verification, reconciliation (AC-03), Matplotlib PNGs
    ├── test_web.py              # Flask read-only routing, XSS auto-escaping, architectural rules
    └── test_web_forms.py        # CSRF enforcement, form workflows, active nav indicators, datalists
```

---

## 4. Application Architecture & Interaction Flow

The system strictly enforces a three-tier separation of concerns:

```
[ HTTP Browser Client ]            [ Terminal Console ]
           │                                 │
           v                                 v
[ src/web/routes.py & write_routes.py ]   [ src/main.py ]
           │                                 │
           └─────────────────┬───────────────┘
                             v
                 [ Business Logic Layer ]
                 - src/employees.py
                 - src/attendance.py
                 - src/calculations.py
                             │
                             v
                 [ Analytics & Reporting ]
                 - src/analysis.py (Pandas)
                 - src/reports.py & visualizations.py
                             │
                             v
                 [ Database Layer: src/db.py ]
                             │
                             v
                 [ MySQL 8.0+ Database ]
```

### Architectural Guardrails (Enforced by Automated Tests)
1. **Zero SQL in Presentation Layers**: `SELECT`, `INSERT`, `UPDATE`, and `DELETE` keywords are strictly prohibited in `src/web/*.py` and `src/main.py`.
2. **Strict CSRF Synchronizer Token**: All state-changing POST requests require a hidden `csrf_token` compared using constant-time string comparison (`hmac.compare_digest`).
3. **No Unsafe Jinja Filters**: The `|safe` filter and `Markup` bypasses are strictly forbidden across all templates and source code.
4. **100% Parameterized Queries**: Every database query uses `%s` placeholders with parameter tuples passed to `cursor.execute()`. String interpolation is never used.
5. **No DELETE Statements**: Application logic never executes SQL `DELETE` queries on employee records; foreign keys specify `ON DELETE RESTRICT`.

---

## 5. Database Schema, Constraints & Migrations

### 5.1 Tables and Constraints

#### `employees` Table
```sql
CREATE TABLE IF NOT EXISTS employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    employee_name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    joining_date DATE NOT NULL
);
```

#### `attendance` Table
```sql
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('Present', 'Absent', 'Leave', 'Holiday') NOT NULL,
    UNIQUE KEY uq_employee_date (employee_id, attendance_date),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
);
```

### 5.2 Key Database Properties
- **Composite Unique Key `uq_employee_date`**: Prevents an employee from having duplicate attendance records on the same calendar date. Triggers MySQL error `1062` on violation.
- **Foreign Key `ON DELETE RESTRICT`**: Rejects any attempt to delete an employee record that has associated attendance rows.
- **Strict ENUM**: Rejects invalid attendance statuses at the database layer.

### 5.3 Schema Migration Engine
[`src/db.py:migrate_schema`](file:///c:/employee-attendance-analysis/src/db.py) provides an idempotent migration engine to transition pre-Phase-1 schemas to the current specification:
1. Detects whether `joining_date` exists in `employees`.
2. Adds `joining_date DATE NULL` if missing.
3. Backfills existing records with each employee's earliest recorded attendance date (`MIN(attendance_date)`), falling back to `2026-09-01`.
4. Verifies zero `NULL` records remain, then alters the column to `NOT NULL`.
5. Tested for idempotency and partial-failure recovery in [`tests/test_migration.py`](file:///c:/employee-attendance-analysis/tests/test_migration.py).

---

## 6. Core System Features

### 6.1 Employee Directory Management
- **Add Employee**: Validates unique employee code, legal name, department, and joining date (defaults to today if omitted).
- **Edit Employee**: Modifies employee name and department while preserving the primary identifier code.
- **Directory Search & Filter**: Search by name, code, or department with an optional "Include inactive" toggle.
- **Deactivation (Never Delete)**: Departure confirmation screen deactivates employee records (`is_active = FALSE`), preserving full historical attendance data.

### 6.2 Attendance Operations
- **Single Attendance Entry**: Interactive record form with searchable employee datalist, date picker, and status selector.
- **Department Bulk Attendance Roster**:
  - Select department and date $\rightarrow$ loads active staff whose joining date is on or before the selected date.
  - Defaults all eligible staff to **Present**.
  - One-click **"Mark All Present"** reset control.
  - Segmented radio buttons to mark individual staff as **Present**, **Absent**, or **Leave**.
  - Confirmation summary and mandatory review checkbox.
  - **Atomic Transaction**: If any employee in the department already has attendance recorded for that date, the entire batch is rejected with an explanatory conflict alert, rolling back the database transaction so zero partial records are saved.
- **Attendance Correction**: Safely updates an existing recorded status without creating duplicates.
- **Organization Holiday Recording**: Inserts a `Holiday` record for every eligible active employee in a single atomic transaction.

### 6.3 Analytics, Reports & Visualizations
- **Employee Summary (`/summary/employees`)**: Individual totals for Present, Absent, Leave, Holiday, and Eligible Days with exact attendance and absenteeism percentages.
- **Department Summary (`/summary/departments`)**: Aggregates totals across each department and calculates rates from aggregate sums.
- **Absenteeism Leaderboard (`/ranking`)**: Ranks staff from highest to lowest absenteeism percentage, placing `N/A` records at the bottom.
- **Monthly Plaintext Report (`/report`)**: Comprehensive monthly breakdown with organization totals, department summaries, and individual attendance lines.
- **Visual Analytics Charts (`/charts`)**: Headless generation of two Matplotlib PNG charts:
  - `absenteeism_YYYY-MM.png`: Horizontal bar chart ranking employee absenteeism rates.
  - `monthly_attendance.png`: Department-level comparative attendance percentage bar chart.

### 6.4 Console CLI Menu
[`src/main.py`](file:///c:/employee-attendance-analysis/src/main.py) provides 15 menu options mirroring all web capabilities with full terminal formatting and robust keyboard-interrupt traps.

---

## 7. Authoritative Business Rules & Calculation Formulas

All calculations adhere strictly to the rules documented in [`docs/BUSINESS_RULES.md`](file:///c:/employee-attendance-analysis/docs/BUSINESS_RULES.md):

### 7.1 Mathematical Formulas
1. **Eligible Working Days**:
   $$\text{Eligible Days} = \text{Present} + \text{Absent} + \text{Leave}$$
   *(Holidays are strictly excluded from the eligible days denominator).*

2. **Attendance Percentage**:
   $$\text{Attendance Rate} = \frac{\text{Present}}{\text{Eligible Days}} \times 100$$

3. **Absenteeism Percentage**:
   $$\text{Absenteeism Rate} = \frac{\text{Absent}}{\text{Eligible Days}} \times 100$$
   *(Approved Leave is authorized and is not counted as absenteeism).*

4. **The Zero-Eligible-Days Rule ("N/A")**:
   When $\text{Eligible Days} = 0$, division by zero is prevented; raw percentage returns `None`, and display outputs `"N/A"`. It is never reported as `0.00%`.

5. **Aggregation Principle (Sum of Days, Never Average of Averages)**:
   Department and company percentages sum raw days first, then divide:
   $$\text{Department Attendance \%} = \frac{\sum \text{Present}}{\sum \text{Eligible Days}} \times 100$$

### 7.2 Operational Constraints
- **Missing Records**: A missing row in the database is not an absence. Only explicitly recorded rows count.
- **Weekend Rule**: Saturdays and Sundays (`weekday() >= 5`) are non-working days; any attendance entry is rejected.
- **Joining Date Rule**: Employees cannot have attendance recorded prior to their `joining_date`.
- **Inactive Employee Protection**: Inactive employees cannot receive new attendance records.
- **Atomic Batch Rollback**: Batch operations rollback entirely upon duplicate detection.

---

## 8. Workflows & Page-by-Page User Guide

### 8.1 Dashboard (`/`)
- Displays real-time KPI stat cards: Active Employees, Bulk Attendance shortcut, and Historical Log access.
- Provides quick monthly report and visual analytics generation forms.

### 8.2 Staff Directory (`/employees`)
- Lists all employees with code, name, department, joining date, status badge, and action links.
- Filter by search string (name, code, or department) and toggle "Include inactive" staff.
- Quick actions: **Edit** details or **Deactivate** employee.

### 8.3 Attendance Log (`/attendance`)
- Chronological historical log with filter controls: Employee Code (searchable datalist), Department dropdown, and Start/End date bounds.
- Status badges: Emerald (Present), Rose (Absent), Amber (Leave), Purple (Holiday).
- **Correct** action link opens the attendance correction screen pre-populated with employee code and date.

### 8.4 Department Bulk Attendance (`/attendance/department`)
1. Select a Department and an Attendance Date $\rightarrow$ Click **"Load Roster"**.
2. If conflicts exist: A warning alert lists conflicting employee codes and blocks batch submission, offering direct links to view or correct existing records.
3. If clean: Displays eligible active roster. All employees default to **Present**.
4. Adjust individual statuses using the Present / Absent / Leave radio toggles.
5. Use **"Mark All Present"** to instantly reset all selections.
6. Check the confirmation checkbox and click **"Submit Department Attendance"**.

### 8.5 Reporting & Analytics Views
- Accessible via the **Reports & Analytics** main navigation tab.
- Includes a persistent sub-navigation bar to jump between:
  - **Employee Summary** (`/summary/employees`): Formatted table with date-range filters.
  - **Department Summary** (`/summary/departments`): Department aggregates with date-range filters.
  - **Absenteeism Ranking** (`/ranking`): Staff ranked by absenteeism rate.
  - **Monthly Report** (`/report`): Plaintext monthly report with Year and Month inputs (defaults to 2026-09).
  - **Visual Charts** (`/charts`): Rendered Matplotlib charts with Year and Month inputs (defaults to 2026-09).

---

## 9. UI/UX Design System & Searchable Selectors

### 9.1 Dark Slate Theme Specification
- **Backgrounds**: Root `--bg: #090d16`, Cards `--surface: #111827`, Elevated Cards `--surface-elevated: #1e293b`.
- **Borders**: Standard `--border: #2d3748`, Subtle `--border-subtle: #1f2937`.
- **Typography**: Apple System / BlinkMacSystemFont / Segoe UI, Primary Text `--text: #f8fafc`, Muted `--text-muted: #94a3b8`.
- **Accents**: Primary Cyan `--primary: #38bdf8`, Success Emerald `--accent: #10b981`, Danger Rose `--danger: #f43f5e`, Warning Amber `--warning: #f59e0b`.
- **Badges**: Unified `.badge` pill geometry with 9999px border-radius, font-weight 600, and semantic subtle background fills.
- **Focus Outlines**: Accessible `:focus-visible` outlines (`2px solid var(--primary); outline-offset: 2px`).
- **Responsive Layout**: Tables wrapped in `<div style="overflow-x: auto;">` to prevent horizontal clipping on smaller viewports.

### 9.2 Searchable Selectors (CSP Compliant)
Forms requiring employee selection ([`attendance_form.html`](file:///c:/employee-attendance-analysis/src/web/templates/attendance_form.html)) use HTML5 `<input list="employee_options">` with `<datalist>`:
```html
<input list="employee_options" id="employee_code" name="employee_code" value="{{ employee_code }}" placeholder="Type code, name, or department to search..." required>
<datalist id="employee_options">
    {% for emp in employees %}
    <option value="{{ emp.employee_code }}" label="{{ emp.employee_code }} — {{ emp.employee_name }} ({{ emp.department }})">
        {{ emp.employee_code }} - {{ emp.employee_name }} ({{ emp.department }})
    </option>
    {% endfor %}
</datalist>
```
- **Operator Experience**: Typing any part of the name or code displays matching suggestions natively in all modern browsers.
- **Backend Safety**: Submits exclusively the verified `employee_code`; displayed names are never trusted as database keys.
- **Zero Scripts**: 100% compliant with strict Content Security Policy; zero `<script>` tags required.

---

## 10. Step-by-Step PowerShell Setup & Run Guide

Execute these commands in Windows PowerShell:

### Step 10.1: Clone and Enter Repository
```powershell
git clone <repository-url>
cd employee-attendance-analysis
```

### Step 10.2: Virtual Environment Setup
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 10.3: MySQL Database & User Initialization
Log in to MySQL as root and execute:
```sql
CREATE DATABASE attendance_db;
CREATE DATABASE attendance_db_test;

CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
FLUSH PRIVILEGES;
```

### Step 10.4: Configure Environment Variables
```powershell
Copy-Item .env.example .env
```
Generate a secret key:
```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```
Edit `.env` to supply:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=attendance_user
DB_PASSWORD=ChooseAStrongPassword
DB_NAME=attendance_db
DB_TEST_NAME=attendance_db_test
FLASK_SECRET_KEY=<your-generated-key>
```

### Step 10.5: Initialize Schema & Apply Migration
```powershell
# Apply initial tables:
.\venv\Scripts\python.exe -c "from src.db import apply_schema; apply_schema('attendance_db')"

# Ensure joining_date migration is synchronized:
.\venv\Scripts\python.exe -c "from src.db import get_connection, migrate_schema; conn = get_connection('attendance_db'); migrate_schema(conn); conn.close()"
```

### Step 10.6: Populate Standard Sample Seed Data
```powershell
.\venv\Scripts\python.exe database/seed_data.py attendance_db
```

### Step 10.7: Launch Application
- **Flask Web Server**:
  ```powershell
  .\venv\Scripts\python.exe -m src.web
  ```
  Open browser: **`http://127.0.0.1:5000`**
- **Console CLI Menu**:
  ```powershell
  .\venv\Scripts\python.exe -m src.main
  ```

---

## 11. Testing Suite & Test Isolation Safeguards

### 11.1 Executing Tests
```powershell
.\venv\Scripts\python.exe -m pytest -v
```

### 11.2 Test Isolation Invariant
- All tests execute strictly against `attendance_db_test`.
- [`src/db.py:require_test_database`](file:///c:/employee-attendance-analysis/src/db.py) prevents any test from running against a database name that does not end in `_test`.
- Test fixtures truncate and reseed test tables before each test execution, leaving `attendance_db` production records untouched.

### 11.3 Verified Test Results
```
============================ 127 passed in 13.45s =============================
```
- **Total Tests**: 127
- **Passing**: 127 (100%)
- **Failing**: 0
- **Warnings**: 0

---

## 12. Benchmark Dataset & Calculations (September 2026)

The deterministic seed script ([`database/seed_data.py`](file:///c:/employee-attendance-analysis/database/seed_data.py)) populates September 2026 across 6 active employees:

- **Calendar Structure**: 30 calendar days, 8 weekend days, 1 holiday (2026-09-14), 21 working weekdays.
- **Employee Metrics**:
  - `E001` (Asha Rao, Eng): 21 Present, 0 Absent, 0 Leave, 1 Holiday $\rightarrow$ 21 Eligible, **100.00% Att**, 0.00% Abs
  - `E002` (Ravi Kumar, Eng): 18 Present, 2 Absent, 1 Leave, 1 Holiday $\rightarrow$ 21 Eligible, **85.71% Att**, 9.52% Abs
  - `E003` (Meera Nair, Sales): 14 Present, 4 Absent, 3 Leave, 1 Holiday $\rightarrow$ 21 Eligible, **66.67% Att**, 19.05% Abs
  - `E004` (Karan Shah, Sales): 20 Present, 0 Absent, 1 Leave, 1 Holiday $\rightarrow$ 21 Eligible, **95.24% Att**, 0.00% Abs
  - `E005` (Divya Menon, HR): 7 Present, 14 Absent, 0 Leave, 1 Holiday $\rightarrow$ 21 Eligible, **33.33% Att**, 66.67% Abs
  - `E006` (Sample Newjoiner, HR): 0 Present, 0 Absent, 0 Leave, 1 Holiday $\rightarrow$ 0 Eligible, **N/A Att**, **N/A Abs**
- **Department Metrics**:
  - **Engineering**: 39 Present / 42 Eligible $\rightarrow$ **92.86%** Attendance
  - **Sales**: 34 Present / 42 Eligible $\rightarrow$ **80.95%** Attendance
  - **HR**: 7 Present / 21 Eligible $\rightarrow$ **33.33%** Attendance
- **Organization Overall**:
  - 80 Present + 20 Absent + 5 Leave = **105 Eligible Days**
  - Overall Attendance Rate: $\frac{80}{105} \times 100 = \mathbf{76.19\%}$
  - Overall Absenteeism Rate: $\frac{20}{105} \times 100 = \mathbf{19.05\%}$

---

## 13. Security Architecture & Defensive Measures

1. **Anti-CSRF Synchronizer Tokens**:
   - Every state-changing form generates a cryptographically random session token (`secrets.token_hex(32)`).
   - Validated on POST using constant-time string comparison (`hmac.compare_digest`).
2. **Defensive Parameterized SQL**:
   - 100% of queries use parameter tuples. f-strings, `%` interpolation, and string concatenation are strictly barred.
3. **Automated XSS Prevention**:
   - Jinja2 autoescaping is enforced globally.
   - Use of `|safe` and `Markup` is prohibited and verified by architectural unit tests.
4. **Security HTTP Response Headers**:
   - `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'`
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
5. **Cookie Security**:
   - Session cookies enforce `HttpOnly=True` and `SameSite=Lax`.
6. **Local-Only Web Binding**:
   - Flask binds strictly to `127.0.0.1:5000` with `debug=False`.
   - Never expose port 5000 directly to the public internet.

---

## 14. Troubleshooting Guide

### Issue 14.1: `Unknown column 'joining_date' in 'field list'` (Error 1054)
- **Cause**: Existing database was created before the joining date schema update.
- **Fix**: Run the safe migration script:
  ```powershell
  .\venv\Scripts\python.exe -c "from src.db import get_connection, migrate_schema; conn = get_connection(); migrate_schema(conn); conn.close()"
  ```

### Issue 14.2: Port 5000 in Use
- **Cause**: A background Flask instance is running.
- **Fix**: Locate and kill the process:
  ```powershell
  Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object OwningProcess
  Stop-Process -Id <ProcessId> -Force
  ```

### Issue 14.3: `Safety violation: Test operations must use a database ending with '_test'`
- **Cause**: `DB_TEST_NAME` in `.env` is incorrectly set to `attendance_db`.
- **Fix**: Open `.env` and set `DB_TEST_NAME=attendance_db_test`.

### Issue 14.4: MySQL Connection Refused (Error 2003)
- **Cause**: MySQL Windows service is inactive.
- **Fix**: Run `Start-Service MySQL80` from an Administrator PowerShell prompt.

---

## 15. Known Limitations & Future Roadmap

### Known Limitations
- **Single-User Architecture**: Designed for single HR operator use; multi-user authentication and role-based permissions are not yet implemented.
- **Manual Attendance Data Entry**: Biometric hardware webhooks (fingerprint / RFID) are not integrated.
- **No Server-Side Pagination**: Datasets over 1,000 records render in a single scrollable container.

### Future Roadmap
1. **User Authentication & RBAC**: Admin, Manager, and Operator user roles with salted password hashing (`argon2`).
2. **Data Export**: Export summary tables to CSV and Excel (`.xlsx`).
3. **Audit Trail**: Dedicated `attendance_audit` table tracking operator, timestamp, and previous vs new status for corrections.
4. **Pagination**: Server-side `LIMIT` and `OFFSET` query pagination for large historical datasets.

---

## 16. Git & GitHub Backup Instructions

To preserve your work and push updates to your GitHub repository:

```powershell
# Check current repository status:
git status

# Stage all documentation, source code, and template modifications:
git add .

# Commit with a clear, descriptive message:
git commit -m "Complete Phase 3 UI/UX redesign, searchable selectors, and permanent documentation"

# Push to your remote repository:
git push origin main
```

---

## 17. Disaster Recovery Runbook

To restore the complete environment from scratch on a new machine in **under 5 minutes**:

1. Clone repository:
   ```powershell
   git clone <repository-url>
   cd employee-attendance-analysis
   ```
2. Create virtual environment & install dependencies:
   ```powershell
   python -m venv venv
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. Create MySQL databases and user:
   ```sql
   CREATE DATABASE attendance_db;
   CREATE DATABASE attendance_db_test;
   CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
   GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
   GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
4. Configure `.env` from template with a generated secret key.
5. Apply schema and synchronize migration:
   ```powershell
   .\venv\Scripts\python.exe -c "from src.db import apply_schema; apply_schema('attendance_db')"
   .\venv\Scripts\python.exe -c "from src.db import get_connection, migrate_schema; conn = get_connection('attendance_db'); migrate_schema(conn); conn.close()"
   ```
6. Seed sample data:
   ```powershell
   .\venv\Scripts\python.exe database/seed_data.py attendance_db
   ```
7. Verify 127/127 tests pass:
   ```powershell
   .\venv\Scripts\python.exe -m pytest -v
   ```
8. Start the web application:
   ```powershell
   .\venv\Scripts\python.exe -m src.web
   ```

---

## 18. Instructions for the Next AI Coding Agent

If you are an AI assistant continuing development on this repository, you **must adhere to these mandatory instructions**:

1. **Read This README and Linked Docs First**:
   Review this `README.md`, [`docs/ARCHITECTURE.md`](file:///c:/employee-attendance-analysis/docs/ARCHITECTURE.md), and [`docs/BUSINESS_RULES.md`](file:///c:/employee-attendance-analysis/docs/BUSINESS_RULES.md) before modifying any code.
2. **Inspect Current Code Before Changing Anything**:
   Never assume the code matches an outdated specification. Verify actual routes, schema, and templates using file viewing and grep tools.
3. **Preserve Business Logic & Formulas**:
   Never alter the eligible days formula ($\text{Present} + \text{Absent} + \text{Leave}$), holiday exclusions, or aggregate day total law. Never average percentages to calculate cohort metrics.
4. **Run Tests Before and After Every Change**:
   Execute `.\venv\Scripts\python.exe -m pytest -v` before and after making any edits. Ensure all 127 existing tests pass.
5. **Use Only `attendance_db_test` for Automated Tests**:
   Never point automated tests or fixtures to `attendance_db`. `require_test_database()` enforces that test database names must end with `_test`.
6. **Zero Secrets in Code or Logs**:
   Never commit passwords, API keys, or `.env` contents. Use placeholders in documentation and commit messages.
7. **Maintain Architectural Invariants**:
   - Zero SQL statements in `src/web/*.py` or `src/main.py`.
   - Zero `<script>` tags in `src/web/templates/*.html`.
   - Zero `|safe` or `Markup` bypasses.
   - Zero SQL `DELETE` statements; deactivation is the only supported departure flow.
8. **Update Documentation Synchronously**:
   If you add a route, schema column, or business rule, immediately update this `README.md`, `PROGRESS.md`, and the appropriate document in `docs/`.

---

## 19. Supporting Documentation Links

- **Architecture & Request Lifecycle**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Database Schema, Constraints & Migrations**: [`docs/DATABASE.md`](docs/DATABASE.md)
- **Authoritative Business Rules & Calculations**: [`docs/BUSINESS_RULES.md`](docs/BUSINESS_RULES.md)
- **Development Setup & Troubleshooting**: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- **Project Implementation Status & Roadmap**: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- **Disaster Recovery Runbook**: [`docs/RECOVERY.md`](docs/RECOVERY.md)
