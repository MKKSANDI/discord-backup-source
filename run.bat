@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "LOG_DIR=%TEMP%\DiscordAccountBackup"
set "LAUNCHER_LOG=%LOG_DIR%\launcher.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

set "ELEVATED_FLAG=0"
if /i "%~1"=="--elevated" (
    set "ELEVATED_FLAG=1"
    shift
)

net session >nul 2>&1
if errorlevel 1 (
    if "%ELEVATED_FLAG%"=="1" (
        echo Failed to start with administrator privileges.
        echo Accept the UAC prompt, or run Command Prompt as Administrator and retry.
        echo Launcher log: "%LAUNCHER_LOG%"
        >>"%LAUNCHER_LOG%" echo [%date% %time%] admin check failed after elevation.
        pause
        exit /b 1
    )
    echo Requesting administrator privileges...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c """"%~f0"""" --elevated %*' -Verb RunAs"
    if errorlevel 1 (
        echo Could not launch the elevated process.
        echo Launcher log: "%LAUNCHER_LOG%"
        >>"%LAUNCHER_LOG%" echo [%date% %time%] failed to spawn elevated process.
        pause
        exit /b 1
    )
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON="
)

if not defined PYTHON (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON=python"
)

if not defined PYTHON (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON=py -3"
)

if not defined PYTHON (
    echo Python was not found. Install Python 3.10+ and re-run.
    echo Launcher log: "%LAUNCHER_LOG%"
    >>"%LAUNCHER_LOG%" echo [%date% %time%] no python runtime found.
    pause
    exit /b 1
)

%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies from requirements.txt.
    echo Launcher log: "%LAUNCHER_LOG%"
    >>"%LAUNCHER_LOG%" echo [%date% %time%] dependency install failed.
    pause
    exit /b 1
)

%PYTHON% main.py %*
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo.
    echo DiscordAccountBackup exited with code %APP_EXIT%.
    echo Launcher log: "%LAUNCHER_LOG%"
    >>"%LAUNCHER_LOG%" echo [%date% %time%] app exited with code %APP_EXIT%.
    pause
)
exit /b %APP_EXIT%
