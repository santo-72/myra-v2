@echo off
chcp 65001 > nul
title M.Y.R.A - Contact & Phone Number Importer
cd /d "%~dp0"
echo Running M.Y.R.A Contact Importer...
venv\Scripts\python.exe import_contacts.py
pause
