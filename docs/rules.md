# Attendance and Business Rules

This document details the business logic, calculation standards, constraints, and decisions governing the Employee Attendance Analysis System.

## Status List
The attendance system records daily status using a strict enumeration of four values:
- **Present**: The employee attended work.
- **Absent**: The employee was unscheduled and did not work.
- **Leave**: The employee took an approved scheduled leave.
- **Holiday**: The organization was closed for an official holiday.

## Core Rules

### 1. Weekend Rule
Weekends (Saturday and Sunday) are non-working days. No attendance rows may ever exist or be recorded for weekend dates.

### 2. Holiday Rule
Holidays are stored as explicit rows with status `Holiday` in the attendance table for each active employee on that calendar date. Holidays are excluded from eligible working days.

### 3. Eligible Working Days
Eligible working days represent all non-holiday working days where an employee was scheduled to work. It is defined as:
$$\text{Eligible Days} = \text{Present} + \text{Absent} + \text{Leave}$$
Holiday rows are never counted as eligible working days.

### 4. Attendance and Absenteeism Formulas (in Words)
- **Attendance Percentage**: The number of Present days divided by the total number of eligible working days (Present + Absent + Leave), multiplied by 100.
- **Absenteeism Rate**: The number of Absent days divided by the total number of eligible working days (Present + Absent + Leave), multiplied by 100. Approved Leave is considered an authorized absence from work and is not counted as absenteeism.

### 5. Missing Rows
A missing row is not an absence. Only explicitly recorded rows in the database count toward calculations and reporting. Unrecorded dates are ignored.

### 6. The N/A Rule (Zero Eligible Days)
When an employee or group has zero eligible working days (e.g. newly joined staff or employees with only holiday entries), the percentage is undefined (`None` or `NaN`), and is formatted for display as `"N/A"`. It is never shown as 0% and never raises a division-by-zero error.

### 7. Rounding
Rounding is strictly for display purposes and formatted to two decimal places (e.g. `76.19%`). Internal calculations and raw counts are never rounded.

### 8. Department Percentage Calculation
Department-level attendance percentage is calculated by summing total Present days across all employees in the department and dividing by the total eligible days across the department. It is never an arithmetic average of individual employee percentages.

### 9. Never-Delete and Deactivate Rule
Employee records are never deleted from the database. When an employee departs, they are deactivated (`is_active = FALSE`). Deactivated employees retain their full attendance history for historical reporting and audit reconciliation. Database foreign keys enforce `ON DELETE RESTRICT`.

### 10. Attendance Corrections
An existing attendance record can be updated through an explicit correction action. A second insert for the same employee and date is rejected by the database unique key constraint (`uq_employee_date`).

## Additional Implemented Constraints
- **Weekend Date Rejection**: Attempting to record attendance or a holiday on a Saturday or Sunday raises a validation error and is rejected before database insertion.
- **Inactive Employee Protection**: Inactive employees cannot have new attendance rows recorded.
- **Atomic Holiday Recording**: The holiday recording option inserts a `Holiday` record for every currently active employee in a single atomic transaction. If any active employee already has a recorded attendance row for that date, the entire transaction is rolled back and refused.

## Project Decisions (D1 to D6)
- **D1 (Holiday Rows)**: Record a Holiday row for every active employee on the holiday date, rather than maintaining a separate holidays table.
- **D2 (Leave in Denominator)**: Approved leave days count in eligible working days (denominator), ensuring that leave impacts the attendance percentage without being penalized as absenteeism.
- **D3 (Department Percentage Aggregation)**: Department percentages are computed from aggregate day totals (total present / total eligible), preventing distortion caused by averaging employee percentages with unequal day weights.
- **D4 (Deactivate Instead of Delete)**: Employees are deactivated via `is_active = FALSE`, preserving historical attendance integrity and preventing orphan foreign key references.
- **D5 (Command-Line Menu)**: Provide a beginner-friendly command-line menu interface (`src/main.py`) for console operations.
- **D6 (Flask Web Interface)**: Provide a clean, local-only Flask web interface (`src/web/`) alongside the command-line menu, sharing identical business modules without duplicate SQL or formulas.

## Worked Calculation Example
Consider an employee with the following recorded days in a month:
- **Present**: 15 days
- **Absent**: 3 days
- **Leave**: 2 days
- **Holiday**: 2 days

**Calculations**:
1. **Eligible Working Days**:
   $$\text{Eligible Days} = 15 \text{ (Present)} + 3 \text{ (Absent)} + 2 \text{ (Leave)} = 20 \text{ days}$$
   *(Note: The 2 Holiday days are excluded).*
2. **Attendance Percentage**:
   $$\text{Attendance Rate} = \frac{15}{20} \times 100 = 75.00\%$$
3. **Absenteeism Rate**:
   $$\text{Absenteeism Rate} = \frac{3}{20} \times 100 = 15.00\%$$
