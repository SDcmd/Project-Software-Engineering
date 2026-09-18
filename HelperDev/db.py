from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('DEVELOPER','PROJECT_MANAGER','ADMIN'))
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    task_type TEXT NOT NULL CHECK(task_type IN ('REQUIREMENTS','DESIGN','IMPLEMENTATION','BUG_FIX','TESTING','REVIEW','DOCUMENTATION','DEPLOYMENT')),
    priority TEXT NOT NULL CHECK(priority IN ('HIGH','MEDIUM','LOW')),
    progress_status TEXT NOT NULL DEFAULT 'PLANNED' CHECK(progress_status IN ('PLANNED','IN_PROGRESS','DONE')),
    assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    due_date TEXT,
    reminder_at TEXT,
    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
    github_url TEXT,
    github_kind TEXT,
    github_repo TEXT,
    github_number INTEGER,
    github_state TEXT,
    github_title TEXT,
    github_synced_at TEXT,
    github_auto_complete INTEGER NOT NULL DEFAULT 0 CHECK(github_auto_complete IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    prerequisite_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY(task_id, prerequisite_id),
    CHECK(task_id <> prerequisite_id)
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA)
