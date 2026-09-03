@echo off
setlocal
cd /d "%~dp0"
title YouTube Video Frame Extractor - Setup

echo.
echo ==============================================================
echo   YouTube Video Frame Extractor - One-time setup
echo ==============================================================
echo.

where py >nul 2>&1
if not errorlevel 1 goto :create_with_py

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3 was not found.
  echo Install Python from https://www.python.org/downloads/
  echo Enable "Add Python to PATH" during installation.
  pause
  exit /b 1
)

echo Creating the local Python environment...
if not exist ".venv\Scripts\python.exe" python -m venv .venv
goto :install_python

:create_with_py
echo Creating the local Python environment...
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv

:install_python
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: The Python environment could not be created.
  pause
  exit /b 1
)

echo Installing application packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :install_failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed

".venv\Scripts\python.exe" -c "from system_checks import javascript_runtime; raise SystemExit(0 if javascript_runtime() else 1)"
if not errorlevel 1 goto :runtime_ready

echo.
echo YouTube requires a JavaScript runtime. Deno is recommended.
where winget >nul 2>&1
if errorlevel 1 goto :runtime_manual

choice /M "Install Deno now with Windows Package Manager"
if errorlevel 2 goto :runtime_manual
winget install DenoLand.Deno --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :runtime_manual
".venv\Scripts\python.exe" -c "from system_checks import javascript_runtime; raise SystemExit(0 if javascript_runtime() else 1)"
if errorlevel 1 goto :runtime_manual
goto :runtime_ready

:runtime_manual
echo.
echo WARNING: Deno 2.3+ or Node.js 22+ is still required for YouTube downloads.
echo Install Deno from https://docs.deno.com/runtime/getting_started/installation/

:runtime_ready
where ffmpeg >nul 2>&1
if not errorlevel 1 goto :complete
echo.
echo NOTE: FFmpeg was not found. The app will use compatible standard-quality
echo streams. Install FFmpeg later if you want merged 720p video streams.
echo Download: https://ffmpeg.org/download.html

:complete
echo.
echo ==============================================================
echo   Setup complete. Double-click start.bat to run the app.
echo ==============================================================
echo.
pause
exit /b 0

:install_failed
echo.
echo ERROR: Package installation failed. Check your internet connection,
echo then run setup.bat again.
pause
exit /b 1
