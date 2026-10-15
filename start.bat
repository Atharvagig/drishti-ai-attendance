@echo off
echo ====================================================
echo Starting Drishti AI - Smart Campus Attendance Platform
echo ====================================================

:: Change to the directory where the batch file is located
cd /d "%~dp0"

:: Check and activate virtual environment (venv314 has native dlib cp314 support)
IF EXIST "venv314\Scripts\activate.bat" (
    echo Activating virtual environment (venv314 - Python 3.14 with dlib)...
    call venv314\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    echo Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
) ELSE IF EXIST ".venv\Scripts\activate.bat" (
    echo Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) ELSE (
    echo Warning: No virtual environment found! Running with global Python.
)

echo.
echo Launching the application...
python run.py

echo.
pause
