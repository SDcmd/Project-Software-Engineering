from __future__ import annotations

import re
import sqlite3

from ..security import hash_password


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
VALID_ROLES = {"DEVELOPER", "PROJECT_MANAGER", "ADMIN"}


class UserService:
    """Account creation, lookup, and administrator-controlled role management."""

    def __init__(self, database):
        self.database = database

    def create_developer_account(self, username: str, password: str) -> int:
        """Create a self-service Developer account and return its database id.

        Self-service registration deliberately cannot create privileged roles. Project
        Manager and Administrator privileges are never user-selectable at registration.
        """
        username = (username or "").strip()
        self._validate_username(username)
        self._validate_password(password)

        try:
            with self.database.connect() as conn:
                cur = conn.execute(
                    "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
                    (username, hash_password(password), "DEVELOPER"),
                )
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            if "users.username" in str(exc).lower() or "unique" in str(exc).lower():
                raise ValueError("That username is already in use") from exc
            raise

    def user_by_username(self, username: str):
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT id,username,password_hash,role FROM users WHERE username=?",
                ((username or "").strip(),),
            ).fetchone()
        return dict(row) if row else None

    def user_by_id(self, user_id: int):
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT id,username,role FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict]:
        """Return public account metadata only; password hashes are never exposed."""
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT id,username,role FROM users ORDER BY username COLLATE NOCASE, id"
            ).fetchall()
        return [dict(row) for row in rows]

    def change_role(self, user_id: int, new_role: str) -> dict:
        """Change a user's role while preserving at least one Administrator account."""
        new_role = (new_role or "").strip().upper()
        if new_role not in VALID_ROLES:
            raise ValueError("Invalid role")

        with self.database.connect() as conn:
            # Serialize role changes so the last-administrator invariant is checked
            # and updated in one write transaction.
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT id,username,role FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            if not row:
                raise ValueError("User does not exist")

            current_role = row["role"]
            if current_role == new_role:
                return dict(row)

            if current_role == "ADMIN" and new_role != "ADMIN":
                admin_count = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role='ADMIN'"
                ).fetchone()[0]
                if admin_count <= 1:
                    raise ValueError(
                        "The last Administrator cannot be demoted. Promote another user to Administrator first."
                    )

            conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
            updated = conn.execute(
                "SELECT id,username,role FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            return dict(updated)

    @staticmethod
    def _validate_username(username: str) -> None:
        if not USERNAME_RE.fullmatch(username):
            raise ValueError(
                "Username must be 3-32 characters and use only letters, numbers, dots, underscores, or hyphens"
            )

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password or "") < 8:
            raise ValueError("Password must contain at least 8 characters")
        if len(password) > 128:
            raise ValueError("Password must not exceed 128 characters")
