CREATE TABLE IF NOT EXISTS employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    employee_name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    joining_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('Present', 'Absent', 'Leave', 'Holiday') NOT NULL,
    UNIQUE KEY uq_employee_date (employee_id, attendance_date),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Admin', 'HR') NOT NULL DEFAULT 'HR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_audit (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    attendance_id INT NULL,
    employee_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    action_type ENUM('CREATE', 'CORRECT') NOT NULL,
    previous_status ENUM('Present', 'Absent', 'Leave', 'Holiday') NULL,
    new_status ENUM('Present', 'Absent', 'Leave', 'Holiday') NOT NULL,
    correction_reason TEXT NULL,
    user_id INT NULL,
    username VARCHAR(50) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
