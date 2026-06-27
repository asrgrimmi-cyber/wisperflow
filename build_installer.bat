@echo off
title Wisper — Build Installer
echo.
echo ==========================================
echo   Wisper — Build Production Installer
echo ==========================================
echo.

:: Step 1: Activate venv
if not exist venv (
    echo [ERROR] No venv found. Run setup.py first.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

:: Step 2: Install build tools
echo [1/3] Installing build tools...
pip install -q pyinstaller

:: Step 3: Build exe with PyInstaller
echo [2/3] Building Wisper.exe (this takes a few minutes)...
pyinstaller build.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)
echo [OK] Wisper.exe built → dist\Wisper.exe

:: Step 4: Build installer with Inno Setup (if available)
echo [3/3] Building installer...
where iscc >nul 2>&1
if errorlevel 1 (
    echo.
    echo [SKIP] Inno Setup not found.
    echo   To create the installer:
    echo   1. Install Inno Setup: https://jrsoftware.org/isinfo.php
    echo   2. Run: iscc installer.iss
    echo.
    echo   For now, you can distribute dist\Wisper.exe directly.
) else (
    iscc installer.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup build failed.
        pause
        exit /b 1
    )
    echo [OK] Installer built → dist\WisperSetup.exe
)

echo.
echo ==========================================
echo   Build complete!
echo.
echo   Distributable files:
echo     dist\Wisper.exe       — standalone app
if exist dist\WisperSetup.exe (
echo     dist\WisperSetup.exe  — Windows installer
)
echo ==========================================
pause
