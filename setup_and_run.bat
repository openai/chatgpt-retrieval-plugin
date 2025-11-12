@echo off
REM Windows batch file to setup and run the ChatGPT Retrieval Plugin
REM Double-click this file to automatically install and run

echo ============================================================
echo   ChatGPT Retrieval Plugin - Windows Setup
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.10 or 3.11 from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo Checking Python version...
python --version

REM Run the Python setup script
echo.
echo Running automatic setup...
echo.

python setup_and_run.py

if errorlevel 1 (
    echo.
    echo Setup failed. Please check the errors above.
    pause
    exit /b 1
)

pause
