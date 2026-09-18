# HelperDev

**Manage Work Better.**

HelperDev is a local, cross-platform developer task-management prototype for macOS and Windows. It provides dependency-aware READY/BLOCKED task states, a personal Ready-to-Work queue, calendar scheduling and reminders, GitHub Issue/Pull Request linkage, local SQLite persistence, self-service Developer registration, and server-enforced role-based access control.

## Local server configuration

HelperDev starts locally at **`http://127.0.0.1:5001`** by default. The launchers support an optional `HELPERDEV_PORT` environment variable when another loopback port is required.

## RBAC and account features

- Login page lists all three demo credentials with their roles.
- A **Switch Account** control clears the current session and returns to the login page.
- Administrator-only **User Management** allows role changes between **DEVELOPER**, **PROJECT_MANAGER**, and **ADMIN**.
- Public/self-service registration remains fixed to **DEVELOPER**.
- Project Managers and Administrators can assign and manage any task.
- Developers remain restricted to tasks assigned to themselves.
- Role checks are enforced on the server, not only by hiding UI controls.
- The final Administrator account cannot be demoted.
- The Ready-to-Work queue remains personal for every role.
- The delivered source passes **40/40 automated tests**.

## Demo accounts

```text
Developer:       dev / dev123
Project Manager: pm / pm123
Administrator:   admin / admin123
```

Use the Administrator account to open **User Management** and change roles.

## Quick start on macOS

1. Extract `HelperDev.zip`.
2. Open the extracted folder.
3. Double-click `Start_HelperDev_macOS.command`.
4. Open `http://127.0.0.1:5001` in your browser.

See `README_INSTALLATION.md` for full installation and automated verification instructions, and `README_USER_GUIDE.md` for usage guidance.

## Data

Normal HelperDev data is stored locally in:

```text
HelperDev.db
```

Keep that file if you want to preserve users, roles, projects and tasks.
