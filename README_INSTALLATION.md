# HelperDev — Installation and Running Guide

This guide explains how to install and run HelperDev on **macOS** and **Windows**. HelperDev is a local Python/FastAPI web application. It runs on your computer and opens in a normal web browser at `http://127.0.0.1:5001`.

HelperDev stores its normal application data locally in the SQLite database file `HelperDev.db`. It does not require MySQL, PostgreSQL, Docker, or a separate database server.

## Default local address and optional port override

HelperDev starts on **`http://127.0.0.1:5001`** by default. This is only the local listening port; changing it does not change HelperDev routes, permissions, data, or features.

On macOS, if you specifically want port **5173** for a run, start the launcher from Terminal with:

```bash
HELPERDEV_PORT=5173 ./Start_HelperDev_macOS.command
```

Then open either `http://127.0.0.1:5173` or `http://localhost:5173`. When `HELPERDEV_PORT` is not set, the launcher returns to the default port **5001**.

On Windows Command Prompt, an equivalent temporary override is:

```bat
set HELPERDEV_PORT=5173
Start_HelperDev_Windows.bat
```


## 1. What you need

Before starting, you need:

- macOS or Windows.
- Python 3.10 or newer. Python 3.11–3.13 are suitable choices.
- A modern web browser such as Safari, Chrome, Edge, or Firefox.
- Internet access during the first setup so Python can download the packages listed in `requirements.txt`.
- Internet access later only if you use the optional GitHub synchronization feature.

The HelperDev ZIP already contains the application source code, templates, styles, startup scripts, tests, and the SQLite database.

## 2. Important files in the package

```text
HelperDev/
├── README.md
├── README_INSTALLATION.md
├── README_USER_GUIDE.md
├── requirements.txt
├── Start_HelperDev_macOS.command
├── Start_HelperDev_Windows.bat
├── HelperDev.db
├── HelperDev/
│   ├── app.py
│   ├── db.py
│   ├── security.py
│   ├── seed.py
│   ├── services/
│   ├── templates/
│   └── static/
└── tests/
```

`HelperDev.db` contains saved users, projects, tasks, dependencies, reminders, and stored GitHub-link metadata. Do not delete it if you want to keep your data.

---

# Part A — macOS installation

## A1. Check whether Python is installed

Open **Terminal** and run:

```bash
python3 --version
```

If you see a Python 3 version, for example:

```text
Python 3.12.8
```

continue to the next section.

If `python3` is not found, install a current Python 3 release. After installing Python, close Terminal, open it again, and repeat:

```bash
python3 --version
```

## A2. Extract HelperDev

1. Locate `HelperDev.zip` in Finder.
2. Double-click the ZIP to extract it.
3. Keep the extracted HelperDev folder somewhere writable, for example your Documents folder.
4. Do not run the application from inside the ZIP archive.

## A3. Easiest macOS method — use the launcher

Inside the extracted folder, locate:

```text
Start_HelperDev_macOS.command
```

Double-click it.

On the first run, the launcher will:

1. Change into the HelperDev directory.
2. Create a private Python virtual environment named `.venv` if it does not exist.
3. Install the dependencies from `requirements.txt` if necessary.
4. Start HelperDev on:

```text
http://127.0.0.1:5001
```

Open that address in your browser.

### If macOS refuses to open the `.command` file

Try either of these methods.

**Method 1 — Finder:**

1. Right-click `Start_HelperDev_macOS.command`.
2. Choose **Open**.
3. Confirm that you want to open it.

**Method 2 — Terminal:**

Open Terminal, drag the HelperDev folder into Terminal after typing `cd `, or navigate to it manually. Then run:

```bash
chmod +x Start_HelperDev_macOS.command
./Start_HelperDev_macOS.command
```

## A4. Manual macOS installation

If you prefer to set up HelperDev yourself, open Terminal and change into the extracted folder:

```bash
cd "/path/to/HelperDev"
```

Create the virtual environment:

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

Install HelperDev dependencies:

