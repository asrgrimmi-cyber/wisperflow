@echo off
:: Wisper Installer - installs Wisper.exe and creates shortcuts
:: Run as Administrator for Program Files install, or it falls back to AppData.

setlocal

echo.
echo  ===========================
echo    Wisper Installer v1.0
echo  ===========================
echo.

:: Get the directory this script lives in
pushd "%~dp0"
set "SRC_DIR=%CD%"
popd

:: Check exe exists
if not exist "%SRC_DIR%\dist\Wisper.exe" (
    echo  ERROR: dist\Wisper.exe not found. Build first: pyinstaller build.spec
    pause
    exit /b 1
)

:: Determine install directory - try Program Files, fall back to AppData
set "INSTALL_DIR=%LocalAppData%\Wisper"
mkdir "%ProgramFiles%\Wisper" 2>nul && set "INSTALL_DIR=%ProgramFiles%\Wisper"
if "%INSTALL_DIR%"=="%LocalAppData%\Wisper" (
    echo  No admin rights - installing to AppData instead.
    mkdir "%INSTALL_DIR%" 2>nul
)

echo  Installing to: %INSTALL_DIR%
echo.

:: Copy files
copy /Y "%SRC_DIR%\dist\Wisper.exe" "%INSTALL_DIR%\Wisper.exe" >nul
if errorlevel 1 (
    echo  ERROR: Could not copy Wisper.exe.
    pause
    exit /b 1
)
copy /Y "%SRC_DIR%\config.yaml" "%INSTALL_DIR%\config.yaml" >nul 2>nul
echo  [OK] Files copied.

:: Create Start Menu shortcut
set "START_MENU=%AppData%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\Wisper.lnk'); $s.TargetPath = '%INSTALL_DIR%\Wisper.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'Wisper Speech-to-Text'; $s.Save()"
echo  [OK] Start Menu shortcut created.

:: Create Desktop shortcut
set "DESKTOP=%UserProfile%\Desktop"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\Wisper.lnk'); $s.TargetPath = '%INSTALL_DIR%\Wisper.exe'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.Description = 'Wisper Speech-to-Text'; $s.Save()"
echo  [OK] Desktop shortcut created.

:: Create uninstaller
(
    echo @echo off
    echo echo Uninstalling Wisper...
    echo taskkill /F /IM Wisper.exe 2^>nul
    echo timeout /t 2 /nobreak ^>nul
    echo del /Q "%INSTALL_DIR%\Wisper.exe"
    echo del /Q "%INSTALL_DIR%\config.yaml"
    echo del /Q "%START_MENU%\Wisper.lnk"
    echo del /Q "%DESKTOP%\Wisper.lnk"
    echo rmdir "%INSTALL_DIR%" 2^>nul
    echo echo Wisper has been uninstalled.
    echo pause
) > "%INSTALL_DIR%\uninstall.bat"
echo  [OK] Uninstaller created.

echo.
echo  Installation complete!
echo  You can launch Wisper from your Desktop or Start Menu.
echo.

set /p LAUNCH="  Launch Wisper now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    start "" "%INSTALL_DIR%\Wisper.exe"
)

endlocal
