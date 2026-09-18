from datetime import datetime, timedelta

from .security import hash_password


def seed_demo(db):
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return
        users = [
            ("dev", hash_password("dev123"), "DEVELOPER"),
            ("pm", hash_password("pm123"), "PROJECT_MANAGER"),
            ("admin", hash_password("admin123"), "ADMIN"),
        ]
        conn.executemany("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)", users)
        dev_id = conn.execute("SELECT id FROM users WHERE username='dev'").fetchone()[0]
        pm_id = conn.execute("SELECT id FROM users WHERE username='pm'").fetchone()[0]
        cur = conn.execute(
            "INSERT INTO projects(name,description) VALUES (?,?)",
            ("Authentication Module", "Dependency-aware plan for a small web authentication feature."),
        )
        project_id = cur.lastrowid
        now = datetime.now()
        d1 = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        d2 = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        d3 = (now + timedelta(days=3)).strftime("%Y-%m-%d")
        d4 = (now + timedelta(days=4)).strftime("%Y-%m-%d")
        reminder_due = (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")
        tasks = [
            (project_id, "Define login requirements", "Specify login behaviour and acceptance criteria.", "REQUIREMENTS", "HIGH", "DONE", pm_id, d1, None),
            (project_id, "Design user data model", "Define user fields and persistence constraints.", "DESIGN", "HIGH", "DONE", dev_id, d1, None),
            (project_id, "Implement authentication service", "Implement credential verification and session creation.", "IMPLEMENTATION", "HIGH", "PLANNED", dev_id, d2, reminder_due),
            (project_id, "Build login interface", "Create login form and error feedback.", "IMPLEMENTATION", "MEDIUM", "PLANNED", dev_id, d3, None),
            (project_id, "Write authentication tests", "Cover successful and failed login paths.", "TESTING", "HIGH", "PLANNED", dev_id, d3, None),
            (project_id, "Perform code review", "Review implementation and test coverage.", "REVIEW", "MEDIUM", "PLANNED", pm_id, d4, None),
        ]
        conn.executemany(
            """INSERT INTO tasks(project_id,title,description,task_type,priority,progress_status,assignee_id,due_date,reminder_at)
               VALUES (?,?,?,?,?,?,?,?,?)""", tasks
        )
        ids = {r["title"]: r["id"] for r in conn.execute("SELECT id,title FROM tasks").fetchall()}
        deps = [
            (ids["Implement authentication service"], ids["Define login requirements"]),
            (ids["Implement authentication service"], ids["Design user data model"]),
            (ids["Build login interface"], ids["Implement authentication service"]),
            (ids["Write authentication tests"], ids["Implement authentication service"]),
            (ids["Perform code review"], ids["Build login interface"]),
            (ids["Perform code review"], ids["Write authentication tests"]),
        ]
        conn.executemany("INSERT INTO task_dependencies(task_id,prerequisite_id) VALUES (?,?)", deps)
