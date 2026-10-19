# System Architecture & Technical Specification

The **Employee Attendance Analysis System** is built on a clean three-tier architecture that decouples database persistence, business rules, analytical aggregation, and dual presentation interfaces (a Windows console CLI and a local Flask web application).

---

## 1. High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                               Presentation Layer                                  |
|                                                                                   |
|   +------------------------------------+   +----------------------------------+   |
|   |   Flask Web Application (Browser)  |   |   Console CLI Menu (Terminal)    |   |
|   |   - Jinja2 Templates (Dark Slate)  |   |   - Interactive Keyboard Prompts |   |
|   |   - HTTP Request Handlers          |   |   - Formatted Tabular Prints     |   |
|   |   - Anti-CSRF & Security Headers   |   |   - Strict Choice Validation     |   |
|   +-----------------+------------------+   +-----------------+----------------+   |
+---------------------|----------------------------------------|--------------------+
                      |                                        |
                      +-------------------+--------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Business Logic & Analytics Layer                           |
|                                                                                   |
|   +-----------------------+  +-----------------------+  +---------------------+   |
|   |    src/employees.py   |  |   src/attendance.py   |  | src/calculations.py |   |
|   |  - Add/Update/Deact   |  |  - Single & Bulk Batch|  |  - Raw Rate Formulas|   |
|   |  - Joining Date Rules |  |  - Conflict Detection |  |  - Display Strings  |   |
|   |  - Department Rosters |  |  - Atomic Rollback    |  |  - Zero Day Handling|   |
|   +-----------------------+  +-----------------------+  +---------------------+   |
|                                         |                                         |
|   +-------------------------------------+-------------------------------------+   |
|   |                                                                           |   |
|   |   +-------------------------------+   +-------------------------------+   |   |
|   |   |        src/analysis.py        |   |        src/reports.py         |   |   |
|   |   |  - SQL to Pandas DataFrame    |   |  - Text Report Generation     |   |   |
|   |   |  - GroupBy Employee/Dept      |   |  - Matplotlib Trend Charts    |   |   |
|   |   |  - Aggregation (Total Days)   |   |  - Reconciliation Verifier    |   |   |
|   |   +-------------------------------+   +-------------------------------+   |   |
+-----------------------------------------|-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
|                             Database & Storage Layer                              |
|                                                                                   |
|   +------------------------------------+   +----------------------------------+   |
|   |              src/db.py             |   |            config.py             |   |
|   |  - Connection Factory & Teardown   |   |  - Environment Variable Loader   |   |
|   |  - Database Isolation Safeguards   |   |  - DB Host, Port, Credentials    |   |
|   |  - Schema Migration Engine         |   |  - Secret Keys & Output Paths    |   |
|   +-----------------+------------------+   +----------------------------------+   |
|                     |                                                             |
|                     v                                                             |
|   +---------------------------------------------------------------------------+   |
|   |                   MySQL Server 8.0+ (`attendance_db`)                     |   |
|   |  - `employees` Table (Indexed Unique Code, Joining Date, Active Status)   |   |
|   |  - `attendance` Table (Indexed Unique Employee+Date, Status Enum)         |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Layer Descriptions

### 2.1 Presentation Layer

The presentation layer exposes the system's capabilities through two parallel interfaces that share identical business logic:

