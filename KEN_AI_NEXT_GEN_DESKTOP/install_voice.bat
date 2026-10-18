@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements-voice.txt
if errorlevel 1 (
  echo Voice add-on installation failed.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sounddevice, faster_whisper, pyttsx3"
if errorlevel 1 (
  echo Voice packages could not be loaded. Review the installation error above.
  pause
  exit /b 1
)
echo Voice recognition and speech output installed. Whisper downloads its model the first time you use the microphone.
pause
