@echo off
setlocal
cd /d "%~dp0"
title Doodle Baseball Expanded V19 - GitHub Release Edition
py launcher.py
if errorlevel 1 (
  python launcher.py
)
if errorlevel 1 (
  echo.
  echo The launcher stopped with an error.
  pause
)
