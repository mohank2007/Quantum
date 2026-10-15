@echo off
setlocal enabledelayedexpansion
title Hybrid QML Disease Detection Platform

:: Change to platform directory
cd /d "%~dp0Diseases_Detection_Paltform"

echo =====================================================================
echo           Hybrid QML Disease Detection Platform Manager
echo =====================================================================
echo.

:: 1. Verify Docker CLI is installed
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker command was not found in your system PATH.
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

:: 2. Check if Docker Daemon is running
echo [1/3] Checking Docker engine status...
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Docker daemon is not running.
    echo [INFO] Attempting to launch Docker Desktop automatically...

    set "DOCKER_EXE="
    if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" (
        set "DOCKER_EXE=%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
    ) else if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        set "DOCKER_EXE=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    ) else if exist "%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe" (
        set "DOCKER_EXE=%ProgramFiles(x86)%\Docker\Docker\Docker Desktop.exe"
    )

    if defined DOCKER_EXE (
        start "" "!DOCKER_EXE!"
        echo [INFO] Docker Desktop launched from: "!DOCKER_EXE!"
        echo [INFO] Waiting for Docker engine to initialize (this typically takes 20-45 seconds)...
    ) else (
        echo [WARNING] Could not locate Docker Desktop.exe automatically.
        echo Please open Docker Desktop manually from the Windows Start Menu.
    )

    set /a attempts=0
    :wait_docker_loop
    timeout /t 3 /nobreak >nul
    set /a attempts+=1
    docker info >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [OK] Docker engine is now connected and ready!
        goto :docker_is_ready
    )
    if !attempts! leq 25 (
        echo   Waiting for Docker daemon... (!attempts!/25)
        goto :wait_docker_loop
    )

    echo.
    echo [ERROR] Docker daemon did not become ready in time.
    echo Tips:
    echo  1. Open Docker Desktop manually and wait until the whale icon turns steady (green).
    echo  2. If using WSL 2, make sure it is updated: wsl --update
    echo.
    pause
    exit /b 1
)

:docker_is_ready
echo [OK] Docker engine is active.
echo.

:: 3. Launch Platform Containers
echo [2/3] Building and starting platform containers (Docker Compose)...
docker compose up --build -d
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to start containers via Docker Compose.
    pause
    exit /b 1
)

:: 4. Open Browser
echo.
echo [3/3] Opening Web Application in your default browser...
timeout /t 2 /nobreak >nul
start http://localhost:3000

:menu
cls
echo =====================================================================
echo           Hybrid QML Disease Detection Platform - ONLINE
echo =====================================================================
echo.
echo   Service Endpoints:
echo     - Web Application:       http://localhost:3000
echo     - FastAPI Swagger Docs:  http://localhost:8000/api/v1/docs
echo     - FastAPI Health Probe:  http://localhost:8000/api/v1/health
echo     - MinIO Object Storage:  http://localhost:9001 (minioadmin / minioadmin)
echo.
echo   Demo Login:
echo     Email:    hqml@gmail.com
echo     Password: 12345678
echo =====================================================================
echo.
echo Select an action:
echo   [1] View live container logs (Press Ctrl+C to return to menu)
echo   [2] Run platform health check
echo   [3] Restart platform containers
echo   [4] Stop platform (docker compose down) and Exit
echo   [5] Exit console (Platform remains running in background)
echo.
set /p user_choice="Enter your choice (1-5): "

if "%user_choice%"=="1" goto :action_logs
if "%user_choice%"=="2" goto :action_health
if "%user_choice%"=="3" goto :action_restart
if "%user_choice%"=="4" goto :action_stop
if "%user_choice%"=="5" goto :action_exit

echo [WARNING] Invalid selection. Please enter a number between 1 and 5.
timeout /t 2 /nobreak >nul
goto :menu

:action_logs
echo.
echo Streaming container logs (Press Ctrl+C to return to menu)...
echo.
docker compose logs -f
goto :menu

:action_health
cls
echo =====================================================================
echo                       Platform Health Check
echo =====================================================================
echo.
echo [1] Checking Container Status:
docker compose ps
echo.
echo [2] Checking Endpoints:

curl -s -f -o nul http://localhost:8000/api/v1/health >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] FastAPI Backend is ONLINE  (http://localhost:8000/api/v1/health)
) else (
    echo   [--] FastAPI Backend is still starting or offline
)

curl -s -f -o nul http://localhost:3000/ >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] Frontend UI is ONLINE     (http://localhost:3000)
) else (
    echo   [--] Frontend UI is still starting or offline
)

curl -s -f -o nul http://localhost:9000/minio/health/live >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   [OK] MinIO Storage is ONLINE   (http://localhost:9000)
) else (
    echo   [--] MinIO Storage is still starting or offline
)
echo.
pause
goto :menu

:action_restart
echo.
echo Restarting platform containers...
docker compose restart
echo [OK] Containers restarted.
timeout /t 2 /nobreak >nul
goto :menu

:action_stop
echo.
echo Stopping all platform containers...
docker compose down
echo.
echo [OK] Platform has been stopped.
timeout /t 3 /nobreak >nul
exit /b 0

:action_exit
echo.
echo Platform is continuing to run in the background.
echo You can re-open this script anytime to manage or stop the platform.
timeout /t 2 /nobreak >nul
exit /b 0
