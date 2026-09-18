# HelperDev — Features and User Guide

HelperDev is a developer-focused task-management application designed to make dependencies explicit, distinguish actionable work from blocked work, and keep task information in one local workspace.

The login page presents the application with the message:

> **Manage Work Better.**
>
> HelperDev helps you manage tasks so that you can focus on development without worrying about organisation.

This guide explains what HelperDev currently does and how to use each feature.

---

# 1. Accounts, login, and roles

## 1.1 Demo accounts

HelperDev includes three demonstration accounts:

```text
Developer:       dev / dev123
Project Manager: pm / pm123
Administrator:   admin / admin123
```

## 1.2 Creating your own account

From the login page:

1. Click **Create a new account**.
2. Enter a username containing 3-32 characters.
3. Use letters, numbers, dots, underscores, or hyphens in the username. Spaces are not allowed (for example, use `new_user` rather than `New user`).
4. Enter a password containing at least 8 characters.
5. Enter the same password again in **Confirm password**.
6. Click **Create account**.

After successful registration, HelperDev signs the new user in automatically.

Self-service registration always creates the role:

```text
DEVELOPER
```

The registration form intentionally cannot create `PROJECT_MANAGER` or `ADMIN` privileges.

## 1.3 Password storage

Passwords are not stored in plain text. HelperDev hashes passwords with scrypt and a random salt before storing the result in `HelperDev.db`.

## 1.4 Logging out and switching accounts

Click **Sign out** in the top-right area.

Logging out clears the browser session but does not delete projects or tasks. All accounts use the same local SQLite database, so when another user logs in, the underlying project data is still present. Permissions and personal views can differ by account.

## 1.5 Current role behavior

**Developer**

- Can sign in and create projects.
- Can create tasks, but the server always assigns a Developer-created task to that Developer.
- Can edit/delete/start/complete only their own assigned tasks.
- Can manage dependencies, reminders, and GitHub links only for their own tasks.
- Has a personal Ready-to-Work queue.
- Cannot access User Management or change roles.

**Project Manager**

- Can assign tasks to any registered user.
- Can modify, start, complete, delete, schedule, and manage dependencies/GitHub links for any task.
- Has a personal Ready-to-Work queue containing only tasks assigned to that Project Manager.
- Cannot access User Management or change roles.

**Administrator**

- Has the same task-level permissions as Project Manager.
- Can open **User Management** and change users between DEVELOPER, PROJECT_MANAGER, and ADMIN.
- Cannot demote the final remaining Administrator account.
- Self-service registration still cannot create an Administrator account.

---

# 2. Projects

The **Projects** screen is the main workspace list.

## Create a project

1. Sign in.
2. Scroll to **Create project**.
3. Enter a project name.
4. Optionally enter a short description.
5. Click **Create project**.

The project is stored in `HelperDev.db` and remains available after logout or application restart.

## Open a project

Click a project card to open its task board.

---

# 3. Task board

Each project has four visual lanes:

```text
READY | BLOCKED | IN PROGRESS | DONE
```

The lane is based on the task's stored progress state together with dependency readiness.

- **READY** — a planned task whose active prerequisites are all complete.
- **BLOCKED** — a planned task with at least one unfinished prerequisite.
- **IN PROGRESS** — a task that has been started.
- **DONE** — a completed task.

The board also displays summary counts for the four states.

## Lane navigation

Each lane has up/down controls for navigating its task cards when the lane contains more items than are visible. The mouse wheel scrolls the main page rather than independently trapping the user inside a lane.

A floating back-to-top button appears after the page has been scrolled down.

---

# 4. Creating tasks

Inside a project, click the **Create Task** shortcut or scroll to the **Create task** form.

A task can contain:

- title;
- description;
- task type;
- priority;
- assignee;
- due date;
- reminder time;
- optional GitHub Issue/Pull Request URL;
- optional PR-merge auto-completion setting.

Current task types are:

```text
REQUIREMENTS
DESIGN
IMPLEMENTATION
BUG_FIX
TESTING
REVIEW
DOCUMENTATION
DEPLOYMENT
```

