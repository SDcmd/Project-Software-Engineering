from __future__ import annotations

import calendar as pycalendar
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .db import Database
from .security import verify_password
from .seed import seed_demo
from .services.dependency_service import DependencyService, DependencyError
from .services.task_service import TaskService
from .services.project_service import ProjectService
from .services.github_service import GitHubService, GitHubIntegrationError
from .services.user_service import UserService, VALID_ROLES

BASE = Path(__file__).resolve().parent
TASK_TYPES = ["REQUIREMENTS", "DESIGN", "IMPLEMENTATION", "BUG_FIX", "TESTING", "REVIEW", "DOCUMENTATION", "DEPLOYMENT"]
PRIORITIES = ["HIGH", "MEDIUM", "LOW"]


def create_app(db_path: str | None = None, seed: bool = True) -> FastAPI:
    app = FastAPI(title="HelperDev")
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("HELPERDEV_SECRET", "prototype-only-change-me"),
        same_site="lax",
        https_only=False,
    )
    app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
    templates = Jinja2Templates(directory=BASE / "templates")
    database = Database(db_path or str(BASE.parent / "HelperDev.db"))
    database.init()
    if seed:
        seed_demo(database)
    dependencies = DependencyService(database)
    tasks = TaskService(database, dependencies)
    projects = ProjectService(database)
    github = GitHubService(database)
    users_service = UserService(database)
    app.state.database = database
    app.state.dependencies = dependencies
    app.state.tasks = tasks
    app.state.projects = projects
    app.state.github = github
    app.state.users = users_service

    def current_user(request: Request):
        uid = request.session.get("user_id")
        if not uid:
            return None
        with database.connect() as conn:
            row = conn.execute("SELECT id,username,role FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None

    def require_user(request: Request):
        return current_user(request)

    def is_manager(user: dict) -> bool:
        return user["role"] in {"PROJECT_MANAGER", "ADMIN"}

    def is_admin(user: dict) -> bool:
        return user["role"] == "ADMIN"

    def can_modify_task(user: dict, task: dict) -> bool:
        return is_manager(user) or task.get("assignee_id") == user["id"]

    def task_project_id(task_id: int) -> int | None:
        with database.connect() as conn:
            row = conn.execute("SELECT project_id FROM tasks WHERE id=?", (task_id,)).fetchone()
        return row["project_id"] if row else None

    def project_redirect(project_id: int, *, message: str | None = None, error: str | None = None):
        suffix = ""
        if message:
            suffix = "?message=" + quote_plus(message)
        elif error:
            suffix = "?error=" + quote_plus(error)
        return RedirectResponse(f"/projects/{project_id}{suffix}", status_code=303)

    def calendar_redirect(year: int, month: int, *, message: str | None = None, error: str | None = None):
        params = f"year={year}&month={month}"
        if message:
            params += "&message=" + quote_plus(message)
        elif error:
            params += "&error=" + quote_plus(error)
        return RedirectResponse(f"/calendar?{params}", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        if not current_user(request):
            return RedirectResponse("/login", status_code=303)
        return RedirectResponse("/projects", status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, error: str | None = None):
        return templates.TemplateResponse(request, "login.html", {"error": error})

    @app.post("/login")
    def login(request: Request, username: str = Form(...), password: str = Form(...)):
        with database.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return RedirectResponse("/login?error=Invalid+username+or+password", status_code=303)
        request.session["user_id"] = row["id"]
        return RedirectResponse("/projects", status_code=303)

    @app.get("/register", response_class=HTMLResponse)
    def register_page(request: Request, error: str | None = None, username: str = ""):
        if current_user(request):
            return RedirectResponse("/projects", status_code=303)
        return templates.TemplateResponse(request, "register.html", {"error": error, "username": username})

    @app.post("/register", response_class=HTMLResponse)
    def register(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        if current_user(request):
            return RedirectResponse("/projects", status_code=303)
        username = username.strip()
        if password != confirm_password:
            return templates.TemplateResponse(
                request, "register.html",
                {
                    "error": "Password confirmation error: Passwords do not match",
                    "error_field": "confirm_password",
                    "username": username,
                },
                status_code=400,
            )
        try:
            user_id = users_service.create_developer_account(username, password)
        except ValueError as exc:
            message = str(exc)
            lowered = message.lower()
            if "username" in lowered:
                field = "username"
                message = f"Username error: {message}"
            else:
                field = "password"
                message = f"Password error: {message}"
            return templates.TemplateResponse(
                request, "register.html",
                {"error": message, "error_field": field, "username": username},
                status_code=400,
            )
        request.session.clear()
        request.session["user_id"] = user_id
        return RedirectResponse("/projects?message=Account+created+successfully", status_code=303)

    @app.post("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.post("/switch-account")
    def switch_account(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/admin/users", response_class=HTMLResponse)
    def user_management(request: Request, message: str | None = None, error: str | None = None):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        if not is_admin(user):
            raise HTTPException(status_code=403, detail="Administrator access required")
        return templates.TemplateResponse(request, "user_management.html", {
            "user": user,
            "users": users_service.list_users(),
            "role_options": ["DEVELOPER", "PROJECT_MANAGER", "ADMIN"],
            "message": message,
            "error": error,
        })

    @app.post("/admin/users/{user_id}/role")
    def change_user_role(request: Request, user_id: int, role: str = Form(...)):
        actor = require_user(request)
        if not actor:
            return RedirectResponse("/login", status_code=303)
        if not is_admin(actor):
            raise HTTPException(status_code=403, detail="Administrator access required")
        requested_role = (role or "").strip().upper()
        if requested_role not in VALID_ROLES:
            return RedirectResponse(
                "/admin/users?error=" + quote_plus("Invalid role"),
                status_code=303,
            )
        try:
            updated = users_service.change_role(user_id, requested_role)
        except ValueError as exc:
            return RedirectResponse(
                "/admin/users?error=" + quote_plus(str(exc)),
                status_code=303,
            )

        if updated["id"] == actor["id"] and updated["role"] != "ADMIN":
            return RedirectResponse(
                "/projects?message=" + quote_plus(
                    f"Your role was changed to {updated['role'].replace('_', ' ').title()}"
                ),
                status_code=303,
            )
        return RedirectResponse(
            "/admin/users?message=" + quote_plus(
                f"{updated['username']} role changed to {updated['role'].replace('_', ' ').title()}"
            ),
            status_code=303,
        )

    @app.get("/projects", response_class=HTMLResponse)
    def project_list(request: Request, message: str | None = None, error: str | None = None):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(request, "projects.html", {
            "user": user, "projects": projects.list_projects(), "message": message, "error": error,
            "reminders": tasks.due_reminders_for_user(user["id"]),
        })

    @app.post("/projects")
    def create_project(request: Request, name: str = Form(...), description: str = Form("")):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        try:
            project_id = projects.create_project(name, description)
            return project_redirect(project_id, message="Project created")
        except ValueError as exc:
            return RedirectResponse(f"/projects?error={quote_plus(str(exc))}", status_code=303)

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_board(request: Request, project_id: int, message: str | None = None, error: str | None = None,
                      sort: str = "priority", direction: str = "asc"):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        project = projects.get_project(project_id)
        if not project:
            raise HTTPException(404)
        with database.connect() as conn:
            users = conn.execute("SELECT id,username,role FROM users ORDER BY username").fetchall()
        sort = sort if sort in {"priority", "due", "title", "created"} else "priority"
        direction = direction if direction in {"asc", "desc"} else "asc"
        task_list = tasks.project_tasks(project_id, sort, direction)
        by_state = {s: [] for s in ["READY", "BLOCKED", "IN_PROGRESS", "DONE"]}
        for t in task_list:
            by_state[t["effective_state"]].append(t)
        return templates.TemplateResponse(request, "project.html", {
            "user": user, "project": project, "tasks": task_list, "by_state": by_state,
            "users": [dict(u) for u in users], "task_types": TASK_TYPES, "priorities": PRIORITIES,
            "message": message, "error": error, "sort": sort, "direction": direction,
        })

    @app.post("/projects/{project_id}/tasks")
    def create_task(request: Request, project_id: int, title: str = Form(...), description: str = Form(""),
                    task_type: str = Form(...), priority: str = Form(...), assignee_id: int | None = Form(None),
                    due_date: str = Form(""), reminder_at: str = Form(""), github_url: str = Form(""),
                    github_auto_complete: str | None = Form(None)):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        if not is_manager(user):
            assignee_id = user["id"]
        try:
            if github_url.strip():
                github.parse_url(github_url)
            task_id = tasks.create_task(project_id, title, description, task_type, priority, assignee_id, due_date, reminder_at)
            if github_url.strip():
                github.link_task(task_id, github_url, auto_complete=(github_auto_complete == "on"))
            return project_redirect(project_id, message="Task created")
        except (ValueError, GitHubIntegrationError) as exc:
            return project_redirect(project_id, error=str(exc))

    @app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
    def edit_task_page(request: Request, task_id: int, error: str | None = None):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="You can only edit tasks assigned to you")
        with database.connect() as conn:
            users = conn.execute("SELECT id,username,role FROM users ORDER BY username").fetchall()
        return templates.TemplateResponse(request, "edit_task.html", {
            "user": user, "task": task, "users": [dict(u) for u in users],
            "task_types": TASK_TYPES, "priorities": PRIORITIES, "error": error,
        })

    @app.post("/tasks/{task_id}/edit")
    def edit_task(request: Request, task_id: int, title: str = Form(...), description: str = Form(""),
                  task_type: str = Form(...), priority: str = Form(...), assignee_id: int | None = Form(None),
                  due_date: str = Form(""), reminder_at: str = Form(""), github_url: str = Form(""),
                  github_auto_complete: str | None = Form(None)):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="You can only edit tasks assigned to you")
        if not is_manager(user):
            assignee_id = user["id"]
        try:
            if github_url.strip():
                github.parse_url(github_url)
            tasks.update_task(task_id, title, description, task_type, priority, assignee_id, due_date, reminder_at)
            if github_url.strip():
                current = tasks.task(task_id)
                if current.get("github_url") != github.parse_url(github_url).canonical_url or bool(current.get("github_auto_complete")) != (github_auto_complete == "on"):
                    github.link_task(task_id, github_url, auto_complete=(github_auto_complete == "on"))
            elif task.get("github_url"):
                github.unlink_task(task_id)
            return project_redirect(task["project_id"], message="Task updated")
        except (ValueError, GitHubIntegrationError) as exc:
            return RedirectResponse(f"/tasks/{task_id}/edit?error={quote_plus(str(exc))}", status_code=303)

    @app.post("/tasks/{task_id}/delete")
    def delete_task(request: Request, task_id: int):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="You can only delete tasks assigned to you")
        project_id = tasks.delete_task(task_id)
        return project_redirect(project_id, message="Task deleted")

    @app.post("/tasks/{task_id}/dependencies")
    def add_dependency(request: Request, task_id: int, prerequisite_id: int = Form(...)):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="You can only change dependencies for tasks assigned to you")
        try:
            dependencies.add_dependency(task_id, prerequisite_id)
            return project_redirect(task["project_id"], message="Dependency added")
        except DependencyError as exc:
            return project_redirect(task["project_id"], error=str(exc))

    @app.post("/tasks/{task_id}/dependencies/{prerequisite_id}/remove")
    def remove_dependency(request: Request, task_id: int, prerequisite_id: int):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="You can only change dependencies for tasks assigned to you")
        try:
            dependencies.remove_dependency(task_id, prerequisite_id)
            return project_redirect(task["project_id"], message="Dependency removed")
        except DependencyError as exc:
            return project_redirect(task["project_id"], error=str(exc))

    @app.post("/tasks/{task_id}/github/sync")
    def sync_github_task(request: Request, task_id: int):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="Not authorized for that task")
        try:
            result = github.sync_task(task_id)
            if result["auto_completed"]:
                message = f"GitHub synced: pull request {result['state']}; task automatically completed"
            else:
                message = f"GitHub synced: {result['kind'].replace('_',' ').title()} is {result['state']}"
            return project_redirect(task["project_id"], message=message)
        except GitHubIntegrationError as exc:
            return project_redirect(task["project_id"], error=str(exc))

    @app.post("/tasks/{task_id}/github/unlink")
    def unlink_github_task(request: Request, task_id: int):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="Not authorized for that task")
        try:
            github.unlink_task(task_id)
            return project_redirect(task["project_id"], message="GitHub link removed")
        except GitHubIntegrationError as exc:
            return project_redirect(task["project_id"], error=str(exc))

    @app.post("/tasks/{task_id}/start")
    def start_task(request: Request, task_id: int):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="Not authorized for that task")
        try:
            tasks.set_progress_status(task_id, "IN_PROGRESS")
            return project_redirect(task["project_id"], message="Task started")
        except ValueError as exc:
            return project_redirect(task["project_id"], error=str(exc))

    @app.post("/tasks/{task_id}/complete")
    def complete_task(request: Request, task_id: int):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            raise HTTPException(404)
        if not can_modify_task(user, task):
            return project_redirect(task["project_id"], error="Not authorized for that task")
        try:
            tasks.set_progress_status(task_id, "DONE")
            return project_redirect(task["project_id"], message="Task completed - dependent readiness recalculated")
        except ValueError as exc:
            return project_redirect(task["project_id"], error=str(exc))

    @app.get("/ready", response_class=HTMLResponse)
    def ready_queue(request: Request):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        return templates.TemplateResponse(request, "ready.html", {
            "user": user, "tasks": tasks.ready_for_user(user["id"]),
            "reminders": tasks.due_reminders_for_user(user["id"]),
        })

    @app.get("/calendar", response_class=HTMLResponse)
    def calendar_page(request: Request, year: int | None = None, month: int | None = None,
                      message: str | None = None, error: str | None = None):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        if month < 1 or month > 12:
            raise HTTPException(400, "Invalid month")
        month_tasks = tasks.calendar_tasks(year, month)
        by_date: dict[str, list[dict]] = {}
        for t in month_tasks:
            by_date.setdefault(t["due_date"], []).append(t)
        cal = pycalendar.Calendar(firstweekday=0)
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            weeks.append([{
                "date": d.isoformat(), "day": d.day, "in_month": d.month == month,
                "tasks": by_date.get(d.isoformat(), []), "today": d == now.date(),
            } for d in week])
        prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        with database.connect() as conn:
            users = conn.execute("SELECT id,username,role FROM users ORDER BY username").fetchall()
        return templates.TemplateResponse(request, "calendar.html", {
            "user": user, "weeks": weeks, "month_name": pycalendar.month_name[month], "year": year, "month": month,
            "prev_year": prev_year, "prev_month": prev_month, "next_year": next_year, "next_month": next_month,
            "reminders": tasks.due_reminders_for_user(user["id"]),
            "projects": projects.list_projects(), "users": [dict(u) for u in users],
            "task_types": TASK_TYPES, "priorities": PRIORITIES,
            "reminder_candidates": tasks.reminder_candidates(user["id"], include_all=is_manager(user)),
            "message": message, "error": error,
        })

    @app.post("/calendar/tasks")
    def create_task_from_calendar(
        request: Request,
        project_id: int = Form(...),
        title: str = Form(...),
        description: str = Form(""),
        task_type: str = Form(...),
        priority: str = Form(...),
        assignee_id: int | None = Form(None),
        due_date: str = Form(...),
        reminder_at: str = Form(""),
        github_url: str = Form(""),
        github_auto_complete: str | None = Form(None),
        calendar_year: int = Form(...),
        calendar_month: int = Form(...),
    ):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        if not is_manager(user):
            assignee_id = user["id"]
        try:
            if github_url.strip():
                github.parse_url(github_url)
            task_id = tasks.create_task(project_id, title, description, task_type, priority, assignee_id, due_date, reminder_at)
            if github_url.strip():
                github.link_task(task_id, github_url, auto_complete=(github_auto_complete == "on"))
            return calendar_redirect(calendar_year, calendar_month, message="Task created from calendar")
        except (ValueError, GitHubIntegrationError) as exc:
            return calendar_redirect(calendar_year, calendar_month, error=str(exc))

    @app.post("/calendar/reminders")
    def set_task_reminder_from_calendar(
        request: Request,
        task_id: int = Form(...),
        reminder_at: str = Form(...),
        calendar_year: int = Form(...),
        calendar_month: int = Form(...),
    ):
        user = require_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        task = tasks.task(task_id)
        if not task:
            return calendar_redirect(calendar_year, calendar_month, error="Task does not exist")
        if not can_modify_task(user, task):
            return calendar_redirect(calendar_year, calendar_month, error="You can only set reminders for tasks assigned to you")
        try:
            tasks.set_reminder(task_id, reminder_at)
            return calendar_redirect(calendar_year, calendar_month, message="Task reminder scheduled")
        except ValueError as exc:
            return calendar_redirect(calendar_year, calendar_month, error=str(exc))

    return app


app = create_app()
