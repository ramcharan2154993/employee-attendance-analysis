"""Authentication and authorization management module."""

import os
import secrets
from typing import Any
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from werkzeug.security import check_password_hash, generate_password_hash

VALID_ROLES = ("Admin", "HR")


def create_user(
    conn: MySQLConnectionAbstract,
    username: str,
    password: str,
    role: str = "HR",
) -> int:
    """Create a new system user with hashed password and role ('Admin' or 'HR')."""
    if not username or not username.strip():
        raise ValueError("Username cannot be blank.")
    clean_username = username.strip()

    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    clean_role = role.strip()
    if clean_role not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{clean_role}'. Must be one of: {', '.join(VALID_ROLES)}."
        )

    pwd_hash = generate_password_hash(password)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, role, is_active)
            VALUES (%s, %s, %s, TRUE)
            """,
            (clean_username, pwd_hash, clean_role),
        )
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062:
            raise ValueError(f"Username '{clean_username}' already exists.") from err
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def authenticate_user(
    conn: MySQLConnectionAbstract,
    username: str,
    password: str,
) -> dict[str, Any] | None:
    """Verify credentials and return user dict if valid and active, else None."""
    if not username or not password:
        return None

    clean_username = username.strip()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, username, password_hash, role, is_active
            FROM users
            WHERE username = %s
            """,
            (clean_username,),
        )
        user = cursor.fetchone()
        if not user or not user["is_active"]:
            return None

        if not check_password_hash(user["password_hash"], password):
            return None

        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "is_active": bool(user["is_active"]),
        }
    finally:
        cursor.close()


def get_user_by_id(
    conn: MySQLConnectionAbstract,
    user_id: int,
) -> dict[str, Any] | None:
    """Retrieve user details by user_id without password hash."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, username, role, is_active, created_at
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        user = cursor.fetchone()
        if user:
            user["is_active"] = bool(user["is_active"])
        return user
    finally:
        cursor.close()


def get_user_by_username(
    conn: MySQLConnectionAbstract,
    username: str,
) -> dict[str, Any] | None:
    """Retrieve user details by username without password hash."""
    if not username:
        return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, username, role, is_active, created_at
            FROM users
            WHERE username = %s
            """,
            (username.strip(),),
        )
        user = cursor.fetchone()
        if user:
            user["is_active"] = bool(user["is_active"])
        return user
    finally:
        cursor.close()


def list_users(conn: MySQLConnectionAbstract) -> list[dict[str, Any]]:
    """Return all system users ordered by username."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, username, role, is_active, created_at
            FROM users
            ORDER BY username
            """
        )
        rows = cursor.fetchall()
        for r in rows:
            r["is_active"] = bool(r["is_active"])
        return rows
    finally:
        cursor.close()


def update_user_role(
    conn: MySQLConnectionAbstract,
    user_id: int,
    new_role: str,
) -> None:
    """Update role of an existing user."""
    clean_role = new_role.strip()
    if clean_role not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{clean_role}'. Must be one of: {', '.join(VALID_ROLES)}."
        )

    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET role = %s WHERE user_id = %s",
            (clean_role, user_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"User with ID {user_id} not found.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def toggle_user_status(conn: MySQLConnectionAbstract, user_id: int) -> bool:
    """Toggle is_active flag for a user. Prevents deactivating the sole active Admin."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, username, role, is_active FROM users WHERE user_id = %s",
            (user_id,),
        )
        user = cursor.fetchone()
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")

        current_active = bool(user["is_active"])
        # If deactivating an Admin, check that at least one other active Admin remains
        if current_active and user["role"] == "Admin":
            cursor.execute(
                "SELECT COUNT(*) as count FROM users WHERE role = 'Admin' AND is_active = TRUE AND user_id != %s",
                (user_id,),
            )
            res = cursor.fetchone()
            if not res or res["count"] == 0:
                raise ValueError("Cannot deactivate the sole remaining active Admin.")

        new_status = not current_active
        cursor.execute(
            "UPDATE users SET is_active = %s WHERE user_id = %s",
            (new_status, user_id),
        )
        conn.commit()
        return new_status
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def provision_initial_admin(
    conn: MySQLConnectionAbstract,
    username: str = "admin",
    password: str | None = None,
) -> tuple[str, str]:
    """Provision initial admin user if no admin exists. Returns (username, password)."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, username FROM users WHERE role = 'Admin' LIMIT 1")
        existing_admin = cursor.fetchone()
        if existing_admin:
            return (existing_admin["username"], "")

        # Determine password
        pwd = password
        if not pwd:
            pwd = os.getenv("ADMIN_INITIAL_PASSWORD")
        if not pwd:
            pwd = secrets.token_urlsafe(12)

        create_user(conn, username=username, password=pwd, role="Admin")
        return (username, pwd)
    finally:
        cursor.close()


if __name__ == "__main__":
    import argparse
    import getpass
    from src.db import get_connection

    parser = argparse.ArgumentParser(description="User and Admin Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    admin_parser = subparsers.add_parser("create-admin", help="Provision or create an Admin user")
    admin_parser.add_argument("--username", default="admin", help="Admin username (default: admin)")
    admin_parser.add_argument("--database", default=None, help="Database name")

    user_parser = subparsers.add_parser("create-user", help="Create an HR or Admin user")
    user_parser.add_argument("--username", required=True, help="Username")
    user_parser.add_argument("--role", default="HR", choices=["HR", "Admin"], help="User role")
    user_parser.add_argument("--database", default=None, help="Database name")

    list_parser = subparsers.add_parser("list-users", help="List all users")
    list_parser.add_argument("--database", default=None, help="Database name")

    args = parser.parse_args()
    if args.command == "create-admin":
        conn = get_connection(args.database)
        try:
            pwd = getpass.getpass(f"Enter password for admin '{args.username}': ")
            pwd_confirm = getpass.getpass("Confirm password: ")
            if pwd != pwd_confirm:
                print("Error: Passwords do not match.")
                exit(1)
            create_user(conn, username=args.username, password=pwd, role="Admin")
            print(f"Admin user '{args.username}' created successfully.")
        finally:
            conn.close()
    elif args.command == "create-user":
        conn = get_connection(args.database)
        try:
            pwd = getpass.getpass(f"Enter password for user '{args.username}': ")
            pwd_confirm = getpass.getpass("Confirm password: ")
            if pwd != pwd_confirm:
                print("Error: Passwords do not match.")
                exit(1)
            create_user(conn, username=args.username, password=pwd, role=args.role)
            print(f"User '{args.username}' ({args.role}) created successfully.")
        finally:
            conn.close()
    elif args.command == "list-users":
        conn = get_connection(args.database)
        try:
            users = list_users(conn)
            print(f"{'ID':<6} {'Username':<20} {'Role':<10} {'Active':<8} {'Created At'}")
            print("-" * 65)
            for u in users:
                print(f"{u['user_id']:<6} {u['username']:<20} {u['role']:<10} {str(u['is_active']):<8} {u['created_at']}")
        finally:
            conn.close()
    else:
        parser.print_help()
