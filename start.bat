@echo off
setlocal
cd /d "%~dp0"
title YouTube Video Frame Extractor

if not exist ".venv\Scripts\python.exe" (
  echo The app has not been set up yet.
  choice /M "Run the one-time setup now"
  if errorlevel 2 exit /b 1
  call setup.bat
  if errorlevel 1 exit /b 1
)

echo.
echo Starting the local app...
echo Keep this window open while you use the extractor.
echo Press Ctrl+C here when you are finished.
echo.

".venv\Scripts\python.exe" app.py --open-browser
if errorlevel 1 (
  echo.
  echo The app stopped because of an error.
  pause
)
