@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    ) else (
        where py >nul 2>nul
        if %errorlevel%==0 (
            set "PYTHON_CMD=py -3"
        ) else (
            echo Python was not found.
            echo Create the virtual environment or install Python, then try again.
            exit /b 1
        )
    )
)

echo Starting Talksy backend and frontend...
%PYTHON_CMD% dev.py
set "EXIT_CODE=%errorlevel%"

endlocal & exit /b %EXIT_CODE%
