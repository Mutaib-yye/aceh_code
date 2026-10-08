@echo off
setlocal
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py -3"

if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto no_python
)

call ".venv\Scripts\activate.bat"
python -c "import gradio, transformers, torch, sentencepiece" >nul 2>nul
if errorlevel 1 goto install

:run
python -m acehid app %*
echo.
echo The app has stopped. Press any key to close this window.
pause >nul
exit /b 0

:install
echo Installing. The first time only, this takes 10 minutes or more.
python -m pip install -q --upgrade pip
python -m pip install -q "gradio==6.29.1" "transformers==5.19.0" "sentencepiece>=0.2" torch huggingface_hub
if errorlevel 1 goto install_failed
goto run

:no_python
echo Python 3.10 or newer was not found. Install it from python.org, tick "Add python.exe to PATH", then run this file again.
pause
exit /b 1

:install_failed
echo Installing failed. Copy the text above and send it to Claude.
pause
exit /b 1
