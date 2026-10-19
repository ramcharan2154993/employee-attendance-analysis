# Authoritative Business Rules & Calculation Standards

This document specifies the exact business logic, calculation standards, constraints, and project owner decisions governing the **Employee Attendance Analysis System**.

---

## 1. Attendance Status Taxonomy

The system records daily attendance using a strict enumeration of four discrete statuses:

| Status | Code / ENUM | Working Day? | Description |
|---|---|---|---|
| **Present** | `'Present'` | Yes | The employee reported to work and performed duties. |
| **Absent** | `'Absent'` | Yes | The employee was scheduled to work but was absent without prior authorized leave. |
| **Leave** | `'Leave'` | Yes | The employee took approved, authorized leave (annual, personal, medical). |
| **Holiday** | `'Holiday'` | No | The organization was officially closed for an observed public holiday. |

---

## 2. Mathematical Formulas & Definitions

### 2.1 Eligible Working Days (The Denominator)
Eligible working days represent all non-holiday calendar days on which an employee was scheduled to work:

$$\text{Eligible Days} = \text{Present} + \text{Absent} + \text{Leave}$$

> **Important**:
> - `Holiday` records are **never** included in the eligible days denominator.
> - `Leave` is included in the denominator because it represents a scheduled working day that was authorized off.

### 2.2 Attendance Percentage
The proportion of scheduled eligible days that the employee was physically present at work:

$$\text{Attendance Percentage} = \frac{\text{Present}}{\text{Eligible Days}} \times 100 = \frac{\text{Present}}{\text{Present} + \text{Absent} + \text{Leave}} \times 100$$

### 2.3 Absenteeism Percentage
The proportion of scheduled eligible days that the employee was unscheduled and absent:

$$\text{Absenteeism Percentage} = \frac{\text{Absent}}{\text{Eligible Days}} \times 100 = \frac{\text{Absent}}{\text{Present} + \text{Absent} + \text{Leave}} \times 100$$

> **Important**:
> - Approved `Leave` does **not** count as absenteeism. An employee taking approved annual leave does not have their absenteeism rate increased.
> - However, approved leave lowers the attendance percentage because the employee was not present.

### 2.4 The Zero-Eligible-Days Rule ("N/A")
When an employee or group has `Eligible Days == 0` (for example, a newly hired staff member whose joining date is after the reporting period, or someone who only has `Holiday` entries recorded):
- Mathematical division by zero is strictly avoided.
- The raw percentage function returns `None` (or `np.nan` in Pandas).
- Display formatters output `"N/A"`.
- It is **never** reported as `0.00%` (which would falsely imply 100% absenteeism).
- In absenteeism leaderboards, records with `"N/A"` are placed at the bottom.

### 2.5 Rounding & Precision
- Rounding is applied **strictly for display purposes** to two decimal places (e.g., `76.19%`).
- All intermediate database queries, Pandas aggregations, and raw calculations retain full floating-point precision.

---

## 3. Department & Organization Aggregation Principles

### The Core Law: Sum of Days, Never Average of Percentages
Department and organization-wide metrics must be calculated by summing raw days across all eligible members, then computing the percentage from the aggregated sums.

$$\text{Department Attendance \%} = \frac{\sum \text{Present}}{\sum \text{Eligible Days}} \times 100$$

### Numerical Proof of Distortion (The Averaging Trap)
Consider an Engineering department with two employees:
- **Employee E001**: 1 Present out of 2 Eligible Days $\rightarrow \text{Attendance} = 50.00\%$
- **Employee E002**: 1 Present out of 1 Eligible Day $\rightarrow \text{Attendance} = 100.00\%$

1. **Incorrect (Averaging Percentages)**:
   $$\frac{50.00\% + 100.00\%}{2} = \mathbf{75.00\%} \quad \text{[INCORRECT]}$$

2. **Correct (Aggregating Raw Counts)**:
   $$\text{Total Present} = 1 + 1 = 2$$
   $$\text{Total Eligible} = 2 + 1 = 3$$
   $$\text{Department Rate} = \frac{2}{3} \times 100 = \mathbf{66.67\%} \quad \text{[CORRECT]}$$

Averaging percentages distorts results by falsely giving an employee with 1 eligible day the exact same weight as an employee with 20 eligible days. The system strictly enforces the aggregate day total method across all reports.

---

## 4. Attendance Constraints & Operational Rules

