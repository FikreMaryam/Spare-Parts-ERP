@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 goto missing_python

py -3.12 --version >nul 2>&1
if errorlevel 1 goto missing_python

if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto setup_failed
)

set "PYTHON=%CD%\.venv\Scripts\python.exe"
"%PYTHON%" -m pip install --disable-pip-version-check -r requirements-prod.txt
if errorlevel 1 goto setup_failed

if not exist ".erp_secret_key" (
    "%PYTHON%" -c "from pathlib import Path; import secrets; Path('.erp_secret_key').write_text(secrets.token_urlsafe(64), encoding='ascii')"
    if errorlevel 1 goto setup_failed
)
set /p "DJANGO_SECRET_KEY=" < ".erp_secret_key"
if not defined DJANGO_SECRET_KEY goto setup_failed

if not exist "media" mkdir "media"
set "USE_SQLITE=True"
set "DEBUG=False"
set "CREATE_DEFAULT_ADMIN=True"

"%PYTHON%" manage.py collectstatic --noinput
if errorlevel 1 goto setup_failed

echo.
echo Starting Spare Parts ERP. Keep this window open while using the app.
echo On first start, save the one-time admin password printed below.
echo.
"%PYTHON%" launcher.py
goto finished

:missing_python
echo Python 3.12 is required. Install Python 3.12 for Windows, including the Python Launcher, then try again.
pause
exit /b 1

:setup_failed
echo Setup failed. Check the error above and make sure this folder is writable and internet access is available.
pause
exit /b 1

:finished
endlocal
