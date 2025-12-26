import os
import shutil
import signal
import subprocess
from pathlib import Path

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Run Django backend and React frontend together (dev only)."

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', default='8000')
        parser.add_argument('--frontend-port', default='3000')

    def handle(self, *args, **options):
        host: str = options['host']
        port: str = str(options['port'])
        frontend_port: str = str(options['frontend_port'])

        backend_dir = Path(__file__).resolve().parents[4]  # backend/
        frontend_dir = backend_dir.parent / 'cctv-frontend'

        if not frontend_dir.exists():
            raise SystemExit(f"Frontend folder not found: {frontend_dir}")

        npm_exe = shutil.which('npm')
        if not npm_exe:
            raise SystemExit("npm not found. Install Node.js and ensure npm is on PATH.")

        env = os.environ.copy()
        env.setdefault('BROWSER', 'none')
        env['PORT'] = frontend_port

        self.stdout.write(self.style.SUCCESS(f"Starting React (PORT={frontend_port}) in {frontend_dir} ..."))
        react_proc = subprocess.Popen(
            [npm_exe, 'start'],
            cwd=str(frontend_dir),
            env=env,
            shell=False,
        )

        try:
            self.stdout.write(self.style.SUCCESS(f"Starting Django on http://{host}:{port} ..."))
            call_command('runserver', f'{host}:{port}')
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Stopping dev servers...'))
        finally:
            try:
                if react_proc.poll() is None:
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
