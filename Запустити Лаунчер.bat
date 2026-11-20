@echo off
chcp 65001 >nul
title Lunarix Client Launcher

set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not defined PY (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        set "PY=%%~dpnPyw.exe"
        if not exist "!PY!" set "PY=%%P"
    )
)
if not defined PY where pythonw >nul 2>&1 && set "PY=pythonw"
if not defined PY where python >nul 2>&1 && set "PY=python"

cd /d "%~dp0"
start "" "%PY%" "%~dp0main.py"
exit
