# Database Specification, Schema & Migrations

The **Employee Attendance Analysis System** uses **MySQL Server 8.0+** running the **InnoDB** storage engine to guarantee ACID transaction compliance, referential integrity, and atomic multi-row batch execution.

---

## 1. Database Configuration & Dedicated User

The application never connects using the MySQL `root` account. Production and testing use distinct databases managed by a dedicated local user:

- **Production Database**: `attendance_db`
- **Automated Test Database**: `attendance_db_test`
- **Dedicated User**: `attendance_user` on `localhost`

### Initialization Commands (MySQL Client)
```sql
CREATE DATABASE attendance_db;
CREATE DATABASE attendance_db_test;

CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'ChooseAStrongPassword';
GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
GRANT ALL PRIVILEGES ON attendance_db_test.* TO 'attendance_user'@'localhost';
FLUSH PRIVILEGES;
```

---

## 2. Table Schema Definition

The full schema is declared in [`database/schema.sql`](file:///c:/employee-attendance-analysis/database/schema.sql).

### 2.1 `employees` Table

Stores personnel master records. Employees cannot be deleted; historical records are preserved by deactivating (`is_active = FALSE`).

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

| Column Name | Data Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `employee_id` | `INT` | No | Auto Increment | `PRIMARY KEY` | Internal surrogate identifier |
| `employee_code` | `VARCHAR(20)` | No | None | `UNIQUE KEY` | Human-readable company code (e.g. `E001`) |
| `employee_name` | `VARCHAR(100)` | No | None | None | Full legal name of staff member |
| `department` | `VARCHAR(50)` | No | None | None | Department name (e.g. `Engineering`, `Sales`) |
| `is_active` | `TINYINT(1)` | No | `1` (`TRUE`) | None | Active working status (`1`=Active, `0`=Deactivated) |
| `joining_date` | `DATE` | No | None | None | Employment commencement date |

### 2.2 `attendance` Table

Stores daily attendance records. Each employee may have at most one attendance record per calendar date.

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

| Column Name | Data Type | Nullable | Default | Constraints & Indexes | Description |
|---|---|---|---|---|---|
| `attendance_id` | `INT` | No | Auto Increment | `PRIMARY KEY` | Internal surrogate record identifier |
| `employee_id` | `INT` | No | None | `FOREIGN KEY` | References `employees(employee_id)` |
| `attendance_date` | `DATE` | No | None | Composite Index | Calendar date of attendance |
| `status` | `ENUM(...)` | No | None | Strict ENUM | `'Present'`, `'Absent'`, `'Leave'`, `'Holiday'` |

### Constraints & Referential Safeguards
1. **`uq_employee_date` (Composite Unique Key)**:
   - `UNIQUE (employee_id, attendance_date)`
   - Guarantees database-level rejection of duplicate attendance for the same employee on the same date.
   - Throws MySQL error code `1062` (`ER_DUP_ENTRY`).
2. **`ON DELETE RESTRICT` (Foreign Key)**:
   - Prevents deletion of employee records that possess associated attendance history.
   - Enforces the enterprise business rule: staff departure is recorded as deactivation, never deletion.
3. **Strict ENUM Validation**:
   - `STRICT_TRANS_TABLES` SQL mode is active. Any attempt to insert an invalid status (such as `'Sick'` or `'Late'`) triggers a database error.

---

## 3. Schema Migration Mechanism

When the `joining_date` requirement was introduced, an idempotent, zero-data-loss migration function was implemented in [`src/db.py`](file:///c:/employee-attendance-analysis/src/db.py): `migrate_schema(conn, fallback_date="2026-09-01")`.

### Migration Steps
```
1. SHOW TABLES LIKE 'employees'
   -> If table does not exist, return immediately.

2. SHOW COLUMNS FROM employees LIKE 'joining_date'
   -> If missing, execute:
      ALTER TABLE employees ADD COLUMN joining_date DATE NULL;

3. SELECT COUNT(*) FROM employees WHERE joining_date IS NULL
   -> If null_count > 0, backfill with earliest attendance date per employee:
      UPDATE employees e
      LEFT JOIN (
          SELECT employee_id, MIN(attendance_date) AS min_date
          FROM attendance
          GROUP BY employee_id
      ) a ON e.employee_id = a.employee_id
      SET e.joining_date = COALESCE(a.min_date, %s)
      WHERE e.joining_date IS NULL;

4. SELECT COUNT(*) FROM employees WHERE joining_date IS NULL
   -> If remaining nulls > 0, raise RuntimeError and abort.

5. ALTER TABLE employees MODIFY COLUMN joining_date DATE NOT NULL;
```

### Safety Properties
- **Idempotent**: Safe to run repeatedly; if `joining_date` is already `NOT NULL`, the function completes without altering existing data.
- **Fault-Tolerant**: Recovers cleanly from partially completed migrations where the column was created as nullable but backfill had not finished.
- **Auditable**: Leaves all existing employee IDs, codes, names, departments, and attendance records 100% intact.

---

## 4. Test Database Isolation

Automated tests must never execute against or alter production data:

- Every test in `tests/` uses fixtures configured with `DATABASE_NAME = config.DB_TEST_NAME` (`attendance_db_test`).
- [`src/db.py`](file:///c:/employee-attendance-analysis/src/db.py) enforces this through `require_test_database(database_name)`:
  ```python
  def require_test_database(database_name: str) -> None:
      if not database_name.endswith("_test"):
          raise ValueError(
              f"Safety violation: Test operations must use a database ending with '_test', got: {database_name}"
          )
  ```
- Any attempt to configure the test suite with `attendance_db` raises a fatal `ValueError` immediately.
- Test fixtures truncate and reseed test tables before each test execution, leaving the production `attendance_db` untouched.

---

## 5. Transaction Management & Atomic Rollback

### Single Record Insertions
Individual attendance entries use auto-commit mode with explicit exception trapping for MySQL error `1062` to raise a user-friendly duplicate message.

### Department Bulk Attendance
[`src/attendance.py:record_department_attendance`](file:///c:/employee-attendance-analysis/src/attendance.py) executes as an atomic all-or-nothing transaction:
1. `conn.autocommit = False`
2. Validates department existence, date (weekday only), and eligible active employees.
3. Performs pre-insert conflict queries checking if any employee in the batch already has attendance for that date.
4. If conflicts exist: raises `AttendanceConflictError` with conflicting employee codes and details, rolling back immediately.
5. If clean: executes `cursor.executemany(...)` inserting the entire department batch and calls `conn.commit()`.
6. If any unexpected database error occurs: executes `conn.rollback()` so no partial records remain.
