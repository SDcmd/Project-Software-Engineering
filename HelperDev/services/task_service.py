from __future__ import annotations

from datetime import datetime

PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
VALID_TASK_TYPES = {"REQUIREMENTS", "DESIGN", "IMPLEMENTATION", "BUG_FIX", "TESTING", "REVIEW", "DOCUMENTATION", "DEPLOYMENT"}
VALID_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


class TaskService:
    def __init__(self, db, dependency_service):
        self.db = db
        self.dependencies = dependency_service

    def create_task(self, project_id: int, title: str, description: str, task_type: str,
                    priority: str, assignee_id: int | None, due_date: str | None = None,
                    reminder_at: str | None = None):
        self._validate_fields(title, task_type, priority, due_date, reminder_at)
        due_date = due_date or None
        reminder_at = reminder_at or None
        with self.db.connect() as conn:
            if not conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ValueError("Project does not exist")
            if assignee_id and not conn.execute("SELECT 1 FROM users WHERE id=?", (assignee_id,)).fetchone():
                raise ValueError("Assignee does not exist")
            cur = conn.execute(
                """INSERT INTO tasks(project_id,title,description,task_type,priority,assignee_id,due_date,reminder_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (project_id, title.strip(), description.strip(), task_type, priority, assignee_id, due_date, reminder_at),
            )
            return cur.lastrowid

    def update_task(self, task_id: int, title: str, description: str, task_type: str,
                    priority: str, assignee_id: int | None, due_date: str | None = None,
                    reminder_at: str | None = None):
        self._validate_fields(title, task_type, priority, due_date, reminder_at)
        due_date = due_date or None
        reminder_at = reminder_at or None
        with self.db.connect() as conn:
            cur = conn.execute(
                """UPDATE tasks
                   SET title=?, description=?, task_type=?, priority=?, assignee_id=?, due_date=?, reminder_at=?
                   WHERE id=? AND archived=0""",
                (title.strip(), description.strip(), task_type, priority, assignee_id, due_date, reminder_at, task_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Task does not exist or is archived")

    def delete_task(self, task_id: int) -> int:
        with self.db.connect() as conn:
            row = conn.execute("SELECT project_id FROM tasks WHERE id=? AND archived=0", (task_id,)).fetchone()
            if not row:
                raise ValueError("Task does not exist")
            project_id = row["project_id"]
            # Foreign-key cascades remove dependency edges involving the task.
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return project_id

    def archive_task(self, task_id: int):
        with self.db.connect() as conn:
            task = conn.execute("SELECT project_id FROM tasks WHERE id=? AND archived=0", (task_id,)).fetchone()
            if not task:
                raise ValueError("Task does not exist or is already archived")
            active_dependents = conn.execute(
                """SELECT d.task_id
                   FROM task_dependencies d
                   JOIN tasks t ON t.id=d.task_id
                   WHERE d.prerequisite_id=? AND t.archived=0""",
                (task_id,),
            ).fetchall()
            if active_dependents:
                raise ValueError("Remove active dependency relationships before archiving this task")
            conn.execute("UPDATE tasks SET archived=1 WHERE id=?", (task_id,))
        return task["project_id"]

    def set_progress_status(self, task_id: int, new_status: str):
        if new_status not in {"PLANNED", "IN_PROGRESS", "DONE"}:
            raise ValueError("Invalid status")

        task = self.task(task_id)
        if not task:
            raise ValueError("Task does not exist or is archived")

        current_status = task["progress_status"]
        if new_status == "IN_PROGRESS":
            if current_status != "PLANNED":
                raise ValueError("Only a planned task can be started")
            if self.dependencies.readiness(task_id).effective_state != "READY":
                raise ValueError("Only a ready task can be started")
        elif new_status == "DONE" and current_status != "IN_PROGRESS":
            raise ValueError("Only an in-progress task can be completed")

        with self.db.connect() as conn:
            cur = conn.execute(
                "UPDATE tasks SET progress_status=? WHERE id=? AND archived=0",
                (new_status, task_id),
            )
            if cur.rowcount == 0:
                raise ValueError("Task does not exist or is archived")

    def task(self, task_id: int):
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id=? AND archived=0", (task_id,)).fetchone()
        return dict(row) if row else None

    def project_tasks(self, project_id: int, sort_by: str = "priority", direction: str = "asc"):
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT t.*, u.username AS assignee
                   FROM tasks t LEFT JOIN users u ON u.id=t.assignee_id
                   WHERE t.project_id=? AND t.archived=0""", (project_id,)
            ).fetchall()
        result = []
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_dt = datetime.now().strftime("%Y-%m-%dT%H:%M")
        for row in rows:
            item = dict(row)
            r = self.dependencies.readiness(row["id"])
            item["effective_state"] = r.effective_state
            item["blocker_ids"] = list(r.blocker_ids)
            item["prerequisites"] = self.dependencies.prerequisite_details(row["id"])
            item["overdue"] = bool(item.get("due_date") and item["due_date"] < now_date and item["progress_status"] != "DONE")
            item["reminder_due"] = bool(item.get("reminder_at") and item["reminder_at"] <= now_dt and item["progress_status"] != "DONE")
            result.append(item)

        def key(t):
            if sort_by == "due":
                return (t.get("due_date") or "9999-12-31", PRIORITY_ORDER[t["priority"]], t["id"])
            if sort_by == "title":
                return (t["title"].lower(), t["id"])
            if sort_by == "created":
                return (t.get("created_at") or "", t["id"])
            return (PRIORITY_ORDER[t["priority"]], t.get("due_date") or "9999-12-31", t["id"])

        result.sort(key=key, reverse=(direction == "desc"))
        return result

    def ready_for_user(self, user_id: int):
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT t.*, p.name AS project_name
                   FROM tasks t JOIN projects p ON p.id=t.project_id
                   WHERE t.assignee_id=? AND t.progress_status='PLANNED' AND t.archived=0""",
                (user_id,),
            ).fetchall()
        result = []
        for row in rows:
            if self.dependencies.readiness(row["id"]).effective_state == "READY":
                result.append(dict(row))
        result.sort(key=lambda t: (PRIORITY_ORDER[t["priority"]], t.get("due_date") or "9999-12-31", t["id"]))
        return result


    def set_reminder(self, task_id: int, reminder_at: str):
        if not reminder_at:
            raise ValueError("Reminder date and time are required")
        try:
            datetime.strptime(reminder_at, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValueError("Reminder must be a valid date and time")
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT progress_status FROM tasks WHERE id=? AND archived=0",
                (task_id,),
            ).fetchone()
            if not row:
                raise ValueError("Task does not exist or is archived")
            if row["progress_status"] == "DONE":
                raise ValueError("A reminder cannot be set for a completed task")
            conn.execute("UPDATE tasks SET reminder_at=? WHERE id=?", (reminder_at, task_id))

    def reminder_candidates(self, user_id: int, include_all: bool = False):
        with self.db.connect() as conn:
            if include_all:
                rows = conn.execute(
                    """SELECT t.id,t.project_id,t.title,t.due_date,t.reminder_at,t.assignee_id,p.name AS project_name
                       FROM tasks t JOIN projects p ON p.id=t.project_id
                       WHERE t.archived=0 AND t.progress_status!='DONE'
                       ORDER BY p.name,t.title"""
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT t.id,t.project_id,t.title,t.due_date,t.reminder_at,t.assignee_id,p.name AS project_name
                       FROM tasks t JOIN projects p ON p.id=t.project_id
                       WHERE t.archived=0 AND t.progress_status!='DONE' AND t.assignee_id=?
                       ORDER BY p.name,t.title""",
                    (user_id,),
                ).fetchall()
        return [dict(r) for r in rows]

    def calendar_tasks(self, year: int, month: int):
        prefix = f"{year:04d}-{month:02d}-%"
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT t.*, p.name AS project_name, u.username AS assignee
                   FROM tasks t
                   JOIN projects p ON p.id=t.project_id
                   LEFT JOIN users u ON u.id=t.assignee_id
                   WHERE t.archived=0 AND t.due_date LIKE ?
                   ORDER BY t.due_date, CASE t.priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END, t.id""",
                (prefix,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["effective_state"] = self.dependencies.readiness(row["id"]).effective_state
            result.append(item)
        return result

    def due_reminders_for_user(self, user_id: int):
        now_dt = datetime.now().strftime("%Y-%m-%dT%H:%M")
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT t.*, p.name AS project_name
                   FROM tasks t JOIN projects p ON p.id=t.project_id
                   WHERE t.assignee_id=? AND t.archived=0 AND t.progress_status!='DONE'
                     AND t.reminder_at IS NOT NULL AND t.reminder_at <= ?
                   ORDER BY t.reminder_at, CASE t.priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END""",
                (user_id, now_dt),
            ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _validate_fields(title: str, task_type: str, priority: str, due_date: str | None, reminder_at: str | None):
        if not title or not title.strip():
            raise ValueError("Task title is required")
        if task_type not in VALID_TASK_TYPES:
            raise ValueError("Invalid task type")
        if priority not in VALID_PRIORITIES:
            raise ValueError("Invalid priority")
        if due_date:
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Due date must be a valid date")
        if reminder_at:
            try:
                datetime.strptime(reminder_at, "%Y-%m-%dT%H:%M")
            except ValueError:
                raise ValueError("Reminder must be a valid date and time")
