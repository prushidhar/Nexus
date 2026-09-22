@echo off
title Build and Deploy Nexus Agent to iQOO 15
echo =================================================================
echo        NEXUS // ONE-CLICK APK COMPILER & ADB DEPLOYER
echo =================================================================
cd /d "%~dp0\android"

echo [1/4] Checking Java Environment...
java -version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Java is not detected in PATH. Please install JDK 17+.
    pause
    exit /b 1
)

echo [2/4] Compiling Debug APK via Gradle...
call gradlew.bat assembleDebug

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Gradle build encountered errors. Please inspect the log above.
    pause
    exit /b 1
)

echo.
echo [3/4] Build Succeeded! Locating APK...
set APK_PATH=app\build\outputs\apk\debug\app-debug.apk
if not exist "%APK_PATH%" (
    echo [WARNING] APK not found at default location: %APK_PATH%
    pause
    exit /b 0
)

echo [4/4] Checking for connected Android device via ADB...
where adb >nul 2>&1
if %ERRORLEVEL% equ 0 (
    adb devices | findstr /C:"device" >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [DEPLOY] Installing Nexus APK onto connected device...
        adb install -r "%APK_PATH%"
        echo [LAUNCH] Starting Nexus MainActivity...
        adb shell am start -n com.nexus.agent/.ui.MainActivity
        echo.
        echo =================================================================
        echo  SUCCESS: Nexus Agent is running on your device!
        echo =================================================================
    ) else (
        echo [NOTICE] No device detected via ADB.
        echo APK is ready at: %~dp0android\%APK_PATH%
    )
) else (
    echo [NOTICE] ADB command not found in PATH.
    echo APK is ready at: %~dp0android\%APK_PATH%
)

pause