Priorities are:

```text
HIGH
MEDIUM
LOW
```

## Assignment rules

When a **Developer** creates a task, HelperDev assigns it to that Developer on the server side.

A **Project Manager** or **Administrator** can choose another user or leave a task unassigned.

---

# 5. Editing and deleting tasks

For a task you are authorized to modify, use the buttons on its card.

**Edit** opens the task-edit screen, where supported task metadata can be changed.

**Delete** permanently removes the task after confirmation. Dependency edges involving the deleted task are also removed by the database relationship rules.

A normal Developer can modify their own assigned tasks. Project Manager and Administrator roles have broader task-level access.

---

# 6. Dependency management

Dependencies are one of HelperDev's central features.

If Task B requires Task A first, define:

```text
Task B depends on Task A
```

Until Task A is complete, Task B appears as **BLOCKED**.

When Task A becomes **DONE**, HelperDev recalculates Task B. If no other unfinished prerequisites remain, Task B becomes **READY**.

## Add a dependency

1. Open the project.
2. Click **Add Dependency** or scroll to the dependency form.
3. Select the dependent task.
4. Select the prerequisite task.
5. Click **Add dependency**.

## Dependency validation

HelperDev rejects invalid dependency relationships such as:

- a task depending on itself;
- duplicate dependency edges;
- dependencies between tasks from different projects;
- circular dependency chains.

## Remove a dependency

Use **Remove** next to the prerequisite shown on an authorized task card.

---

# 7. Starting and completing work

A planned task can be started only when it is **READY**.

## Start a task

Click **Start task** on a Ready task. It moves to **IN PROGRESS**.

HelperDev prevents a **BLOCKED** task from being started through the normal server-side operation.

## Complete a task

Click **Complete** on an In Progress task. The task becomes **DONE**.

After completion, dependent tasks are recalculated automatically. Some previously blocked tasks may immediately become Ready.

---

# 8. Ready-to-Work queue

Open **Ready to Work** from the top navigation or the project shortcut.

This view is personal to the signed-in user. It lists active planned tasks assigned to that user that are currently actionable according to their dependencies.

This is useful when the project board contains many tasks but you want to know which work can actually be started now.

---

# 9. Sorting tasks

On a project board, tasks can be sorted by:

- priority;
- due date;
- title;
- creation time.

You can choose ascending or descending direction and click **Apply**.

---

# 10. Calendar

Open **Calendar** from the top navigation.

The calendar provides a monthly view of scheduled tasks.

You can:

- move between months;
- see tasks on their due dates;
- click a date and create a task for that date;
- schedule an in-app reminder for an existing task.

When a Developer creates a task through the calendar, it is assigned to that Developer. Managers can choose other assignees.

---

# 11. Reminders

HelperDev supports **in-app reminders**.

A reminder time can be set while creating/editing a task or from the Calendar.

When the reminder becomes due, HelperDev can surface it inside the application.

Current limitation: HelperDev does not run a background notification service when the application is closed. It does not currently send email, system notifications, or mobile push notifications.

---

# 12. GitHub Issue and Pull Request integration

A HelperDev task can be linked to a GitHub URL in one of these forms:

```text
https://github.com/OWNER/REPOSITORY/issues/NUMBER
https://github.com/OWNER/REPOSITORY/pull/NUMBER
```

## Link GitHub while creating/editing a task

Paste the Issue or Pull Request URL into the GitHub field.

HelperDev stores parsed link metadata with the task.

## Manual synchronization

For a linked task, click **Sync GitHub**.

HelperDev retrieves the current state from GitHub and caches information such as the title/state and synchronization time.

## Pull Request auto-completion

For a Pull Request link, you can enable:

**Automatically mark this HelperDev task Done when a linked pull request is merged.**

This behavior is triggered during a manual GitHub synchronization. If the linked PR is reported as merged and the option is enabled, HelperDev marks the task Done. That can also unlock dependent tasks.

