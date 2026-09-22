@echo off
chcp 65001 >nul
title NEXUS - Real-Time AI Companion
color 0B
cls
echo ===============================================================================
echo                NEXUS REAL-TIME MULTIMODAL VOICE AGENT
echo      Zero-Mock * 100%% Local * Local VAD * llama.cpp * Vivo Office Kit
echo ===============================================================================
echo.

set PYTHON_EXE=C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\runtime\python\python.exe
set SCRIPT=C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent\laptop\nexus_daemon.py

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python standalone runtime not found at: %PYTHON_EXE%
    pause
    exit /b 1
)

echo [*] Initializing Audio Subsystem...
echo [*] Engaging Nexus Unified Voice Daemon...
echo.

"%PYTHON_EXE%" -u "%SCRIPT%"

pause
