# ERP for My Shop Installer

This folder contains the files to create a Windows installer for the ERP application.

## Requirements
- Inno Setup (download from https://jrsoftware.org/isinfo.php)
- The entire ERP project folder (this should be in the parent directory)

## Creating the Standalone EXE (Recommended)
To avoid Python/venv issues, create a single executable:

1. Activate the venv: `venv\Scripts\activate`
2. Install PyInstaller: `pip install pyinstaller`
3. Build the EXE: `pyinstaller --onefile run_app.py`
4. Move `dist\run_app.exe` to this `deployment/` folder.

## How to Create the Installer
1. Open `erp_setup.iss` with Inno Setup Compiler.
2. Click "Compile" (or press F9).
3. The installer `ERPSetup.exe` will be created in your Inno Setup output directory.

## How to Install
1. Run `ERPSetup.exe` on any Windows computer.
2. Follow the installation wizard.
3. Launch the app from the desktop shortcut.

## Notes
- The installer includes the virtual environment, so no additional Python installation is needed.
- The app runs as a desktop application using pywebview (embedded web view).
- For WebView2 compatibility, ensure Microsoft Edge WebView2 is installed (usually comes with Windows updates).