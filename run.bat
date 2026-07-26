@echo off
chcp 65001 >nul 2>&1
title Myra AI Assistant (TITAN)
echo =========================================
echo       Starting Myra AI Assistant...
echo =========================================
echo.

REM Navigate to the script's own directory
cd /d "%~dp0"

REM ===== Step 1 & 2: Locate or Create Virtual Environment =====
IF EXIST "venv\Scripts\python.exe" (
    echo [Step 1/3] Virtual environment (venv) detected.
    set PYTHON_CMD=venv\Scripts\python.exe
    set PIP_CMD=venv\Scripts\pip.exe
) ELSE IF EXIST ".venv\Scripts\python.exe" (
    echo [Step 1/3] Virtual environment (.venv) detected.
    set PYTHON_CMD=.venv\Scripts\python.exe
    set PIP_CMD=.venv\Scripts\pip.exe
) ELSE (
    echo [Step 1/3] Creating Python virtual environment (venv)...
    python -m venv venv
    IF ERRORLEVEL 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.11/3.12 is installed and added to PATH.
        echo Download from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    set PYTHON_CMD=venv\Scripts\python.exe
    set PIP_CMD=venv\Scripts\pip.exe
)

REM ===== Step 3: Check if ALL key dependencies are installed =====
echo [Step 2/3] Checking environment dependencies...
"%PYTHON_CMD%" -c "import PyQt6, psutil, structlog, sounddevice, websockets, numpy, scipy, google.genai, mss, PIL, chromadb" >nul 2>&1
IF ERRORLEVEL 1 (
    echo [Step 2/3] Some dependencies are missing. Installing automatically...
    echo           Please wait, this may take a few minutes...
    echo.
    "%PIP_CMD%" install --upgrade pip >nul 2>&1
    "%PIP_CMD%" install -e .[dev]
    IF ERRORLEVEL 1 (
        echo.
        echo ERROR: Failed to install dependencies. Check internet connection or Python version.
        pause
        exit /b 1
    )
    echo Installation complete!
) ELSE (
    echo [Step 2/3] All essential packages are verified and ready.
)

echo.
echo =========================================
echo [Step 3/3] Launching Myra AI Application...
echo =========================================
echo.

REM ===== Run the main application using venv Python executable directly =====
"%PYTHON_CMD%" main.py

REM ===== Error reporting if closed unexpectedly =====
IF ERRORLEVEL 1 (
    echo.
    echo =========================================
    echo   WARNING: Myra AI exited with code %ERRORLEVEL%.
    echo   Check any error text above for details.
    echo =========================================
    pause
)

echo Process terminated normally.
exit /b 0
