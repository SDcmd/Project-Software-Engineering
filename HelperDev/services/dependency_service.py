from __future__ import annotations

from dataclasses import dataclass


class DependencyError(ValueError):
    pass


@dataclass(frozen=True)
class Readiness:
    effective_state: str
    blocker_ids: tuple[int, ...]


class DependencyService:
    """Keeps task-dependency rules in one cohesive service."""

    def __init__(self, db):
        self.db = db

    def prerequisite_ids(self, task_id: int) -> list[int]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT prerequisite_id FROM task_dependencies WHERE task_id=? ORDER BY prerequisite_id",
                (task_id,),
            ).fetchall()
        return [r[0] for r in rows]

    def prerequisite_details(self, task_id: int) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT p.id, p.title, p.progress_status
                   FROM task_dependencies d
                   JOIN tasks p ON p.id=d.prerequisite_id
                   WHERE d.task_id=?
                   ORDER BY p.id""",
                (task_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def dependent_ids(self, task_id: int) -> list[int]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT task_id FROM task_dependencies WHERE prerequisite_id=? ORDER BY task_id",
                (task_id,),
            ).fetchall()
        return [r[0] for r in rows]

    def readiness(self, task_id: int) -> Readiness:
        with self.db.connect() as conn:
            task = conn.execute("SELECT progress_status,archived FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task or task["archived"]:
                raise DependencyError("Task does not exist")
            if task["progress_status"] == "DONE":
                return Readiness("DONE", ())
            if task["progress_status"] == "IN_PROGRESS":
                return Readiness("IN_PROGRESS", ())
            blockers = conn.execute(
                """
                SELECT p.id
                FROM task_dependencies d
                JOIN tasks p ON p.id=d.prerequisite_id
                WHERE d.task_id=? AND p.progress_status <> 'DONE' AND p.archived=0
                ORDER BY p.id
                """,
                (task_id,),
            ).fetchall()
        blocker_ids = tuple(r[0] for r in blockers)
        return Readiness("BLOCKED" if blocker_ids else "READY", blocker_ids)

    def add_dependency(self, task_id: int, prerequisite_id: int) -> None:
        if task_id == prerequisite_id:
            raise DependencyError("A task cannot depend on itself")
        with self.db.connect() as conn:
            task = conn.execute("SELECT project_id,archived FROM tasks WHERE id=?", (task_id,)).fetchone()
            prereq = conn.execute("SELECT project_id,archived FROM tasks WHERE id=?", (prerequisite_id,)).fetchone()
            if not task or not prereq or task["archived"] or prereq["archived"]:
                raise DependencyError("Both active tasks must exist")
            if task["project_id"] != prereq["project_id"]:
                raise DependencyError("Dependencies must stay within one project in this prototype")
            exists = conn.execute(
                "SELECT 1 FROM task_dependencies WHERE task_id=? AND prerequisite_id=?",
                (task_id, prerequisite_id),
            ).fetchone()
            if exists:
                raise DependencyError("Dependency already exists")
            if self._path_exists(conn, start=prerequisite_id, target=task_id):
                raise DependencyError("Dependency would create a circular dependency")
            conn.execute(
                "INSERT INTO task_dependencies(task_id, prerequisite_id) VALUES (?, ?)",
                (task_id, prerequisite_id),
            )

    def remove_dependency(self, task_id: int, prerequisite_id: int) -> None:
        with self.db.connect() as conn:
            cur = conn.execute(
                "DELETE FROM task_dependencies WHERE task_id=? AND prerequisite_id=?",
                (task_id, prerequisite_id),
            )
            if cur.rowcount == 0:
                raise DependencyError("Dependency does not exist")

    def _path_exists(self, conn, start: int, target: int) -> bool:
        """Return True if `start` already depends (directly/transitively) on `target`."""
        stack = [start]
        visited: set[int] = set()
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            rows = conn.execute(
                "SELECT prerequisite_id FROM task_dependencies WHERE task_id=?",
                (current,),
            ).fetchall()
            stack.extend(r[0] for r in rows)
        return False
