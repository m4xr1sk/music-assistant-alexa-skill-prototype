#!/usr/bin/env python3
"""Entrypoint that starts both the public (gunicorn) and admin (werkzeug) servers."""
import os
import sys
import signal
import subprocess
import threading

# Ensure the app source is on the Python path
sys.path.insert(0, os.path.dirname(__file__))


def run_admin():
    """Import and run the admin server directly."""
    from app import admin_app
    admin_port = int(os.environ.get('ADMIN_PORT', '5151'))
    print(f'[ADMIN] Starting admin server on port {admin_port} (local only)')
    admin_app.run(host='0.0.0.0', port=admin_port, debug=False, use_reloader=False)


def main():
    port = os.environ.get('PORT', '5150')

    # Start admin server in background thread
    admin_thread = threading.Thread(target=run_admin, daemon=True)
    admin_thread.start()

    # Start gunicorn for the public server as a subprocess
    print(f'[PUBLIC] Starting gunicorn on port {port}')
    
    # Ensure PYTHONPATH includes the current directory so gunicorn can find 'app:app'
    env = os.environ.copy()
    src_dir = os.path.dirname(os.path.abspath(__file__))
    current_pythonpath = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = f"{src_dir}:{current_pythonpath}" if current_pythonpath else src_dir

    gunicorn_cmd = [
        sys.executable, '-m', 'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '2',
        '--timeout', '30',
        '--access-logfile', '-',
        'app:app'
    ]
    proc = subprocess.Popen(gunicorn_cmd, env=env)

    # Forward signals to gunicorn
    def _forward(signum, frame):
        proc.send_signal(signum)

    signal.signal(signal.SIGTERM, _forward)
    signal.signal(signal.SIGINT, _forward)

    # Wait for gunicorn to exit
    sys.exit(proc.wait())


if __name__ == '__main__':
    main()
