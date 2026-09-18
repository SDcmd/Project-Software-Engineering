from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from HelperDev.app import create_app
from HelperDev.security import hash_password, verify_password
from HelperDev.services.dependency_service import DependencyError


def make_app(tmp_path):
    app = create_app(str(tmp_path / "test.db"), seed=False)
    db = app.state.database
    with db.connect() as c:
        c.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)", ("d",hash_password("p"),"DEVELOPER"))
        uid=c.execute("SELECT id FROM users WHERE username='d'").fetchone()[0]
        pid=c.execute("INSERT INTO projects(name,description) VALUES ('P','')").lastrowid
        a=c.execute("INSERT INTO tasks(project_id,title,task_type,priority,progress_status,assignee_id) VALUES (?,?,?,?,?,?)",(pid,"A","DESIGN","HIGH","PLANNED",uid)).lastrowid
        b=c.execute("INSERT INTO tasks(project_id,title,task_type,priority,progress_status,assignee_id) VALUES (?,?,?,?,?,?)",(pid,"B","IMPLEMENTATION","HIGH","PLANNED",uid)).lastrowid
        c_id=c.execute("INSERT INTO tasks(project_id,title,task_type,priority,progress_status,assignee_id) VALUES (?,?,?,?,?,?)",(pid,"C","TESTING","MEDIUM","PLANNED",uid)).lastrowid
    return app, uid, a, b, c_id


