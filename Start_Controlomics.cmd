@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The local Python environment is missing. Follow README.md to install Controlomics.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m controlomics serve
