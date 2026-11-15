@echo off
rem Run any acehid command with the project's Python:   acehid.bat make-packs --people "A,B,C" --per-person 25
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m acehid %*
) else (
    where py >nul 2>nul && (py -3 -m acehid %*) || (python -m acehid %*)
)
