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
```

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
```

Double-click `Start_HelperDev_macOS.command` in Finder.

Because the launcher is not distributed through the Mac App Store or signed by an identified Apple developer, macOS may block it the first time it is opened. If this happens, follow these steps:

1. Double-click `Start_HelperDev_macOS.command`.
2. macOS may display a message saying that Apple could not verify that the file is free of malware. Click **Done**.
3. Open **System Settings**.
4. Go to **Privacy & Security**.
5. Scroll down to the **Security** section.
6. Find the message stating that `Start_HelperDev_macOS.command` was blocked to protect your Mac.
7. Click **Open Anyway**.
8. macOS will display another confirmation dialog. Click **Open Anyway** again.
9. Approve the action using an administrator's **Touch ID** or click **Use Password...** and enter an administrator password.
10. The launcher should then be allowed to run.

After the launcher is approved, it automatically:

1. Creates a local Python virtual environment named `.venv`
2. Installs the dependencies from `requirements.txt`
3. Starts HelperDev at `http://127.0.0.1:5001`

If the launcher still does not open, open Terminal in the project folder and run:

```bash
chmod +x Start_HelperDev_macOS.command
./Start_HelperDev_macOS.command
```

#### Manual setup on macOS

Open Terminal and navigate to the project folder:

```bash
cd "/path/to/HelperDev"
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Start HelperDev:

```bash
python -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001
```

Then open:

```text
http://127.0.0.1:5001
```

To stop the application, press:

```text
Control + C
```

---

### Windows

#### Automatic setup

The easiest method is to double-click:

```text
Start_HelperDev_Windows.bat
```

On the first run, the launcher automatically:

1. Creates a local Python virtual environment named `.venv`
2. Installs the dependencies from `requirements.txt`
3. Starts HelperDev at `http://127.0.0.1:5001`

#### Manual setup using PowerShell

Open PowerShell and navigate to the project folder:

```powershell
cd "C:\path\to\HelperDev"
```

Create a virtual environment:

```powershell
py -3 -m venv .venv
```

If `py` is unavailable, use:

```powershell
python -m venv .venv
```

Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start HelperDev:

```powershell
.\.venv\Scripts\python.exe -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001
```

Then open:

```text
http://127.0.0.1:5001
```

To stop the application, press:

```text
Ctrl + C
```

---

### Running HelperDev again later

On macOS, run:

```text
Start_HelperDev_macOS.command
```

On Windows, run:

```text
Start_HelperDev_Windows.bat
```

The existing `.venv` is reused, so the dependencies do not need to be reinstalled every time.

For the complete installation, troubleshooting, GitHub integration, database backup, and test instructions, see [`README_INSTALLATION.md`](README_INSTALLATION.md).


## Data

Normal HelperDev data is stored locally in:

```text
HelperDev.db
```

Keep that file if you want to preserve users, roles, projects and tasks.
