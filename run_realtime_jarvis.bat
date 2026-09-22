@echo off
chcp 65001 >nul
title JARVIS - Real-Time AI Voice Assistant [iQOO Hackathon 2026]
color 0B
cls
echo ===============================================================================
echo                JARVIS REAL-TIME MULTIMODAL DESKTOP VOICE AGENT
echo      Zero-Mock * 100%% Local * openWakeWord * llama.cpp * Vivo Office Kit
echo ===============================================================================
echo.

set PYTHON_EXE=C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\runtime\python\python.exe
set SCRIPT=C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent\laptop\jarvis_realtime.py

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python standalone runtime not found at: %PYTHON_EXE%
    pause
    exit /b 1
)

echo [*] Initializing Logitech G435 Wireless Audio Subsystem...
echo [*] Loading openWakeWord 'Hey Jarvis' Neural Model...
echo [*] Starting Real-Time Voice Agent Loop...
echo.

"%PYTHON_EXE%" "%SCRIPT%"

pause