def test_dependency_blocks_and_completion_unlocks(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    dep=app.state.dependencies; tasks=app.state.tasks
    dep.add_dependency(b,a)
    assert dep.readiness(a).effective_state == "READY"
    assert dep.readiness(b).effective_state == "BLOCKED"
    tasks.set_progress_status(a,"IN_PROGRESS")
    tasks.set_progress_status(a,"DONE")
    assert dep.readiness(b).effective_state == "READY"


def test_cycle_is_rejected(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    dep=app.state.dependencies
    dep.add_dependency(b,a)
    dep.add_dependency(c,b)
    with pytest.raises(DependencyError, match="circular"):
        dep.add_dependency(a,c)


def test_self_dependency_is_rejected(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    with pytest.raises(DependencyError):
        app.state.dependencies.add_dependency(a,a)


def test_ready_queue_returns_only_actionable_tasks(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    app.state.dependencies.add_dependency(b,a)
    q=app.state.tasks.ready_for_user(uid)
    ids={x['id'] for x in q}
    assert a in ids and c in ids and b not in ids


def test_unauthenticated_user_redirected(tmp_path):
    app, *_ = make_app(tmp_path)
    client=TestClient(app)
    r=client.get('/ready', follow_redirects=False)
    assert r.status_code == 303 and r.headers['location']=='/login'


def test_project_manager_can_create_project(tmp_path):
    app = create_app(str(tmp_path / "test.db"), seed=False)
    db = app.state.database
    with db.connect() as c:
        c.execute("INSERT INTO users(username,password_hash,role) VALUES (?,?,?)", ("pm",hash_password("p"),"PROJECT_MANAGER"))
    client = TestClient(app)
    r = client.post('/login', data={'username':'pm','password':'p'}, follow_redirects=False)
    assert r.status_code == 303
    r = client.post('/projects', data={'name':'New Project','description':'Demo'}, follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'].startswith('/projects/')
    with db.connect() as c:
        row = c.execute("SELECT name,description FROM projects WHERE name='New Project'").fetchone()
    assert row and row['description'] == 'Demo'


def test_dependency_can_be_removed_and_task_becomes_ready(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    dep = app.state.dependencies
    dep.add_dependency(b, a)
    assert dep.readiness(b).effective_state == 'BLOCKED'
    dep.remove_dependency(b, a)
    assert dep.readiness(b).effective_state == 'READY'


def login_as(client, username='d', password='p'):
    r = client.post('/login', data={'username':username,'password':password}, follow_redirects=False)
    assert r.status_code == 303


def test_developer_can_create_task_for_self(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    client = TestClient(app)
    login_as(client)
    r = client.post('/projects/1/tasks', data={
        'title':'New developer task', 'description':'demo', 'task_type':'IMPLEMENTATION',
        'priority':'HIGH', 'assignee_id':'', 'due_date':'2026-09-20', 'reminder_at':'2026-09-19T09:00'
    }, follow_redirects=False)
    assert r.status_code == 303
    with app.state.database.connect() as db:
        row = db.execute("SELECT assignee_id,due_date,reminder_at FROM tasks WHERE title='New developer task'").fetchone()
    assert row and row['assignee_id'] == uid and row['due_date'] == '2026-09-20' and row['reminder_at'] == '2026-09-19T09:00'


def test_task_delete_removes_task_and_dependency_edges(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    app.state.dependencies.add_dependency(b, a)
    app.state.tasks.delete_task(a)
    assert app.state.tasks.task(a) is None
    assert app.state.dependencies.prerequisite_ids(b) == []


def test_due_date_sorting(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    db = app.state.database
    with db.connect() as conn:
        conn.execute("UPDATE tasks SET due_date='2026-09-30' WHERE id=?", (a,))
        conn.execute("UPDATE tasks SET due_date='2026-09-15' WHERE id=?", (b,))
        conn.execute("UPDATE tasks SET due_date='2026-09-20' WHERE id=?", (c,))
    ordered = app.state.tasks.project_tasks(1, sort_by='due')
    assert [x['id'] for x in ordered] == [b, c, a]


def test_calendar_page_renders_scheduled_task(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    with app.state.database.connect() as conn:
        conn.execute("UPDATE tasks SET due_date='2026-09-20' WHERE id=?", (a,))
    client = TestClient(app)
    login_as(client)
    r = client.get('/calendar?year=2026&month=9')
    assert r.status_code == 200
    assert '>01<' in r.text and 'A' in r.text and 'September 2026' in r.text and 'DEV-' not in r.text


def test_calendar_can_create_task_with_clicked_due_date(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    client = TestClient(app)
    login_as(client)
    r = client.post('/calendar/tasks', data={
        'project_id':'1', 'title':'Calendar-created task', 'description':'from calendar',
        'task_type':'IMPLEMENTATION', 'priority':'MEDIUM', 'assignee_id':'',
        'due_date':'2026-09-24', 'reminder_at':'2026-09-24T09:00',
        'calendar_year':'2026', 'calendar_month':'9'
    }, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers['location'].startswith('/calendar?year=2026&month=9')
    with app.state.database.connect() as db:
        row = db.execute("SELECT assignee_id,due_date,reminder_at FROM tasks WHERE title='Calendar-created task'").fetchone()
    assert row and row['assignee_id'] == uid
    assert row['due_date'] == '2026-09-24'
    assert row['reminder_at'] == '2026-09-24T09:00'


def test_calendar_can_schedule_reminder_for_existing_task(tmp_path):
    app, uid, a, b, c = make_app(tmp_path)
    client = TestClient(app)
    login_as(client)
    r = client.post('/calendar/reminders', data={
        'task_id': str(a), 'reminder_at':'2026-09-25T14:30',
        'calendar_year':'2026', 'calendar_month':'9'
    }, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers['location'].startswith('/calendar?year=2026&month=9')
    assert app.state.tasks.task(a)['reminder_at'] == '2026-09-25T14:30'


def test_github_issue_and_pull_urls_are_parsed(tmp_path):
    app, *_ = make_app(tmp_path)
    gh = app.state.github
    issue = gh.parse_url('https://github.com/acme/widgets/issues/17')
    assert issue.kind == 'ISSUE' and issue.repository == 'acme/widgets' and issue.number == 17
    pr = gh.parse_url('https://github.com/acme/widgets/pull/42')
    assert pr.kind == 'PULL_REQUEST' and pr.repository == 'acme/widgets' and pr.number == 42
    with pytest.raises(ValueError):
        gh.parse_url('https://example.com/acme/widgets/issues/17')


def test_task_can_be_linked_and_unlinked_from_github(tmp_path):
    app, uid, a, *_ = make_app(tmp_path)
    gh = app.state.github
    gh.link_task(a, 'https://github.com/acme/widgets/issues/17')
    task = app.state.tasks.task(a)
    assert task['github_kind'] == 'ISSUE'
    assert task['github_repo'] == 'acme/widgets'
    assert task['github_number'] == 17
    assert task['github_state'] == 'NOT_SYNCED'
    gh.unlink_task(a)
    assert app.state.tasks.task(a)['github_url'] is None


def test_merged_pull_request_can_complete_task_and_unlock_dependents(tmp_path, monkeypatch):
    app, uid, a, b, _ = make_app(tmp_path)
    gh = app.state.github
    dep = app.state.dependencies
    dep.add_dependency(b, a)
    gh.link_task(a, 'https://github.com/acme/widgets/pull/42', auto_complete=True)
    monkeypatch.setattr(gh, '_fetch_json', lambda url: {
        'title': 'Implement authentication', 'state': 'closed', 'merged': True,
        'merged_at': '2026-09-11T10:00:00Z'
    })
    result = gh.sync_task(a)
    assert result['state'] == 'MERGED' and result['auto_completed'] is True
    assert app.state.tasks.task(a)['progress_status'] == 'DONE'
    assert dep.readiness(b).effective_state == 'READY'


def test_closed_issue_sync_does_not_auto_complete_task(tmp_path, monkeypatch):
    app, uid, a, *_ = make_app(tmp_path)
    gh = app.state.github
    gh.link_task(a, 'https://github.com/acme/widgets/issues/17', auto_complete=True)
    monkeypatch.setattr(gh, '_fetch_json', lambda url: {'title': 'Bug report', 'state': 'closed'})
    result = gh.sync_task(a)
    assert result['state'] == 'CLOSED'
    assert result['auto_completed'] is False
    assert app.state.tasks.task(a)['progress_status'] == 'PLANNED'



def test_task_can_be_edited(tmp_path):
    app, uid, a, *_ = make_app(tmp_path)
    app.state.tasks.update_task(
        a,
        'Edited task',
        'Updated description',
        'REQUIREMENTS',
        'LOW',
        uid,
        due_date='2026-09-30',
        reminder_at='2026-09-29T09:00',
    )
    task = app.state.tasks.task(a)
    assert task['title'] == 'Edited task'
    assert task['task_type'] == 'REQUIREMENTS'
    assert task['priority'] == 'LOW'
    assert task['due_date'] == '2026-09-30'
    assert task['reminder_at'] == '2026-09-29T09:00'


def test_duplicate_and_cross_project_dependencies_are_rejected(tmp_path):
    app, uid, a, b, _ = make_app(tmp_path)
    dep = app.state.dependencies
    dep.add_dependency(b, a)
    with pytest.raises(DependencyError, match='already exists'):
        dep.add_dependency(b, a)

    with app.state.database.connect() as conn:
        other_project = conn.execute(
            "INSERT INTO projects(name,description) VALUES (?,?)",
            ('Other project', ''),
        ).lastrowid
        other_task = conn.execute(
            """INSERT INTO tasks(project_id,title,task_type,priority,progress_status,assignee_id)
               VALUES (?,?,?,?,?,?)""",
            (other_project, 'Other project task', 'DESIGN', 'MEDIUM', 'PLANNED', uid),
        ).lastrowid
    with pytest.raises(DependencyError, match='within one project'):
        dep.add_dependency(b, other_task)


def test_blocked_task_cannot_be_started(tmp_path):
    app, _, a, b, _ = make_app(tmp_path)
    app.state.dependencies.add_dependency(b, a)
    with pytest.raises(ValueError, match='ready task'):
        app.state.tasks.set_progress_status(b, 'IN_PROGRESS')
    assert app.state.tasks.task(b)['progress_status'] == 'PLANNED'


def test_manual_completion_requires_in_progress_state(tmp_path):
    app, _, a, *_ = make_app(tmp_path)
    with pytest.raises(ValueError, match='in-progress'):
        app.state.tasks.set_progress_status(a, 'DONE')
    app.state.tasks.set_progress_status(a, 'IN_PROGRESS')
    app.state.tasks.set_progress_status(a, 'DONE')
    assert app.state.tasks.task(a)['progress_status'] == 'DONE'


def test_complete_route_rejects_planned_task_then_accepts_started_task(tmp_path):
    app, _, a, *_ = make_app(tmp_path)
    client = TestClient(app)
    login_as(client)

    rejected = client.post(f'/tasks/{a}/complete', follow_redirects=False)
    assert rejected.status_code == 303
    assert 'error=' in rejected.headers['location']
    assert app.state.tasks.task(a)['progress_status'] == 'PLANNED'

    started = client.post(f'/tasks/{a}/start', follow_redirects=False)
    assert started.status_code == 303
    completed = client.post(f'/tasks/{a}/complete', follow_redirects=False)
    assert completed.status_code == 303
    assert app.state.tasks.task(a)['progress_status'] == 'DONE'


def test_closed_unmerged_pull_request_does_not_auto_complete_task(tmp_path, monkeypatch):
    app, _, a, *_ = make_app(tmp_path)
    gh = app.state.github
    gh.link_task(a, 'https://github.com/acme/widgets/pull/42', auto_complete=True)
    monkeypatch.setattr(gh, '_fetch_json', lambda url: {
        'title': 'Work in review',
        'state': 'closed',
        'merged': False,
        'merged_at': None,
    })
    result = gh.sync_task(a)
    assert result['state'] == 'CLOSED'
    assert result['auto_completed'] is False
    assert app.state.tasks.task(a)['progress_status'] == 'PLANNED'


def test_mac_and_windows_launchers_start_same_application_on_default_port():
    project_root = Path(__file__).resolve().parents[1]
    mac_launcher = (project_root / 'Start_HelperDev_macOS.command').read_text()
    windows_launcher = (project_root / 'Start_HelperDev_Windows.bat').read_text()

    assert 'HelperDev.app:app' in mac_launcher
    assert 'HelperDev.app:app' in windows_launcher
    assert '5001' in mac_launcher
    assert '5001' in windows_launcher
    assert 'requirements.txt' in mac_launcher
    assert 'requirements.txt' in windows_launcher

def test_registration_pages_render_account_controls(tmp_path):
    app, *_ = make_app(tmp_path)
    client = TestClient(app)
    login_page = client.get('/login')
    assert login_page.status_code == 200
    assert 'Manage Work Better.' in login_page.text
    assert 'HelperDev helps you manage tasks so that you can focus on development without worrying about organisation.' in login_page.text
    assert 'href="/register"' in login_page.text
    register_page = client.get('/register')
    assert register_page.status_code == 200
    assert 'Create account' in register_page.text
    assert 'Account role: Developer' in register_page.text


def test_new_account_is_created_hashed_and_auto_logged_in(tmp_path):
    app, *_ = make_app(tmp_path)
    client = TestClient(app)
    response = client.post('/register', data={
        'username': 'new.dev',
        'password': 'strongpass123',
        'confirm_password': 'strongpass123',
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'].startswith('/projects?message=Account+created+successfully')
    with app.state.database.connect() as db:
        row = db.execute("SELECT username,password_hash,role FROM users WHERE username='new.dev'").fetchone()
    assert row is not None
    assert row['role'] == 'DEVELOPER'
    assert row['password_hash'] != 'strongpass123'
    assert verify_password('strongpass123', row['password_hash'])
    projects = client.get('/projects')
    assert projects.status_code == 200
    assert 'new.dev' in projects.text


def test_registration_rejects_duplicate_username_and_password_mismatch(tmp_path):
    app, *_ = make_app(tmp_path)
    client = TestClient(app)
    first = client.post('/register', data={
        'username': 'existing-user',
        'password': 'strongpass123',
        'confirm_password': 'strongpass123',
    }, follow_redirects=False)
    assert first.status_code == 303
    client.post('/logout', follow_redirects=False)
    duplicate = client.post('/register', data={
        'username': 'existing-user',
        'password': 'strongpass123',
        'confirm_password': 'strongpass123',
    })
    assert duplicate.status_code == 400
    assert 'already in use' in duplicate.text
    mismatch = client.post('/register', data={
        'username': 'different-user',
        'password': 'strongpass123',
        'confirm_password': 'different-pass123',
    })
    assert mismatch.status_code == 400
    assert 'Passwords do not match' in mismatch.text


def test_self_registration_cannot_create_privileged_role(tmp_path):
    app, *_ = make_app(tmp_path)
    client = TestClient(app)
    response = client.post('/register', data={
        'username': 'attempt-admin',
        'password': 'strongpass123',
        'confirm_password': 'strongpass123',
        'role': 'ADMIN',
    }, follow_redirects=False)
    assert response.status_code == 303
    with app.state.database.connect() as db:
        row = db.execute("SELECT role FROM users WHERE username='attempt-admin'").fetchone()
    assert row and row['role'] == 'DEVELOPER'



def make_rbac_app(tmp_path):
    app = create_app(str(tmp_path / "rbac.db"), seed=False)
    db = app.state.database
    with db.connect() as conn:
        dev_id = conn.execute(
            "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
            ("devuser", hash_password("devpass123"), "DEVELOPER"),
        ).lastrowid
        other_id = conn.execute(
            "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
            ("otherdev", hash_password("otherpass123"), "DEVELOPER"),
        ).lastrowid
        pm_id = conn.execute(
            "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
            ("manager", hash_password("managerpass123"), "PROJECT_MANAGER"),
        ).lastrowid
        admin_id = conn.execute(
            "INSERT INTO users(username,password_hash,role) VALUES (?,?,?)",
            ("administrator", hash_password("adminpass123"), "ADMIN"),
        ).lastrowid
        project_id = conn.execute(
            "INSERT INTO projects(name,description) VALUES (?,?)",
            ("RBAC Project", "Role test project"),
        ).lastrowid
        own_task = conn.execute(
            """INSERT INTO tasks(project_id,title,task_type,priority,progress_status,assignee_id)
               VALUES (?,?,?,?,?,?)""",
            (project_id, "Developer task", "IMPLEMENTATION", "HIGH", "PLANNED", dev_id),
        ).lastrowid
        other_task = conn.execute(
            """INSERT INTO tasks(project_id,title,task_type,priority,progress_status,assignee_id)
               VALUES (?,?,?,?,?,?)""",
            (project_id, "Other task", "TESTING", "MEDIUM", "PLANNED", other_id),
        ).lastrowid
    return app, {
        "dev": dev_id,
        "other": other_id,
        "pm": pm_id,
        "admin": admin_id,
        "project": project_id,
        "own_task": own_task,
        "other_task": other_task,
    }


def test_admin_user_management_page_is_visible_only_to_admin(tmp_path):
    app, ids = make_rbac_app(tmp_path)

    admin_client = TestClient(app)
    login_as(admin_client, "administrator", "adminpass123")
    page = admin_client.get("/admin/users")
    assert page.status_code == 200
    assert "User Management" in page.text
    assert "devuser" in page.text and "manager" in page.text
    assert 'href="/admin/users"' in admin_client.get("/projects").text

    pm_client = TestClient(app)
    login_as(pm_client, "manager", "managerpass123")
    denied = pm_client.get("/admin/users")
    assert denied.status_code == 403
    assert 'href="/admin/users"' not in pm_client.get("/projects").text

    dev_client = TestClient(app)
    login_as(dev_client, "devuser", "devpass123")
    denied = dev_client.get("/admin/users")
    assert denied.status_code == 403
    assert 'href="/admin/users"' not in dev_client.get("/projects").text


def test_non_admin_cannot_change_roles_by_forging_post(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "manager", "managerpass123")
    response = client.post(
        f"/admin/users/{ids['dev']}/role",
        data={"role": "ADMIN"},
        follow_redirects=False,
    )
    assert response.status_code == 403
    with app.state.database.connect() as conn:
        role = conn.execute("SELECT role FROM users WHERE id=?", (ids["dev"],)).fetchone()[0]
    assert role == "DEVELOPER"


def test_admin_can_promote_and_demote_users(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "administrator", "adminpass123")

    promoted = client.post(
        f"/admin/users/{ids['dev']}/role",
        data={"role": "PROJECT_MANAGER"},
        follow_redirects=False,
    )
    assert promoted.status_code == 303
    with app.state.database.connect() as conn:
        assert conn.execute("SELECT role FROM users WHERE id=?", (ids["dev"],)).fetchone()[0] == "PROJECT_MANAGER"

    demoted = client.post(
        f"/admin/users/{ids['dev']}/role",
        data={"role": "DEVELOPER"},
        follow_redirects=False,
    )
    assert demoted.status_code == 303
    with app.state.database.connect() as conn:
        assert conn.execute("SELECT role FROM users WHERE id=?", (ids["dev"],)).fetchone()[0] == "DEVELOPER"


def test_last_administrator_cannot_be_demoted(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "administrator", "adminpass123")
    response = client.post(
        f"/admin/users/{ids['admin']}/role",
        data={"role": "DEVELOPER"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/users?error=")
    with app.state.database.connect() as conn:
        role = conn.execute("SELECT role FROM users WHERE id=?", (ids["admin"],)).fetchone()[0]
    assert role == "ADMIN"


def test_administrator_can_demote_self_when_another_admin_exists(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    with app.state.database.connect() as conn:
        conn.execute("UPDATE users SET role='ADMIN' WHERE id=?", (ids["pm"],))
    client = TestClient(app)
    login_as(client, "administrator", "adminpass123")
    response = client.post(
        f"/admin/users/{ids['admin']}/role",
        data={"role": "DEVELOPER"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/projects?message=")
    with app.state.database.connect() as conn:
        role = conn.execute("SELECT role FROM users WHERE id=?", (ids["admin"],)).fetchone()[0]
    assert role == "DEVELOPER"
    assert client.get("/admin/users").status_code == 403


def test_developer_cannot_assign_new_task_to_another_user(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "devuser", "devpass123")
    response = client.post(
        f"/projects/{ids['project']}/tasks",
        data={
            "title": "Forged assignment",
            "description": "attempt",
            "task_type": "IMPLEMENTATION",
            "priority": "HIGH",
            "assignee_id": str(ids["other"]),
            "due_date": "",
            "reminder_at": "",
            "github_url": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    with app.state.database.connect() as conn:
        row = conn.execute("SELECT assignee_id FROM tasks WHERE title='Forged assignment'").fetchone()
    assert row and row["assignee_id"] == ids["dev"]


def test_developer_cannot_modify_another_users_task(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "devuser", "devpass123")
    response = client.post(
        f"/tasks/{ids['other_task']}/delete",
        follow_redirects=False,
    )
    assert response.status_code == 303
    with app.state.database.connect() as conn:
        assert conn.execute("SELECT 1 FROM tasks WHERE id=?", (ids["other_task"],)).fetchone() is not None


def test_project_manager_can_assign_and_modify_any_task(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "manager", "managerpass123")

    create = client.post(
        f"/projects/{ids['project']}/tasks",
        data={
            "title": "Manager assigned task",
            "description": "assigned to other developer",
            "task_type": "DESIGN",
            "priority": "MEDIUM",
            "assignee_id": str(ids["other"]),
            "due_date": "",
            "reminder_at": "",
            "github_url": "",
        },
        follow_redirects=False,
    )
    assert create.status_code == 303
    with app.state.database.connect() as conn:
        assigned = conn.execute("SELECT assignee_id FROM tasks WHERE title='Manager assigned task'").fetchone()[0]
    assert assigned == ids["other"]

    delete = client.post(f"/tasks/{ids['own_task']}/delete", follow_redirects=False)
    assert delete.status_code == 303
    with app.state.database.connect() as conn:
        assert conn.execute("SELECT 1 FROM tasks WHERE id=?", (ids["own_task"],)).fetchone() is None


def test_ready_queue_remains_personal_for_privileged_roles(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "manager", "managerpass123")
    page = client.get("/ready")
    assert page.status_code == 200
    # Neither seeded RBAC test task is assigned to the manager.
    assert "Developer task" not in page.text
    assert "Other task" not in page.text


def test_admin_role_change_rejects_unknown_role(tmp_path):
    app, ids = make_rbac_app(tmp_path)
    client = TestClient(app)
    login_as(client, "administrator", "adminpass123")
    response = client.post(
        f"/admin/users/{ids['dev']}/role",
        data={"role": "SUPERUSER"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    with app.state.database.connect() as conn:
        role = conn.execute("SELECT role FROM users WHERE id=?", (ids["dev"],)).fetchone()[0]
    assert role == "DEVELOPER"


def test_login_page_lists_all_demo_role_credentials(tmp_path):
    app, *_ = make_app(tmp_path)
    client = TestClient(app)
    page = client.get('/login')
    assert page.status_code == 200
    assert 'Demo accounts' in page.text
    assert 'Developer' in page.text and 'Username:' in page.text and 'dev123' in page.text
    assert 'Project Manager' in page.text and 'pm123' in page.text
    assert 'Administrator' in page.text and 'admin123' in page.text


def test_switch_account_control_clears_session_and_returns_to_login(tmp_path):
    app, *_ = make_app(tmp_path)
    client = TestClient(app)
    login_as(client)
    projects = client.get('/projects')
    assert projects.status_code == 200
    assert 'Switch Account' in projects.text

    switched = client.post('/switch-account', follow_redirects=False)
    assert switched.status_code == 303
    assert switched.headers['location'] == '/login'

    protected = client.get('/projects', follow_redirects=False)
    assert protected.status_code == 303
    assert protected.headers['location'] == '/login'
