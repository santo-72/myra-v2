@echo off
echo =========================================
echo Starting Myra AI Assistant
echo =========================================

REM Navigate to the project directory just in case it's run from somewhere else
cd /d "%~dp0"

REM Run the main Python script
python main.py

REM Pause so the user can see any errors if the script crashes
echo.
echo Process finished.
pause
