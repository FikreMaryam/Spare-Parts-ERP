import os
import sys
import socket
import threading
import time
import secrets
from pathlib import Path

import webbrowser


def get_bool(env_name, default=False):
    """Parse environment booleans safely for development and production modes."""
    raw = os.getenv(env_name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}

# Ensure correct import paths and redirect logs when running inside PyInstaller bundle
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
    try:
        log_path = Path(sys.executable).parent / "app_startup.log"
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception:
        pass

    executable_dir = Path(sys.executable).parent
    env_file = executable_dir / '.env'
    if env_file.is_file():
        with env_file.open('r', encoding='utf-8') as env_stream:
            for line in env_stream:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    os.environ.setdefault('DEBUG', 'False')
    os.environ.setdefault('USE_SQLITE', 'True')
    os.environ.setdefault('CREATE_DEFAULT_ADMIN', 'True')
    if not os.getenv('DJANGO_SECRET_KEY') and not os.getenv('SECRET_KEY'):
        key_file = executable_dir / '.erp_secret_key'
        if key_file.is_file():
            secret_key = key_file.read_text(encoding='ascii').strip()
        else:
            secret_key = secrets.token_urlsafe(64)
            key_file.write_text(secret_key, encoding='ascii')
        os.environ['DJANGO_SECRET_KEY'] = secret_key

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()
from django.conf import settings

# Explicit imports for PyInstaller AST scanner (never executed at runtime before django.setup())
if False:
    import core.settings
    import core.views
    import core.urls
    import core.urls_tenant
    import core.urls_public
    import inventory
    import inventory.apps
    import inventory.models
    import inventory.views
    import sales
    import sales.apps
    import sales.models
    import sales.views
    import expenses
    import hr
    import store
    import b2b
    import customers

from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
from socketserver import ThreadingMixIn

class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

class QuietHandler(WSGIRequestHandler):
    """Custom request handler that silences noisy request logs in production desktop mode."""
    def log_message(self, format, *args):
        if os.getenv('DEBUG', 'True') == 'True':
            super().log_message(format, *args)

http_server = None

def get_lan_ip():
    """Discover local IP address on LAN (works both online and offline without internet)."""
    for target in [('10.255.255.255', 1), ('192.168.255.255', 1), ('8.8.8.8', 80)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(target)
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith('127.'):
                return ip
        except Exception:
            pass

    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass

    return '127.0.0.1'

def ensure_database_ready():
    """Run database migrations and ensure initial superuser setup if needed."""
    use_sqlite = get_bool('USE_SQLITE', True)
    try:
        from django.core.management import call_command
        print("[*] Running database migrations...")
        call_command('migrate', interactive=False, verbosity=0)

        from django.contrib.auth import get_user_model
        from django.utils.crypto import get_random_string
        User = get_user_model()
        should_create_default_admin = get_bool('CREATE_DEFAULT_ADMIN', True)
        if should_create_default_admin and not User.objects.filter(is_superuser=True).exists():
            initial_password = get_random_string(24)
            User.objects.create_superuser('admin', 'admin@example.com', initial_password)
            app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
            credentials_file = app_dir / 'INITIAL_ADMIN_CREDENTIALS.txt'
            credentials_file.write_text(
                f"Username: admin\nPassword: {initial_password}\n",
                encoding='utf-8',
            )
            print(f"[+] Save the one-time admin credentials from {credentials_file}")
        elif not should_create_default_admin:
            print("[*] Skipping default admin creation because CREATE_DEFAULT_ADMIN is disabled.")
        return True
    except Exception as e:
        print(f"[!] Warning during database setup: {e}")
        return False

def find_free_port(start_port=8000):
    """Find an available TCP port starting from start_port."""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port available for ERP application.")

def run_server(application, host, port):
    global http_server
    try:
        from waitress import serve
        serve(application, host=host, port=port, threads=8, _quiet=True)
    except ImportError:
        http_server = make_server(host, port, application, server_class=ThreadedWSGIServer, handler_class=QuietHandler)
        http_server.serve_forever()

def main():
    if not ensure_database_ready():
        print("[*] Startup aborted. Please switch to PostgreSQL for the tenant-enabled ERP setup.")
        return
    port = find_free_port()
    lan_ip = get_lan_ip()
    os.environ['LAN_IP'] = lan_ip
    if lan_ip not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append(lan_ip)
    trusted_origin = f'http://{lan_ip}'
    if trusted_origin not in settings.CSRF_TRUSTED_ORIGINS:
        settings.CSRF_TRUSTED_ORIGINS.append(trusted_origin)

    # The built-in launcher serves HTTP, so browsers must be allowed to send its cookies.
    settings.SESSION_COOKIE_SECURE = False
    settings.CSRF_COOKIE_SECURE = False
    application = get_wsgi_application()

    server_thread = threading.Thread(target=run_server, args=(application, '0.0.0.0', port), daemon=True)
    server_thread.start()

    local_url = f"http://127.0.0.1:{port}"
    network_url = f"http://{lan_ip}:{port}"
    print(f"[*] {settings.APP_NAME} server running!")
    print(f"    - Local URL:   {local_url}")
    print(f"    - Network URL: {network_url} (Use this link on other computers on your network)")

    try:
        webview_started = False
        try:
            import webview
            print("[*] Launching pywebview GUI window...")
            webview.create_window(
                title=f"{settings.APP_NAME} — Network URL: {network_url}",
                url=local_url,
                width=1366,
                height=768,
                min_size=(900, 600),
                resizable=True
            )
            webview.start()
            webview_started = True
        except Exception as e:
            print(f"[!] Native pywebview UI unavailable: {e}")

        # Fallback: Open system web browser automatically if webview window is unavailable
        if not webview_started:
            print(f"[*] Opening ERP system in your web browser: {local_url}")
            webbrowser.open(local_url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    finally:
        print("[*] Shutting down ERP server...")
        if http_server:
            try:
                http_server.shutdown()
            except Exception:
                pass

if __name__ == '__main__':
    main()
