from __future__ import annotations


class ProjectService:
    """Application-level operations for creating and viewing projects."""

    def __init__(self, db):
        self.db = db

    def create_project(self, name: str, description: str = "") -> int:
        if not name or not name.strip():
            raise ValueError("Project name is required")
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO projects(name,description) VALUES (?,?)",
                (name.strip(), description.strip()),
            )
            return cur.lastrowid

    def get_project(self, project_id: int):
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return dict(row) if row else None

    def list_projects(self):
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT p.id,p.name,p.description,COUNT(t.id) AS task_count
                   FROM projects p
                   LEFT JOIN tasks t ON t.project_id=p.id AND t.archived=0
                   GROUP BY p.id,p.name,p.description
                   ORDER BY p.id"""
            ).fetchall()
        return [dict(r) for r in rows]
