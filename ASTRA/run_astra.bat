@echo off
setlocal

REM Run from the repository root no matter where this script is launched from.
cd /d "%~dp0"

REM Start ASTRA CLI.
python -m main

endlocal
