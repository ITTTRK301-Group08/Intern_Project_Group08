from __future__ import annotations

import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import SessionLocal
from app.services.catalog_service import bootstrap_admin


def main() -> int:
    if not sys.stdin.isatty():
        print(
            "Run this command directly in an interactive terminal to enter the Admin password securely.",
            file=sys.stderr,
        )
        return 2

    try:
        email = TypeAdapter(EmailStr).validate_python(
            input("Admin email: ").strip()
        )
    except (ValidationError, EOFError, ValueError):
        print("Enter a valid Admin email address.", file=sys.stderr)
        return 2

    try:
        password = getpass.getpass("Admin password (input hidden): ")
        confirmation = getpass.getpass("Confirm Admin password: ")
    except EOFError:
        print("Password input was interrupted.", file=sys.stderr)
        return 2

    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2
    try:
        password_length = len(password.encode("utf-8"))
    except UnicodeEncodeError:
        print("Admin password must contain valid UTF-8 characters.", file=sys.stderr)
        return 2
    if password_length < 8 or password_length > 72:
        print("Admin password must be between 8 and 72 UTF-8 bytes.", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        admin, created = bootstrap_admin(db, email=str(email), password=password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        db.rollback()
        print(
            f"Admin bootstrap failed ({type(exc).__name__}). Check database connectivity and try again.",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    action = "Created" if created else "Already exists"
    print(f"{action} admin account: {admin.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
