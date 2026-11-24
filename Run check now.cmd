@echo off
rem One-click run: does exactly what the 06:30 scheduled task does, then opens the dashboard.
rem Takes about 3 minutes. Nothing is sent - drafts only.
echo Running the solar job exceptions check (about 3 minutes)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_daily.ps1"
echo Done. Opening the dashboard...
start "" "%~dp0output\dashboard.html"
