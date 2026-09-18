@echo off
setlocal
cd /d "%~dp0"

if not defined HELPERDEV_HOST set "HELPERDEV_HOST=127.0.0.1"
if not defined HELPERDEV_PORT set "HELPERDEV_PORT=5001"

if not exist ".venv\Scripts\python.exe" (
    echo Setting up HelperDev for the first time...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo Python 3 is required. Install Python 3 and run this file again.
            pause
            exit /b 1
        )
        python -m venv .venv
    )
    if errorlevel 1 (
        echo Failed to create the Python virtual environment.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, jinja2, itsdangerous, multipart" >nul 2>nul
if errorlevel 1 (
    echo Installing HelperDev dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 (
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        pause
        exit /b 1
    )
)

echo Starting HelperDev at http://%HELPERDEV_HOST%:%HELPERDEV_PORT%
echo Press Control+C to stop HelperDev.
".venv\Scripts\python.exe" -m uvicorn HelperDev.app:app --host %HELPERDEV_HOST% --port %HELPERDEV_PORT%

if errorlevel 1 (
    echo.
    echo HelperDev stopped with an error.
    pause
)
endlocal
