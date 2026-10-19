# Disaster Recovery & System Restoration Guide

This document is a self-contained, step-by-step runbook for completely reconstructing and verifying the **Employee Attendance Analysis System** from scratch on a new machine, after an OS wipe, or in a fresh Antigravity session.

---

## 1. Fast-Track Restoration Runbook (Under 5 Minutes)

Execute the following commands sequentially in **Windows PowerShell**:

### Step 1: Clone Repository
```powershell
git clone <repository-url>
cd employee-attendance-analysis
```

### Step 2: Create Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 3: Configure MySQL Databases & Credentials
Log in to your local MySQL 8.0+ instance:
```powershell
mysql -u root -p
```
Run the setup script:
```sql
CREATE DATABASE IF NOT EXISTS attendance_db;
CREATE DATABASE IF NOT EXISTS attendance_db_test;

CREATE USER IF NOT EXISTS 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Step 4: Generate `.env` File
```powershell
Copy-Item .env.example .env

# Generate a 64-character hexadecimal Flask secret key:
$SecretKey = .\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"

# Update .env configuration:
(Get-Content .env) `
    -replace "DB_USER=.*", "DB_USER=attendance_user" `
    -replace "DB_PASSWORD=.*", "DB_PASSWORD=ChooseAStrongPassword" `
    -replace "FLASK_SECRET_KEY=.*", "FLASK_SECRET_KEY=$SecretKey" |
    Set-Content .env
```

### Step 5: Initialize Schema & Synchronize Migrations
```powershell
# Apply table structures:
.\venv\Scripts\python.exe -c "from src.db import apply_schema; apply_schema('attendance_db')"

# Ensure joining_date migration is active:
.\venv\Scripts\python.exe -c "from src.db import get_connection, migrate_schema; conn = get_connection('attendance_db'); migrate_schema(conn); conn.close()"
```

### Step 6: Populate Baseline Seed Data
```powershell
.\venv\Scripts\python.exe database/seed_data.py attendance_db
```

### Step 7: Verify System Health with Test Suite
```powershell
.\venv\Scripts\python.exe -m pytest -v
```
*(Verify that all 127 tests pass in ~14 seconds).*

### Step 8: Launch Web Application
```powershell
.\venv\Scripts\python.exe -m src.web
```
Open your browser to: **`http://127.0.0.1:5000`**.

---

## 2. Health Check Diagnostic Script

To verify that the database connection, table integrity, and sample counts are 100% operational in a single command, run:

```powershell
.\venv\Scripts\python.exe -c "
import config, mysql.connector
conn = mysql.connector.connect(
    host=config.DB_HOST,
    port=config.DB_PORT,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    database=config.DB_NAME
)
cur = conn.cursor(dictionary=True)
cur.execute('SELECT COUNT(*) as emp_count FROM employees')
emps = cur.fetchone()['emp_count']
cur.execute('SELECT COUNT(*) as att_count FROM attendance')
atts = cur.fetchone()['att_count']
cur.execute('SHOW COLUMNS FROM employees LIKE ''joining_date''')
has_joining_date = cur.fetchone() is not None
conn.close()

print('=== HEALTH CHECK RESULTS ===')
print(f'Database Connection: SUCCESS ({config.DB_NAME})')
print(f'Employees Table:     {emps} records')
print(f'Attendance Table:    {atts} records')
print(f'Joining Date Column: {\"PRESENT\" if has_joining_date else \"MISSING\"}')
assert emps >= 6, 'Health check failed: expected at least 6 employees'
assert has_joining_date, 'Health check failed: joining_date column missing'
print('=== SYSTEM FULLY OPERATIONAL ===')
"
```

---

## 3. Recovery Checklist

- [ ] Git repository cloned with all source files, templates, and tests.
- [ ] Virtual environment created with Python 3.10+ and dependencies installed.
- [ ] MySQL databases `attendance_db` and `attendance_db_test` created.
- [ ] Dedicated user `attendance_user` created with permissions granted.
- [ ] `.env` created with valid credentials and a unique 64-character secret key.
- [ ] Database schema applied and migration verified.
- [ ] Standard seed data populated (or production backup restored).
- [ ] Full automated test suite passes (127/127 tests).
- [ ] Web application runs on `http://127.0.0.1:5000`.
