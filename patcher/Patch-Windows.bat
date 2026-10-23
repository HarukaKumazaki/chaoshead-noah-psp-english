@echo off
rem Double-click to choose the ISO, or drag the original ISO onto this file.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0patcher.ps1" %*
echo.
pause
