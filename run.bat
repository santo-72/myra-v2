@echo off
chcp 65001 >nul 2>&1
title Myra AI Assistant
echo =========================================
echo       Starting Myra AI Assistant
echo =========================================
echo.

REM Navigate to the script's own directory
cd /d "%~dp0"

REM ===== Step 1: Create Virtual Environment if missing =====
IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [Step 1/3] Creating virtual environment...
    python -m venv .venv
    IF ERRORLEVEL 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python is installed and added to PATH.
        echo Download Python from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
) ELSE (
    echo [Step 1/3] Virtual environment found.
)

REM ===== Step 2: Activate Virtual Environment =====
echo [Step 2/3] Activating virtual environment...
call .venv\Scripts\activate.bat

REM ===== Step 3: Check if ALL key packages are installed =====
echo [Step 3/3] Checking dependencies...
python -c "import PyQt6; import psutil; import structlog; import sounddevice; import websockets; import numpy; import scipy" >nul 2>&1
IF ERRORLEVEL 1 (
    echo           Some dependencies are missing. Installing now...
    echo           This may take 5-15 minutes. Please wait.
    echo.

    REM Install uv first (much faster and smarter than pip)
    pip install uv >nul 2>&1

    REM Use uv to install all dependencies
    uv pip install -e .
    IF ERRORLEVEL 1 (
        echo.
        echo WARNING: uv failed. Falling back to pip...
        pip install -e .
    )
    echo.
    echo Installation complete!
) ELSE (
    echo           All dependencies are installed.
)

echo.
echo =========================================
echo       Launching Myra AI...
echo =========================================
echo.

REM ===== Run the main application =====
python main.py

REM ===== If it crashes, show the error =====
IF ERRORLEVEL 1 (
    echo.
    echo =========================================
    echo   ERROR: Myra exited with an error.
    echo   Check the messages above for details.
    echo =========================================
)

echo.
echo Process finished.
pause
