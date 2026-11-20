@echo off
chcp 65001 >nul
title Building Lunarix Launcher EXE

echo ========================================================
echo        Building Lunarix Launcher (.EXE)
echo ========================================================
echo.

cd /d "%~dp0"
py -3.12 build.py

pause
