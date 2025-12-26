#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

Project behavior tweak (dev convenience):
- Running `python manage.py runserver` will ALSO start the React dev server.
- Use `python manage.py runserver --noreact` to run only Django.
"""

import os
import shutil
import signal
import subprocess
import sys
import socket
from pathlib import Path


def _find_available_port(start_port: int) -> int:
    port = start_port
    while port < start_port + 50:
        # On Windows, attempting to bind with SO_REUSEADDR can yield false positives.
        # Use connect_ex against localhost instead: if something is listening, port is taken.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            result = s.connect_ex(('127.0.0.1', port))
            if result != 0:
                return port
        port += 1
    return start_port


def _maybe_start_react_dev_server(argv: list[str]) -> subprocess.Popen | None:
    if len(argv) < 2 or argv[1] != 'runserver':
        return None

    # Manage.py-only flag; strip it so Django doesn't error.
    normalized = [a.strip().lower() for a in argv]
    noreact_flags = {'--noreact', '--no-react', '--no_react', '/noreact'}
    if any(a in noreact_flags for a in normalized):
        # Persist across Django autoreload (child process inherits env, not our mutated argv).
        os.environ['DJANGO_NOREACT'] = '1'
        argv[:] = [a for a in argv if a.strip().lower() not in noreact_flags]
        print('[manage.py] --noreact set; skipping React dev server.')
        return None

    if os.environ.get('DJANGO_NOREACT', '').strip() == '1':
        return None

    # Only start React in the Django autoreload child process (prevents duplicates).
    if os.environ.get('RUN_MAIN') != 'true' and '--noreload' not in normalized:
        return None

    backend_dir = Path(__file__).resolve().parent
    frontend_dir = backend_dir.parent / 'cctv-frontend'
    if not frontend_dir.exists():
        return None

    npm_exe = shutil.which('npm')
    if not npm_exe:
        return None

    env = os.environ.copy()
    env.setdefault('BROWSER', 'none')
    # Ensure dev server binds locally (reduces surprises on Windows).
    env.setdefault('HOST', '127.0.0.1')

    start_port = int(os.environ.get('FRONTEND_PORT', '3000'))
    port = _find_available_port(start_port)
    env['PORT'] = str(port)
    if port != start_port:
        print(f"[manage.py] Port {start_port} is busy; starting React on {port} instead.")

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    return subprocess.Popen(
        [npm_exe, 'start'],
        cwd=str(frontend_dir),
        env=env,
        shell=False,
        creationflags=creationflags,
    )


def main() -> None:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cctv_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable? "
            "Did you forget to activate a virtual environment?"
        ) from exc

    react_proc = None
    try:
        react_proc = _maybe_start_react_dev_server(sys.argv)
        execute_from_command_line(sys.argv)
    finally:
        if react_proc is not None and react_proc.poll() is None:
            try:
                if os.name == 'nt':
                    react_proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    react_proc.send_signal(signal.SIGINT)
            except Exception:
                pass
            try:
                react_proc.terminate()
            except Exception:
                pass


if __name__ == '__main__':
    main()