```bash
python -m pip install -r requirements.txt
```

Start HelperDev:

```bash
python -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001
```

Open:

```text
http://127.0.0.1:5001
```

## A5. Running HelperDev again later on macOS

The easiest method is simply to double-click:

```text
Start_HelperDev_macOS.command
```

The launcher reuses the existing `.venv`; it does not need to reinstall everything on every run.

To start manually:

```bash
cd "/path/to/HelperDev"
source .venv/bin/activate
python -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001
```

## A6. Stopping HelperDev on macOS

Return to the Terminal window in which HelperDev is running and press:

```text
Control + C
```

Closing the browser alone does not stop the HelperDev server.

---

# Part B — Windows installation

## B1. Check whether Python is installed

Open **Command Prompt** or **PowerShell** and try:

```powershell
py -3 --version
```

If that command is unavailable, try:

```powershell
python --version
```

If you see a Python 3 version, continue.

If Windows cannot find Python, install Python 3. During installation, enabling the option that adds Python to PATH is useful. After installation, close and reopen Command Prompt or PowerShell and check the version again.

## B2. Extract HelperDev

1. Right-click `HelperDev.zip`.
2. Choose **Extract All**.
3. Select a writable destination such as Documents.
4. Open the extracted folder.
5. Do not run the application directly from the ZIP preview.

## B3. Easiest Windows method — use the launcher

Double-click:

```text
Start_HelperDev_Windows.bat
```

On the first run, the launcher will:

1. Create `.venv`.
2. Install packages from `requirements.txt` if necessary.
3. Start HelperDev at:

```text
http://127.0.0.1:5001
```

Open that address in your browser.

### Windows SmartScreen warning

Windows may warn about a downloaded `.bat` file because the file is not digitally signed. The batch file is plain text and can be inspected in Notepad. If you trust the HelperDev package, choose the option that allows you to run it.

## B4. Manual Windows installation — PowerShell

Open PowerShell and navigate to the extracted folder:

```powershell
cd "C:\path\to\HelperDev"
```

Create the virtual environment:

```powershell
py -3 -m venv .venv
```

If the `py` command is not available, use:

```powershell
python -m venv .venv
```

You do not have to activate the virtual environment. The following commands call its Python executable directly, which also avoids PowerShell execution-policy problems:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001
```

Open:

```text
http://127.0.0.1:5001
```

## B5. Manual Windows installation — Command Prompt

Open Command Prompt and navigate to the extracted directory:

```bat
cd /d "C:\path\to\HelperDev"
```

Create the virtual environment:

```bat
python -m venv .venv
```

Install the dependencies:

```bat
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start HelperDev:

```bat
.venv\Scripts\python.exe -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5001
```

Open:

```text
http://127.0.0.1:5001
```

## B6. Running HelperDev again later on Windows

The easiest method is:

```text
Start_HelperDev_Windows.bat
```

The existing `.venv` is reused.

## B7. Stopping HelperDev on Windows

Return to the Command Prompt/PowerShell window running HelperDev and press:

```text
Ctrl + C
```

If Windows asks whether to terminate the batch job, answer `Y` if necessary.

---

# Part C — First login and creating an account

HelperDev includes three demonstration accounts:

```text
Developer:       dev / dev123
Project Manager: pm / pm123
Administrator:   admin / admin123
```

You can also create a new account from the login page:

1. Open `http://127.0.0.1:5001`.
2. Click **Create a new account**.
3. Enter a username.
4. Enter a password of at least 8 characters.
5. Confirm the password.
6. Click **Create account**.

For security, public/self-service account creation always creates a **Developer** account. The registration form cannot grant itself Project Manager or Administrator privileges.

The password is not stored as plain text. HelperDev stores a salted scrypt password hash in the local `users` table in `HelperDev.db`.

## C1. Role-based access control

The three roles have different application permissions:

- **Developer** — creates tasks for themselves and can modify only tasks assigned to them.
- **Project Manager** — can assign tasks to users and manage any task, but cannot change user roles.
- **Administrator** — has Project Manager task permissions and can also open **User Management** to change user roles.

