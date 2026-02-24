@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==================================================
echo   Building Sekolah Kita Scraper for Windows
echo ==================================================
echo.
echo This script will compile the Python program into an .exe file.
echo You must run this on a computer WITH Python installed.
echo.
echo Press any key to start...
pause >nul

REM Check requirements
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found!
    echo Please make sure you are running this script from the project folder.
    pause
    exit /b 1
)

REM --- Python Detection ---
echo Checking for Python...

REM Try 'python'
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :FOUND_PYTHON
)

REM Try 'py'
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :FOUND_PYTHON
)

REM Try 'python3'
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :FOUND_PYTHON
)

REM Failed to find python
echo [ERROR] Python is not installed or not in PATH.
echo Please install Python (3.8+) from python.org.
echo Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:FOUND_PYTHON
echo Using Python command: !PYTHON_CMD!
!PYTHON_CMD! --version
echo.

REM --- Create Venv ---
echo [1/4] Creating virtual environment...
if exist venv_build (
    echo Removing old venv...
    rmdir /s /q venv_build
)

!PYTHON_CMD! -m venv venv_build
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    echo Command used: !PYTHON_CMD! -m venv venv_build
    pause
    exit /b 1
)

REM --- Install Deps ---
echo.
echo [2/4] Installing requirements...
if not exist venv_build\Scripts\activate.bat (
    echo [ERROR] venv activation script not found!
    echo Creation might have failed silently or path is wrong.
    pause
    exit /b 1
)

call venv_build\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Use 'python' now that venv is active
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

REM --- Build ---
echo.
echo [3/4] Building executable with PyInstaller...
echo Verifying PyInstaller installation...
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found in virtual environment!
    echo Trying to install it manually...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo.
echo Cleaning up old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

echo.
echo Starting build process...
echo Command: python -m PyInstaller --noconfirm --onefile --console --clean --name "sekolah-kita-scraper" "scrape_sekolah_kita.py"
echo.
echo NOTE: If this window closes suddenly, your Antivirus might be blocking the build.
echo Please disable Antivirus temporarily if that happens.
echo.
pause

REM Run build and capture output to log file to inspect if it crashes
echo Building... (this may take a minute)
call python -m PyInstaller --noconfirm --onefile --console --clean --name "sekolah-kita-scraper" "scrape_sekolah_kita.py" > build_log.txt 2>&1
set BUILD_STATUS=%errorlevel%

REM Show log output
type build_log.txt

if %BUILD_STATUS% neq 0 (
    echo.
    echo [ERROR] Build failed with error code %BUILD_STATUS%.
    echo Check build_log.txt for details.
    pause
    exit /b %BUILD_STATUS%
)

echo.
echo Build completed successfully.
pause

REM --- Cleanup ---
echo.
echo [4/4] Cleaning up...
call deactivate
REM rmdir /s /q venv_build

echo.
echo ==================================================
echo   Build Success!
echo ==================================================
echo.
echo The executable is located at:
echo   %~dp0dist\sekolah-kita-scraper.exe
echo.
echo You can now copy this .exe to a computer without Python.
echo.
pause
