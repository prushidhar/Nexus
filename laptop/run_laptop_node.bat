@echo off
title Nexus Laptop Node - iQOO Hackathon 2026
echo ==========================================================
echo    Nexus Laptop Office Kit Bridge (RTX 2050 CUDA Node)
echo ==========================================================
cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] Python detected. Checking dependencies...
    python -m pip install -r requirements.txt >nul 2>nul
    echo [INFO] Starting Python Office Kit Watcher...
    python watcher.py
) else (
    echo [INFO] Python not found in PATH.
    echo [INFO] Falling back to Zero-Dependency Native PowerShell Watcher...
    powershell -ExecutionPolicy Bypass -File watcher.ps1
)

pause