Only an Administrator can access `/admin/users`. Public registration never lets a user select a privileged role. HelperDev also refuses to demote the final remaining Administrator.


---

# Part D — Optional GitHub integration

Public GitHub Issue and Pull Request synchronization may work without a token, subject to GitHub's unauthenticated limits. A token can be supplied through the `GITHUB_TOKEN` environment variable for private repositories or higher API limits.

HelperDev does **not** store the token in `HelperDev.db`.

## macOS

In Terminal:

```bash
export GITHUB_TOKEN='YOUR_TOKEN_HERE'
./Start_HelperDev_macOS.command
```

The variable applies to that Terminal session.

## Windows PowerShell

```powershell
$env:GITHUB_TOKEN="YOUR_TOKEN_HERE"
.\Start_HelperDev_Windows.bat
```

## Windows Command Prompt

```bat
set GITHUB_TOKEN=YOUR_TOKEN_HERE
Start_HelperDev_Windows.bat
```

---

# Part E — Where HelperDev saves data

By default, the SQLite database is:

```text
HelperDev.db
```

It is located in the root HelperDev folder next to `requirements.txt`.

The database stores items such as:

- user accounts and password hashes;
- roles;
- projects;
- tasks;
- assignees;
- priorities and task types;
- progress states;
- due dates and reminder times;
- task dependency relationships;
- GitHub Issue/Pull Request link metadata and the last synchronized state.

Logging out, closing the browser, or stopping HelperDev does not delete this file.

## Backing up your data

1. Stop HelperDev first.
2. Copy `HelperDev.db` to a safe backup location.
3. Keep the backup together with the corresponding HelperDev installation.

## Moving data between macOS and Windows

The SQLite file is portable. To move HelperDev between operating systems:

1. Stop HelperDev.
2. Copy the HelperDev folder or at minimum copy `HelperDev.db` into the new HelperDev folder.
3. Do **not** reuse `.venv` between macOS and Windows.
4. Delete `.venv` on the new system if it came from the other operating system.
5. Run the startup script for the new operating system so a new local `.venv` is created.

---

# Part F — Running the automated tests

The submission includes automated tests in `tests/test_HelperDev.py`.

With the environment installed, run from the project root:

## macOS

```bash
.venv/bin/python -m pytest -q
```

## Windows PowerShell or Command Prompt

```text
.venv\Scripts\python.exe -m pytest -q
```

The package contains **40 automated tests** covering task and dependency rules, calendar and reminder behaviour, GitHub Issue/Pull Request integration with mocked API responses, authentication and role-based access control, account registration and role administration, account switching, and launcher consistency.

The `tests` folder is not required for normal HelperDev operation, but keeping it allows the implementation to be verified.

---

# Part G — Troubleshooting

## `python` or `python3` is not found

Install Python 3 and reopen the terminal. On Windows, try `py -3` if `python` is not recognized.

## Port 5001 is already in use

Another application may already be using the default port. Stop the other process, or start HelperDev on a different local port, for example:

```bash
python -m uvicorn HelperDev.app:app --host 127.0.0.1 --port 5173
```

Then open:

```text
http://127.0.0.1:5173
```

On Windows use `.venv\Scripts\python.exe` instead of `python` if the virtual environment is not activated.

## Packages fail to install

Check that Internet access is available and retry:

```bash
python -m pip install -r requirements.txt
```

## The app opens but saved data is missing

Confirm that you are running HelperDev from the expected folder and that its `HelperDev.db` file is the database you intended to use. A different extracted copy of HelperDev can have a different database file.

## I deleted `.venv`

That does not delete your HelperDev tasks. Run the startup script again; it will recreate `.venv`. Your application data is in `HelperDev.db`, not `.venv`.

## I deleted `HelperDev.db`

That removes the database containing the saved application state. On the next normal startup HelperDev can initialize a new database and demo data, but the deleted data can only be recovered from a backup.
