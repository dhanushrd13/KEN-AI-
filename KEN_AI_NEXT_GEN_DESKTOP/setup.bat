@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Reuse an existing working environment first.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version >nul 2>nul
  if not errorlevel 1 goto install_packages
  echo The existing .venv Python cannot start. Preserving it as a backup before rebuilding.
  for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%I"
  if not defined STAMP set "STAMP=backup"
  if exist ".venv-backup-%STAMP%" set "STAMP=%STAMP%-%RANDOM%"
  ren ".venv" ".venv-backup-%STAMP%"
  if errorlevel 1 goto failed
)

set "PYTHON_VERSION="
set "PYTHON_PATH="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.14 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_VERSION=3.14"
  if defined PYTHON_VERSION goto create_environment
  py -3.11 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_VERSION=3.11"
  if defined PYTHON_VERSION goto create_environment
)

if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_PATH=%LocalAppData%\Programs\Python\Python314\python.exe"
if defined PYTHON_PATH set "PYTHON_VERSION=3.14"
if defined PYTHON_PATH goto create_environment
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_PATH=%LocalAppData%\Programs\Python\Python311\python.exe"
if defined PYTHON_PATH set "PYTHON_VERSION=3.11"
if defined PYTHON_PATH goto create_environment
if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_PATH=%ProgramFiles%\Python314\python.exe"
if defined PYTHON_PATH set "PYTHON_VERSION=3.14"
if defined PYTHON_PATH goto create_environment
if exist "%ProgramFiles%\Python311\python.exe" set "PYTHON_PATH=%ProgramFiles%\Python311\python.exe"
if defined PYTHON_PATH set "PYTHON_VERSION=3.11"
if defined PYTHON_PATH goto create_environment

echo Python 3.14 or 3.11 was not found. KEN AI needs Python before setup can continue.
where winget >nul 2>nul
if errorlevel 1 goto manual_install
choice /c YN /m "Install Python 3.14 now using Windows Package Manager?"
if errorlevel 2 goto manual_install
winget install --id Python.Python.3.14 --exact --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto manual_install

where py >nul 2>nul
if not errorlevel 1 (
  py -3.14 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_VERSION=3.14"
  if defined PYTHON_VERSION goto create_environment
)
if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_PATH=%LocalAppData%\Programs\Python\Python314\python.exe"
if defined PYTHON_PATH set "PYTHON_VERSION=3.14"
if defined PYTHON_PATH goto create_environment
goto manual_install

:create_environment
echo Creating the KEN AI environment with Python %PYTHON_VERSION%...
if defined PYTHON_PATH (
  "%PYTHON_PATH%" -m venv .venv
) else (
  py -%PYTHON_VERSION% -m venv .venv
)
if errorlevel 1 goto failed

:install_packages
echo Installing KEN AI and voice packages. This may take several minutes.
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Use the KEN AI desktop icon to launch the assistant, or run run.bat from this folder.
cscript //nologo "%~dp0create_desktop_shortcut.vbs"
if errorlevel 1 echo Desktop shortcut could not be created automatically. Double-click create_desktop_shortcut.vbs once.
pause
exit /b 0

:manual_install
echo.
echo Install Python 3.14 or 3.11 from https://www.python.org/downloads/ .
echo Then run setup.bat again. If Windows asks, allow microphone access when KEN AI starts.
pause
exit /b 1

:failed
echo.
echo Setup failed while creating the environment or installing packages.
echo Check your internet connection, then run setup.bat again. Existing environment backup was preserved.
pause
exit /b 1
