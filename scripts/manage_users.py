"""User management CLI — create, reset, list, or deactivate users directly in the DB.

Usage (no API credentials required):
    python -m scripts.manage_users list
    python -m scripts.manage_users create <username> <password> [--role admin|analyst|viewer]
    python -m scripts.manage_users reset <username> <new_password>
    python -m scripts.manage_users activate <username>
    python -m scripts.manage_users deactivate <username>
    python -m scripts.manage_users delete <username>
"""

import sys

from sqlalchemy import text

from app.auth.jwt import hash_password
from app.database import Base, SessionLocal, get_engine
from app.models.user import User


def _ensure_tables():
    Base.metadata.create_all(bind=get_engine())


def cmd_list():
    _ensure_tables()
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.username).all()
        if not users:
            print("No users found.")
            return
        print(f"{'ID':<6} {'Username':<20} {'Role':<12} {'Active':<8} {'Created'}")
        print("-" * 65)
        for u in users:
            created = u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "unknown"
            print(f"{u.id:<6} {u.username:<20} {u.role:<12} {str(u.is_active):<8} {created}")
    finally:
        db.close()


def cmd_create(username: str, password: str, role: str = "analyst"):
    if role not in ("admin", "analyst", "viewer"):
        print(f"Invalid role '{role}'. Choose: admin, analyst, viewer")
        sys.exit(1)
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)
    _ensure_tables()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"User '{username}' already exists.")
            sys.exit(1)
        user = User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"User '{username}' created with role '{role}'.")
    finally:
        db.close()


def cmd_reset(username: str, new_password: str):
    if len(new_password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)
    _ensure_tables()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)
        user.hashed_password = hash_password(new_password)
        db.commit()
        print(f"Password reset for '{username}'.")
    finally:
        db.close()


def cmd_activate(username: str, active: bool):
    _ensure_tables()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)
        user.is_active = active
        db.commit()
        state = "activated" if active else "deactivated"
        print(f"User '{username}' {state}.")
    finally:
        db.close()


def cmd_delete(username: str):
    _ensure_tables()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' not found.")
            sys.exit(1)
        confirm = input(f"Delete user '{username}' permanently? [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return
        db.delete(user)
        db.commit()
        print(f"User '{username}' deleted.")
    finally:
        db.close()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "list":
        cmd_list()

    elif cmd == "create":
        if len(args) < 3:
            print("Usage: manage_users create <username> <password> [--role admin|analyst|viewer]")
            sys.exit(1)
        username, password = args[1], args[2]
        role = "analyst"
        if "--role" in args:
            idx = args.index("--role")
            if idx + 1 < len(args):
                role = args[idx + 1]
        cmd_create(username, password, role)

    elif cmd == "reset":
        if len(args) < 3:
            print("Usage: manage_users reset <username> <new_password>")
            sys.exit(1)
        cmd_reset(args[1], args[2])

    elif cmd == "activate":
        if len(args) < 2:
            print("Usage: manage_users activate <username>")
            sys.exit(1)
        cmd_activate(args[1], True)

    elif cmd == "deactivate":
        if len(args) < 2:
            print("Usage: manage_users deactivate <username>")
            sys.exit(1)
        cmd_activate(args[1], False)

    elif cmd == "delete":
        if len(args) < 2:
            print("Usage: manage_users delete <username>")
            sys.exit(1)
        cmd_delete(args[1])

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
