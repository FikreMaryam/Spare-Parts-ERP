# Windows setup

## Run without installing Python

Download the latest `SparePartsERP-Windows-Standalone` artifact from the
repository's **Build Windows standalone app** GitHub Actions run. Extract it,
then double-click `SparePartsERP/SparePartsERP.exe`. Keep the `_internal`
folder beside the EXE. The ZIP includes Python and its dependencies.

On first start, read `INITIAL_ADMIN_CREDENTIALS.txt`, sign in, change the
password, and delete the credentials file.

To build the latest source, push it to `master` or manually run the **Build
Windows standalone app** workflow from the GitHub Actions tab. Download the
workflow artifact before its 30-day retention expires.

## Build from source

To run the latest source directly, install Python 3.12 for Windows (including
the Python Launcher), then double-click `start_windows.bat`. The first run
creates a virtual environment and installs the dependencies, so it needs
internet access.

If you want to continue using existing shop data, copy
`db.sqlite3` and the `media` folder from the old PC while the app is stopped.
Keep these files private; they contain shop data and uploaded files.

The app opens in a browser on the Windows PC. To use this Windows PC as a
server for other computers on the same trusted Wi-Fi/LAN, use the Network URL
printed in the command window. Allow Python through Windows Firewall on private
networks if prompted. The server PC must remain on and the command window must
remain open.

Each installation has its own database unless you copy the database and media.
This HTTP setup is for local-network testing only; do not expose it directly to
the public internet.
