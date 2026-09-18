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

## Installation and Running

HelperDev is a local Python/FastAPI application for macOS and Windows. It runs in a web browser at:

```text
http://127.0.0.1:5001

### Requirements

Before running HelperDev, make sure you have:

- Python 3.10 or newer
- A modern web browser
- Internet access during the first setup so Python can install the packages in `requirements.txt`

---

### macOS

#### Automatic setup

The easiest method is to run:

```text
Start_HelperDev_macOS.command

Double-click the file in Finder.

On the first run, the launcher automatically:

Creates a local Python virtual environment named .venv
Installs the dependencies from requirements.txt
Starts HelperDev at http://127.0.0.1:5001

If macOS refuses to open the launcher, open Terminal in the project folder and run:

chmod +x Start_HelperDev_macOS.command
./Start_HelperDev_macOS.command
Manual setup on macOS

Open Terminal and navigate to the project folder:

cd "/path/to/HelperDev"

Create a virtual environment:

python3 -m venv .venv

Activate it:

source .venv/bin/activate

Upgrade pip:

python -m pip install --upgrade pip

Install the dependencies:

python -m pip install -r requirements.txt

Start HelperDev:

python -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001

Then open:

http://127.0.0.1:5001

To stop the application, press:

Control + C
Windows
Automatic setup

The easiest method is to double-click:

Start_HelperDev_Windows.bat

On the first run, the launcher automatically:

Creates a local Python virtual environment named .venv
Installs the dependencies from requirements.txt
Starts HelperDev at http://127.0.0.1:5001
Manual setup using PowerShell

Open PowerShell and navigate to the project folder:

cd "C:\path\to\HelperDev"

Create a virtual environment:

py -3 -m venv .venv

If py is unavailable, use:

python -m venv .venv

Install the dependencies:

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Start HelperDev:

.\.venv\Scripts\python.exe -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001

Then open:

http://127.0.0.1:5001

To stop the application, press:

Ctrl + C
Running HelperDev again later

On macOS, run:

Start_HelperDev_macOS.command

On Windows, run:

Start_HelperDev_Windows.bat

The existing .venv is reused, so the dependencies do not need to be reinstalled every time.

For the complete installation, troubleshooting, GitHub integration, database backup, and test instructions, see README_INSTALLATION.md.

## Data

Normal HelperDev data is stored locally in:

```text
HelperDev.db
```

Keep that file if you want to preserve users, roles, projects and tasks.
