@echo off
title Nexus AI Master Launcher
color 0b
cls
echo ===============================================================================
echo                     NEXUS AI COMPANION - SYSTEM LAUNCHER
echo ===============================================================================
echo.
echo Starting subsystems in independent persistent windows...
echo.

:: 1. Start Clicky HUD Overlay in its own window
echo [1/2] Launching Clicky Visual HUD...
start "Nexus HUD (Clicky)" cmd /k "title Nexus HUD && cd /d C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\repos\clicky-windows && npx.cmd electron . --disable-gpu --disable-gpu-compositing --no-sandbox"

timeout /t 3 /nobreak >nul

:: 2. Start Core Voice Daemon in its own window
echo [2/2] Launching Nexus Voice Daemon...
start "Nexus Voice Daemon" cmd /k "title Nexus Voice Daemon && cd /d C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent && "C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\runtime\python\python.exe" -u laptop\nexus_daemon.py"

echo.
echo ===============================================================================
echo  NEXUS IS NOW FULLY ACTIVE AND RUNNING!
echo.
echo  HOTKEYS TO ACTIVATE:
echo    - Press: Win + Alt
echo    - Or:    Alt + Space
echo    - Or:    Ctrl + Shift + Space
echo.
echo  VOICE COMMANDS TO TRY ALOUD:
echo    - "Hey Nexus, open Chrome"
echo    - "Hey Nexus, what are my routines?"
echo    - "Hey Nexus, check system status"
echo.
echo  Keep the two small background windows open while using Nexus!
echo ===============================================================================
echo.
pause
