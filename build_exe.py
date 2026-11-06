import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

LOCAL_APPS = ['core', 'inventory', 'sales', 'expenses', 'hr', 'store', 'b2b', 'customers', 'reports']

def discover_hidden_imports():
    """Recursively collect all module paths for local Django apps."""
    hidden_imports = set()
    for app in LOCAL_APPS:
        app_path = BASE_DIR / app
        if app_path.is_dir():
            hidden_imports.add(app)
            for py_file in app_path.rglob('*.py'):
                rel_path = py_file.relative_to(BASE_DIR)
                parts = rel_path.with_suffix('').parts
                mod_name = '.'.join(parts)
                if mod_name.endswith('.__init__'):
                    mod_name = mod_name[:-9]
                if mod_name:
                    hidden_imports.add(mod_name)
    return sorted(list(hidden_imports))

APP_NAME = "SparePartsERP"

def ensure_icon():
    """Locate or generate a default icon.ico file for the executable."""
    icon_path = BASE_DIR / "app_icon.ico"
    if not icon_path.exists():
        alt_icon = BASE_DIR / "icon.ico"
        if alt_icon.exists():
            return alt_icon
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGBA', (256, 256), color=(15, 23, 42))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([16, 16, 240, 240], radius=36, fill=(30, 41, 59), outline=(59, 130, 246), width=8)
            draw.ellipse([76, 76, 180, 180], fill=(59, 130, 246))
            draw.ellipse([104, 104, 152, 152], fill=(15, 23, 42))
            img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            print(f"[+] Default icon created at: {icon_path}")
        except Exception as e:
            print(f"[!] Note on icon creation: {e}")
            return None
    return icon_path

def build():
    print(f"[*] Starting PyInstaller build process for {APP_NAME}...")

    try:
        import PyInstaller
    except ImportError as exc:
        raise RuntimeError(
            "PyInstaller is required. Install project requirements before building."
        ) from exc

    dist_folder = BASE_DIR / "dist" / APP_NAME
    if dist_folder.exists():
        import shutil
        shutil.rmtree(dist_folder)

    icon = ensure_icon()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", APP_NAME,
    ]

    if icon and icon.exists():
        cmd.extend(["--icon", str(icon)])
        print(f"[*] Using application icon: {icon}")

    # Include global templates & static folders
    if (BASE_DIR / 'templates').is_dir():
        cmd.extend(["--add-data", f"{BASE_DIR / 'templates'};templates"])
    if (BASE_DIR / 'static').is_dir():
        cmd.extend(["--add-data", f"{BASE_DIR / 'static'};static"])
    if (BASE_DIR / 'staticfiles').is_dir():
        cmd.extend(["--add-data", f"{BASE_DIR / 'staticfiles'};staticfiles"])

    # Include local app directories
    for app in LOCAL_APPS:
        app_path = BASE_DIR / app
        if app_path.is_dir():
            cmd.extend(["--add-data", f"{app_path};{app}"])

    # Standard Django & library hidden imports
    django_hidden = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "django.db.backends.postgresql",
        "django.db.backends.sqlite3",
        "django_tenants",
        "django_tenants.routers",
        "whitenoise",
        "whitenoise.middleware",
        "psycopg2",
        "reportlab",
        "openpyxl",
        "webview",
    ]
    for imp in django_hidden:
        cmd.extend(["--hidden-import", imp])

    # Discovered local app modules
    local_modules = discover_hidden_imports()
    print(f"[*] Discovered {len(local_modules)} local modules to bundle.")
    for mod in local_modules:
        cmd.extend(["--hidden-import", mod])

    cmd.append("launcher.py")

    print(f"[*] Executing PyInstaller build...\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist_folder = BASE_DIR / "dist" / "SparePartsERP"
        readme = BASE_DIR / "WINDOWS_STANDALONE_README.txt"
        if readme.is_file():
            import shutil
            shutil.copy2(readme, dist_folder / "README.txt")
        print("\n" + "=" * 60)
        print("[+] BUILD SUCCESSFUL!")
        print(f"[+] Executable directory: {dist_folder}")
        print(f"[+] Executable file: {dist_folder / 'SparePartsERP.exe'}")
        print("=" * 60 + "\n")
    else:
        raise subprocess.CalledProcessError(result.returncode, cmd)

if __name__ == '__main__':
    build()
