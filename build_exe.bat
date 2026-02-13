@echo off
REM Build KIA_TOKEN.exe - run this on Windows
REM Requirements: Python 3.8+ installed

echo [1/3] Creating virtual environment...
python -m venv .build_venv
call .build_venv\Scripts\activate.bat

echo [2/3] Installing dependencies...
pip install -q pyinstaller requests websocket-client

echo [3/3] Building KIA_TOKEN.exe...
pyinstaller --onefile --name KIA_TOKEN --clean --noconfirm KIA_TOKEN.py

echo.
echo ============================================================
echo   Build complete! File: dist\KIA_TOKEN.exe
echo ============================================================
echo.

deactivate
pause
