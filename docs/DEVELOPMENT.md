# Development, Configuration & Operations Guide

This guide provides step-by-step instructions for installing, configuring, running, testing, and troubleshooting the **Employee Attendance Analysis System** in a Windows PowerShell environment.

---

## 1. Prerequisites

Before setting up the project, ensure the following software is installed on your Windows host:

1. **Python**: Python 3.10+ (tested and verified with **Python 3.14.6**).
2. **Database**: **MySQL Server 8.0+** running locally on port 3306.
3. **Shell**: **Windows PowerShell** or Windows Terminal.
4. **Version Control**: **Git for Windows**.

---

## 2. Environment Setup & Installation

### Step 2.1: Clone Repository & Enter Directory
```powershell
git clone <repository-url>
cd employee-attendance-analysis
```

### Step 2.2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`).*

### Step 2.3: Install Dependencies
```powershell
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 3. Database Initialization & Configuration

### Step 3.1: Create MySQL Databases & Limited User
Open MySQL command client or run via PowerShell:
```sql
CREATE DATABASE attendance_db;
CREATE DATABASE attendance_db_test;

CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
FLUSH PRIVILEGES;
```

### Step 3.2: Configure `.env`
Copy the environment template:
```powershell
Copy-Item .env.example .env
```

Generate a secure 64-character hexadecimal key for Flask sessions:
```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env` to set your credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=attendance_user
DB_PASSWORD=ChooseAStrongPassword
DB_NAME=attendance_db
DB_TEST_NAME=attendance_db_test
FLASK_SECRET_KEY=<paste-generated-key-here>
```
> **Security Notice**: `.env` is listed in `.gitignore` and must never be committed to source control.

### Step 3.3: Initialize Database Schema
Apply the baseline database schema:
```powershell
.\venv\Scripts\python.exe -c "from src.db import apply_schema; apply_schema('attendance_db')"
```

### Step 3.4: Run Schema Migration (Idempotent)
Ensure the `joining_date` column and constraints are fully synchronized:
```powershell
.\venv\Scripts\python.exe -c "from src.db import get_connection, migrate_schema; conn = get_connection('attendance_db'); migrate_schema(conn); conn.close()"
```

### Step 3.5: Seed Sample Data
Populate the standard September 2026 fake dataset (6 employees, 111 attendance rows):
```powershell
.\venv\Scripts\python.exe database/seed_data.py attendance_db
```

---

## 4. Running the Application

### 4.1 Running the Flask Web Interface
Start the local Flask development server:
```powershell
.\venv\Scripts\python.exe -m src.web
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```
> *Note*: The development server warning in the terminal is normal and expected for single-operator local use.

### 4.2 Running the Console CLI Menu
Launch the interactive terminal interface:
```powershell
.\venv\Scripts\python.exe -m src.main
```
The menu presents 15 operations:
- `1`: Add Employee
- `2`: List Employees
- `3`: Search Employees
- `4`: Update Employee
- `5`: Deactivate Employee
- `6`: Record Daily Attendance (Individual)
- `7`: View Attendance Records (Filterable)
- `8`: Correct Attendance Record
- `9`: Record Organization Holiday
- `10`: View Employee Attendance Summary
- `11`: View Department Attendance Summary
- `12`: View Absenteeism Ranking
- `13`: Generate Monthly Report
- `14`: Export Monthly Visual Charts
- `15`: Record Department Attendance (Bulk Roster)
- `0`: Exit Application

---

## 5. Testing & Quality Assurance

### 5.1 Running the Complete Automated Test Suite
```powershell
.\venv\Scripts\python.exe -m pytest -v
```

### 5.2 Test Coverage by Module
- **`tests/test_calculations.py`**: Validates percentage formulas, precision, display formatting, zero-day handling (`"N/A"`), and negative count rejections.
- **`tests/test_employees.py`**: Validates employee creation, duplicate code rejection, field sanitization, SQL injection safety, department listing, and joining date enforcement.
- **`tests/test_attendance.py`**: Validates individual attendance, duplicate rejection, weekend blocking, joining date validation, department bulk batching, conflict detection, and atomic rollback.
- **`tests/test_analysis.py`**: Validates Pandas DataFrame transformation, summary aggregation by total days, and absenteeism sorting.
- **`tests/test_reports.py`**: Validates text report formatting, reconciliation checks (AC-03), and Matplotlib PNG generation.
- **`tests/test_migration.py`**: Tests idempotency of schema migration and recovery from partial failures.
- **`tests/test_main.py`**: Tests CLI menu flows, choice handling, input traps, and EOF handling.
- **`tests/test_web.py`**: Tests Flask endpoints, routing, XSS output auto-escaping, 404/405 error handlers, and security headers.
- **`tests/test_web_forms.py`**: Tests CSRF validation, form POST workflows, datalists, active navigation indicators, department attendance UI, and cookie security flags.

---

## 6. Troubleshooting Common Issues

### Issue 1: `Unknown column 'joining_date' in 'field list'` (Error 1054)
- **Cause**: Database tables were created with an earlier schema version prior to the `joining_date` migration.
- **Fix**: Run the safe migration script:
  ```powershell
  .\venv\Scripts\python.exe -c "from src.db import get_connection, migrate_schema; conn = get_connection(); migrate_schema(conn); conn.close()"
  ```

### Issue 2: `Safety violation: Test operations must use a database ending with '_test'`
- **Cause**: An automated test detected `DB_TEST_NAME` set to a production database.
- **Fix**: Check `.env` and ensure `DB_TEST_NAME=attendance_db_test`. Automated tests strictly enforce database isolation.

### Issue 3: Port 5000 Already in Use
- **Cause**: A previous Flask process is still running in the background.
- **Fix**: Find and terminate the process holding port 5000:
  ```powershell
  Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object OwningProcess
  Stop-Process -Id <ProcessId> -Force
  ```

### Issue 4: `Error: invalid or missing form token` (CSRF 400)
- **Cause**: Submitting a state-changing POST form without a valid CSRF token, or session cookie expired.
- **Fix**: Refresh the page to obtain a fresh session token and re-submit the form.

### Issue 5: `Can't connect to MySQL server on 'localhost'` (Error 2003)
- **Cause**: MySQL Windows service is stopped.
- **Fix**: Start the MySQL service from an elevated PowerShell prompt:
  ```powershell
  Start-Service MySQL80
  ```