### 4.1 Missing Records are Not Absences
A missing database row is never assumed to be an absence. Only explicitly recorded rows count toward metrics. Unrecorded dates are treated as unrecorded and omitted from the denominator.

### 4.2 Weekend Rejection Rule
Weekends (Saturday and Sunday, where `date.weekday() >= 5`) are non-working days. Any attempt to record individual attendance, bulk department attendance, or holidays on a weekend is rejected before database insertion with a clear validation error.

### 4.3 Employee Joining-Date Eligibility Rule
Every employee record has a mandatory `joining_date`.
- Attendance cannot be recorded for any date earlier than an employee's `joining_date`.
- Department bulk rosters and historical reports exclude employees on dates prior to their joining date.
- A holiday is only recorded for an employee if the holiday date is on or after their joining date.

### 4.4 Inactive Employee Rule (Deactivation Instead of Deletion)
Employee records are **never deleted** from the database (`ON DELETE RESTRICT`):
- Departed staff are marked `is_active = FALSE`.
- Deactivated employees retain their full attendance history for historical audits and reconciliation.
- Inactive employees cannot have new daily attendance or holidays recorded.
- Inactive employees can be included or excluded from staff directory views using the "Include Inactive" filter toggle.

### 4.5 Duplicate Prevention & Atomic Department Submission
- Database composite key `UNIQUE (employee_id, attendance_date)` rejects duplicate entries.
- Department bulk attendance uses an **atomic all-or-nothing** batch transaction:
  - If any employee in the selected department already has attendance recorded on the selected date, the entire batch is rejected.
  - The transaction is rolled back; zero partial rows are saved.
  - The conflicting employee codes and names are displayed with links to view existing logs or perform individual corrections.

---

## 5. Standard Seed Dataset & Benchmark Results

The standard sample dataset in [`database/seed_data.py`](file:///c:/employee-attendance-analysis/database/seed_data.py) models September 2026 across 6 active employees:

- **Calendar Structure (September 2026)**:
  - 30 total calendar days.
  - 8 weekend days (4 Saturdays, 4 Sundays).
  - 1 official holiday on Monday, September 14, 2026.
  - 21 normal working weekdays.

### 5.1 Employee Breakdown
| Code | Name | Department | Joining Date | Present | Absent | Leave | Holiday | Eligible | Att % | Abs % |
|---|---|---|---|---|---|---|---|---|---|---|
| `E001` | Asha Rao | Engineering | 2026-01-15 | 21 | 0 | 0 | 1 | 21 | 100.00% | 0.00% |
| `E002` | Ravi Kumar | Engineering | 2026-02-01 | 18 | 2 | 1 | 1 | 21 | 85.71% | 9.52% |
| `E003` | Meera Nair | Sales | 2026-03-10 | 14 | 4 | 3 | 1 | 21 | 66.67% | 19.05% |
| `E004` | Karan Shah | Sales | 2026-04-01 | 20 | 0 | 1 | 1 | 21 | 95.24% | 0.00% |
| `E005` | Divya Menon | HR | 2026-05-01 | 7 | 14 | 0 | 1 | 21 | 33.33% | 66.67% |
| `E006` | Sample Newjoiner | HR | 2026-09-01 | 0 | 0 | 0 | 1 | 0 | N/A | N/A |

### 5.2 Department Summaries
| Department | Total Present | Total Absent | Total Leave | Total Holiday | Total Eligible | Attendance % | Absenteeism % |
|---|---|---|---|---|---|---|---|
| **Engineering** | 39 | 2 | 1 | 2 | 42 | **92.86%** | 4.76% |
| **Sales** | 34 | 4 | 4 | 2 | 42 | **80.95%** | 9.52% |
| **HR** | 7 | 14 | 0 | 2 | 21 | **33.33%** | 66.67% |

### 5.3 Organization Totals & Reconciliation
- **Total Present**: 80
- **Total Absent**: 20
- **Total Leave**: 5
- **Total Holiday Records**: 6 (1 holiday date $\times$ 6 employees)
- **Total Database Rows**: 111 (80 + 20 + 5 + 6)
- **Total Eligible Days**: 105 (80 + 20 + 5)
- **Overall Organization Attendance Rate**: $\frac{80}{105} \times 100 = \mathbf{76.19\%}$
- **Overall Organization Absenteeism Rate**: $\frac{20}{105} \times 100 = \mathbf{19.05\%}$
