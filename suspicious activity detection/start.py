"""
Start both Django backend and React frontend with a single command.
Usage: python start.py
"""
import subprocess
import sys
import os
import signal
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')
FRONTEND_DIR = os.path.join(ROOT_DIR, 'frontend')


def main():
    processes = []

    try:
        # Start Django backend
        print("[*] Starting Django backend on http://127.0.0.1:8000 ...")
        backend = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver'],
            cwd=BACKEND_DIR,
        )
        processes.append(backend)
        time.sleep(1)

        # Start React frontend
        print("[*] Starting React frontend on http://localhost:3000 ...")
        frontend = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=FRONTEND_DIR,
            shell=True,
        )
        processes.append(frontend)

        print("\n" + "=" * 50)
        print("  AI Surveillance System Running")
        print("  Backend:  http://127.0.0.1:8000")
        print("  Frontend: http://localhost:3000")
        print("  Press Ctrl+C to stop both servers")
        print("=" * 50 + "\n")

        # Wait for either process to exit
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
        print("[*] All servers stopped.")


if __name__ == '__main__':
    main()
