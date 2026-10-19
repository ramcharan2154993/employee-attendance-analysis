"""CLI tool to interactively create or provision an initial Administrator account."""

import argparse
import getpass
import sys
from typing import Sequence
import mysql.connector
from src.auth import create_user, get_user_by_username
from src.db import get_connection


def main(argv: Sequence[str] | None = None) -> int:
    """Prompt for credentials interactively and create an Admin user."""
    parser = argparse.ArgumentParser(
        description="Create an Admin user account interactively."
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Username for the new Admin (prompted if omitted)",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Database name (defaults to DB_NAME from environment)",
    )
    args = parser.parse_args(argv)

    username = args.username
    if not username:
        try:
            username = input("Enter admin username (default: admin): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return 1
        if not username:
            username = "admin"

    try:
        conn = get_connection(args.database)
    except Exception as exc:
        print(f"Error connecting to database: {exc}", file=sys.stderr)
        return 1

    try:
        existing = get_user_by_username(conn, username)
        if existing:
            print(f"Error: Username '{username}' already exists.", file=sys.stderr)
            return 1

        try:
            pwd = getpass.getpass(f"Enter password for admin '{username}' (min 10 chars): ")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return 1

        if len(pwd) < 10:
            print(
                "Error: Password must be at least 10 characters long.",
                file=sys.stderr,
            )
            return 1

        try:
            pwd_confirm = getpass.getpass("Confirm password: ")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return 1

        if pwd != pwd_confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            return 1

        create_user(conn, username=username, password=pwd, role="Admin")
        print(f"Admin user '{username}' created successfully.")
        return 0
    except mysql.connector.Error as err:
        print(f"Database error: {err}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
