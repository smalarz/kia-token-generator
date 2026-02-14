@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Kia Token Generator - EXE Builder

echo.
echo ============================================================
echo   Kia Token Generator - EXE Builder
echo ============================================================
echo.

REM ============================================================
REM  STEP 0: Check prerequisites
REM ============================================================
echo [0/4] Checking prerequisites...
echo.
set "ERRORS=0"

REM --- Check: KIA_TOKEN.py in current folder ---
if not exist "KIA_TOKEN.py" (
    echo   [X] KIA_TOKEN.py NOT FOUND in this folder
    echo       Make sure build_exe.bat and KIA_TOKEN.py are in the same folder.
    echo.
    set /a ERRORS+=1
) else (
    echo   [OK] KIA_TOKEN.py found
)

REM --- Check: Python ---
set "PYTHON_CMD="

where python >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
    echo !PYVER! | findstr /r "Python 3\." >nul 2>&1
    if !errorlevel!==0 (
        set "PYTHON_CMD=python"
    )
)

if "!PYTHON_CMD!"=="" (
    where python3 >nul 2>&1
    if !errorlevel!==0 (
        for /f "tokens=*" %%v in ('python3 --version 2^>^&1') do set "PYVER=%%v"
        echo !PYVER! | findstr /r "Python 3\." >nul 2>&1
        if !errorlevel!==0 (
            set "PYTHON_CMD=python3"
        )
    )
)

if "!PYTHON_CMD!"=="" (
    where py >nul 2>&1
    if !errorlevel!==0 (
        for /f "tokens=*" %%v in ('py -3 --version 2^>^&1') do set "PYVER=%%v"
        echo !PYVER! | findstr /r "Python 3\." >nul 2>&1
        if !errorlevel!==0 (
            set "PYTHON_CMD=py -3"
        )
    )
)

if "!PYTHON_CMD!"=="" (
    echo   [X] Python 3 NOT FOUND
    echo.
    echo       How to install Python:
    echo       1. Go to https://www.python.org/downloads/
    echo       2. Click the big yellow "Download Python 3.x.x" button
    echo       3. Run the downloaded file
    echo       4. IMPORTANT: Check the box "Add Python to PATH" at the bottom!
    echo       5. Click "Install Now"
    echo       6. Close this window and run build_exe.bat again
    echo.
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do set "PYVER=%%v"
    echo   [OK] !PYVER! ^(!PYTHON_CMD!^)
)

REM --- Check: Python can create venv ---
if not "!PYTHON_CMD!"=="" (
    !PYTHON_CMD! -m venv --help >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [X] Python 'venv' module is missing
        echo       Reinstall Python from https://www.python.org/downloads/
        echo       Make sure to check "Install pip" and "Add to PATH" during setup.
        echo.
        set /a ERRORS+=1
    ) else (
        echo   [OK] Python venv module available
    )
)

REM --- Check: pip works ---
if not "!PYTHON_CMD!"=="" (
    !PYTHON_CMD! -m pip --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [X] pip is missing or broken
        echo       Try running: !PYTHON_CMD! -m ensurepip --upgrade
        echo       Or reinstall Python from https://www.python.org/downloads/
        echo.
        set /a ERRORS+=1
    ) else (
        for /f "tokens=*" %%p in ('!PYTHON_CMD! -m pip --version 2^>^&1') do set "PIPVER=%%p"
        echo   [OK] !PIPVER!
    )
)

echo.

REM --- Stop if anything is missing ---
if %ERRORS% gtr 0 (
    echo ============================================================
    echo   Cannot continue — %ERRORS% problem^(s^) found above.
    echo   Fix them and run this script again.
    echo ============================================================
    goto :end
)

echo   All prerequisites OK!
echo.

REM ============================================================
REM  STEP 1: Create virtual environment
REM ============================================================
echo [1/4] Creating virtual environment...
if exist ".build_venv" (
    echo   Removing old .build_venv...
    rmdir /s /q .build_venv
)

!PYTHON_CMD! -m venv .build_venv
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Could not create virtual environment.
    echo   Your Python installation may be corrupted.
    echo   Reinstall from https://www.python.org/downloads/
    goto :end
)
echo   Done.
echo.

REM ============================================================
REM  STEP 2: Activate venv and upgrade pip
REM ============================================================
echo [2/4] Activating environment and upgrading pip...
call .build_venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo   ERROR: Could not activate virtual environment.
    goto :end
)

python -m pip install --upgrade pip -q >nul 2>&1
echo   Done.
echo.

REM ============================================================
REM  STEP 3: Install dependencies
REM ============================================================
echo [3/4] Installing dependencies (pyinstaller, requests, websocket-client)...
pip install pyinstaller requests websocket-client -q
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: Could not install dependencies.
    echo.
    echo   Possible causes:
    echo   - No internet connection
    echo   - Firewall/proxy blocking pip
    echo   - Try: pip install pyinstaller requests websocket-client
    goto :end
)
echo   Done.
echo.

REM ============================================================
REM  STEP 4: Build EXE
REM ============================================================
echo [4/4] Building KIA_TOKEN.exe (this may take a minute)...
echo.
pyinstaller --onefile --name KIA_TOKEN --clean --noconfirm KIA_TOKEN.py
if %errorlevel% neq 0 (
    echo.
    echo   ERROR: PyInstaller build failed. See errors above.
    goto :end
)

REM --- Verify the EXE exists ---
if not exist "dist\KIA_TOKEN.exe" (
    echo.
    echo   ERROR: Build seemed to succeed but dist\KIA_TOKEN.exe was not created.
    goto :end
)

REM --- Show file size ---
for %%F in (dist\KIA_TOKEN.exe) do set "FILESIZE=%%~zF"
set /a FILESIZE_MB=!FILESIZE! / 1048576

echo.
echo ============================================================
echo   Build complete!
echo ============================================================
echo.
echo   Your file: dist\KIA_TOKEN.exe (ca. !FILESIZE_MB! MB)
echo.
echo   You can copy KIA_TOKEN.exe anywhere and double-click it.
echo   No Python needed to run it — it's fully standalone.
echo.
echo   NOTE: Windows Defender / SmartScreen may show a warning
echo   when you first run the .exe — click "More info" then
echo   "Run anyway". This is normal for unsigned executables.
echo.

deactivate >nul 2>&1

:end
echo.
pause
