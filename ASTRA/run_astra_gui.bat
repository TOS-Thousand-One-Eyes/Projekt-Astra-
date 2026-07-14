@echo off
setlocal

REM Run from the repository root no matter where this script is launched from.
cd /d "%~dp0"

REM Start ASTRA's lightweight Tkinter GUI without requiring an editable install.
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
python -m gui.app

endlocal
