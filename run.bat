@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" kawarimi.py %*
pause
