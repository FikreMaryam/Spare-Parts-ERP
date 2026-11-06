@echo off
title Spare Parts ERP - Update & Build Assistant
color 0A

echo ============================================================
echo           SPARE PARTS ERP - ONE-CLICK UPDATE TOOL
echo ============================================================
echo.

echo [*] Step 1: Checking Python virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment folder 'venv' not found. Using system Python...
)

echo.
echo [*] Step 2: Checking database migrations...
python manage.py makemigrations
python manage.py migrate

echo.
echo [*] Step 3: Rebuilding Windows Executable Package...
python build_exe.py

echo.
echo ============================================================
echo [!] UPDATE & REBUILD COMPLETE!
echo [!] Your updated executable is located at:
echo     dist\SparePartsERP\SparePartsERP.exe
echo ============================================================
echo.
pause