Closing a linked GitHub Issue does **not** automatically complete the HelperDev task.

## Private repositories and API limits

You can supply a GitHub token using the `GITHUB_TOKEN` environment variable. The token is read from the process environment and is not stored in SQLite.

See `README_INSTALLATION.md` for the macOS and Windows commands.

---

# 13. Data storage and persistence

HelperDev uses SQLite. The database file is:

```text
HelperDev.db
```

The database is local to the HelperDev folder.

Closing the browser, logging out, or stopping the server does not erase the database. When HelperDev starts again, it reopens the same file.

The database contains tables for:

- users;
- projects;
- tasks;
- task dependencies.

Task records also contain scheduling, reminder, and GitHub-integration fields.

## Backup

To back up your work:

1. Stop HelperDev.
2. Copy `HelperDev.db` to another safe location.

## Important

Deleting the `tests` folder does not remove your tasks and does not normally prevent the app from running.

Deleting `HelperDev.db` removes the saved database state unless you have a backup.

---

# 14. Cross-platform use

The same HelperDev source code is designed to run on macOS and Windows.

The application uses:

- Python;
- FastAPI;
- Jinja2;
- SQLite;
- standard cross-platform filesystem paths.

Do not move a `.venv` from macOS to Windows or from Windows to macOS. Each operating system should create its own virtual environment. The SQLite `HelperDev.db` file can be copied between the systems.

---

# 15. Automated verification

The package includes automated tests in:

```text
tests/test_HelperDev.py
```

The HelperDev package contains **40 automated tests** covering task and dependency rules, calendar and reminder behaviour, GitHub Issue/Pull Request integration with mocked API responses, authentication and role-based access control, account registration and role administration, account switching, and launcher consistency.

See `README_INSTALLATION.md` for the commands to run them.

---

# 16. Current prototype boundaries

HelperDev is a university software-engineering prototype rather than a production-hosted SaaS platform. Current boundaries include:

- local SQLite storage;
- signed browser sessions;
- no password-reset workflow;
- no email verification;
- no background reminder worker;
- no webhooks or continuous GitHub polling;
- no repository hosting;
- no CI/CD execution;
- no public production HTTPS configuration in the local package;
- self-service registration creates Developer accounts only.

These boundaries do not prevent the implemented local workflow from functioning, but they should be considered before any production deployment.


---

# 17. Role-based access control and User Management

HelperDev provides DEVELOPER, PROJECT_MANAGER, and ADMIN roles as a complete user-facing authorization workflow.

## Developer

A Developer can create tasks for themselves and can edit, delete, start, complete, add/remove dependencies, schedule reminders, and manage GitHub links only for tasks assigned to them. If a Developer submits another user's id as the assignee during task creation, the server replaces it with the authenticated Developer's own id.

## Project Manager

A Project Manager can create tasks for any assignee and can manage any task. A Project Manager cannot access User Management and cannot change roles.

## Administrator

An Administrator has the same task-level permissions as a Project Manager plus access to **User Management**.

To change a role:

1. Sign in with an Administrator account.
2. Select **User Management** in the top navigation.
3. Find the required username.
4. Select DEVELOPER, PROJECT_MANAGER, or ADMIN.
5. Select **Update**.
6. The new role takes effect on the user's next request because HelperDev reads the current role from SQLite for each authenticated request.

The final remaining Administrator cannot be demoted. To demote that account, first promote another account to Administrator.

## Ready-to-Work is always personal

Project Manager and Administrator task-management privileges do not make the Ready-to-Work queue global. Every role sees only READY tasks assigned to the currently authenticated user.


# 17. Demo roles and switching accounts

The login page lists all three built-in demonstration accounts so each role can be tested directly:

- Developer: `dev` / `dev123`
- Project Manager: `pm` / `pm123`
- Administrator: `admin` / `admin123`

When signed in, **Switch Account** securely clears the current signed-in session and returns to the main login page. Use it when you want to move immediately from one demonstration role to another. **Sign out** remains available and performs the same secure session-clearing action.
