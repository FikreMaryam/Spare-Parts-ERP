import os
import sys
import subprocess
import threading
import time
import webview

# Set the working directory to the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Add the current directory to Python path
sys.path.insert(0, script_dir)

# Setup Django
import django
django.setup()

def run_server():
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000', '--noreload'])

# Start server in a thread
server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# Wait for server to start
time.sleep(3)

# Create webview window
webview.create_window('ERP for My Shop', 'http://127.0.0.1:8000', width=1200, height=800)
webview.start()