1. **Flask Web Application (`src/web/`)**:
   - Built with Python Flask, semantic HTML5, and vanilla CSS.
   - Enforces a high-contrast dark slate visual system (`#090d16` background, `#111827` surface cards, `#1e293b` elevated surfaces, `#38bdf8` cyan accents, emerald/rose/amber status badges).
   - Fully zero-framework: no React, Vue, npm, Node.js, or external JavaScript runtimes.
   - Uses native browser controls (`<input list="...">`, `<datalist>`, radio groups) to provide accessible searchable selectors without requiring unsafe inline scripts.
   - Dispatches read-only queries through [`src/web/routes.py`](file:///c:/employee-attendance-analysis/src/web/routes.py) and data modifications through [`src/web/write_routes.py`](file:///c:/employee-attendance-analysis/src/web/write_routes.py).
   - Manages connection lifecycle via `flask.g` and tears down MySQL connections cleanly after every request via `@app.teardown_appcontext`.

2. **Console CLI Menu (`src/main.py`)**:
   - Standalone terminal menu offering 15 interactive operations.
   - Prompts for keyboard inputs, validates date formats, employee codes, and choices.
   - Formats tabular summaries and error notifications directly in the terminal using Python string formatting.
   - Traps `KeyboardInterrupt` and `EOFError` to guarantee clean database connection closures.

### 2.2 Business Logic Layer

The business layer encapsulates all enterprise attendance validation and transactional boundaries:

- **[`src/employees.py`](file:///c:/employee-attendance-analysis/src/employees.py)**:
  - Manages employee records (addition, updates, searches, directory listings).
  - Enforces required joining dates (`joining_date DATE NOT NULL`).
  - Prohibits row deletion (`ON DELETE RESTRICT`); supports deactivation (`is_active = FALSE`).
  - Provides department roster helpers (`get_department_employees`) with date filtering to exclude staff before their joining date.

- **[`src/attendance.py`](file:///c:/employee-attendance-analysis/src/attendance.py)**:
  - Validates individual daily attendance (`record_attendance`, `update_attendance`).
  - Rejects weekend attendance (Saturday and Sunday).
  - Validates employee status: prohibits attendance for inactive staff or dates earlier than an employee's joining date.
  - Implements atomic all-or-nothing department bulk attendance (`record_department_attendance`).
  - Performs pre-submission conflict checks (`check_department_attendance_conflicts`) and handles rollback on any duplicate key clash.
  - Implements organization-wide holiday recording (`record_holiday`) that inserts holiday rows for all eligible active employees.

- **[`src/calculations.py`](file:///c:/employee-attendance-analysis/src/calculations.py)**:
  - Pure calculation functions containing zero database queries or I/O.
  - Computes raw float percentages for Attendance and Absenteeism.
  - Returns `None` for zero eligible days and formats strings to `"N/A"`.
  - Formats valid percentages to two decimal places (`"76.19%"`).

### 2.3 Analytics & Reporting Layer

- **[`src/analysis.py`](file:///c:/employee-attendance-analysis/src/analysis.py)**:
  - Queries raw attendance joined with employees into a Pandas `DataFrame` (`load_attendance_df`).
  - Computes `employee_summary`: total Present, Absent, Leave, Holiday, and Eligible days per individual.
  - Computes `department_summary`: aggregates total Present and total Eligible days by department, dividing aggregated counts to calculate department percentages (never averaging employee percentages).
  - Computes `absenteeism_ranking`: sorts staff by absenteeism percentage descending, placing `N/A` records at the bottom.

- **[`src/reports.py`](file:///c:/employee-attendance-analysis/src/reports.py)** & **[`src/visualizations.py`](file:///c:/employee-attendance-analysis/src/visualizations.py)**:
  - Produces formatted text reports (`generate_monthly_report`, `format_employee_report`, etc.).
  - Generates Matplotlib chart artifacts: `absenteeism_YYYY-MM.png` (horizontal bar ranking) and `monthly_attendance.png` (department comparison).

### 2.4 Database & Persistence Layer

- **[`src/db.py`](file:///c:/employee-attendance-analysis/src/db.py)**:
  - Factory function `get_connection()` initializing `mysql.connector` with credentials loaded from `config.py`.
  - Implements `apply_schema()` to execute [`database/schema.sql`](file:///c:/employee-attendance-analysis/database/schema.sql).
  - Implements idempotent `migrate_schema()` to migrate older schemas to include `joining_date`.
  - Test database isolation guard `require_test_database()`: strictly halts if a test attempts to run against a database name that does not end in `_test`.

---

## 3. Strict Architectural Rules & Enforcements

The codebase is protected by automated architectural tests in [`tests/test_web.py`](file:///c:/employee-attendance-analysis/tests/test_web.py), [`tests/test_web_forms.py`](file:///c:/employee-attendance-analysis/tests/test_web_forms.py), and [`tests/test_main.py`](file:///c:/employee-attendance-analysis/tests/test_main.py):

1. **Zero SQL in Presentation Layers**:
   - `SELECT`, `INSERT`, `UPDATE`, and `DELETE` SQL keywords are strictly forbidden in `src/web/*.py` and `src/main.py`.
   - All database access must be routed through `src.employees`, `src.attendance`, `src.analysis`, or `src.db`.

2. **Zero Inline Scripts & CSP Compliance**:
   - Templates under `src/web/templates/` must contain zero `<script>` tags.
   - HTTP response header `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'` prevents script injection.

3. **No Unsafe Jinja Escaping**:
   - The filters `|safe` and Flask `Markup` are completely barred across all templates and source code.
   - All user inputs (such as employee names containing `<script>` or HTML tags) are safely auto-escaped by Jinja2.

4. **100% Parameterized SQL**:
   - Every query uses `%s` placeholders with parameter tuples passed to `cursor.execute(query, params)`.
   - String concatenation, `%` formatting, and f-strings are never used to compose SQL statements.

5. **Prohibition of Row Deletion**:
   - No SQL `DELETE` statement exists in application business logic.
   - Employee departure is handled exclusively via deactivation (`is_active = FALSE`).
   - The foreign key constraint specifies `ON DELETE RESTRICT`.
