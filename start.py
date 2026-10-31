import os
import shutil
import signal
import subprocess
import sys
import time
from urllib.request import urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT


def find_python_in_venv() -> str:
    if os.name == "nt":
        candidate = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = BACKEND_DIR / ".venv" / "bin" / "python"

    if candidate.exists():
        return str(candidate)

    return shutil.which("python") or shutil.which("python3") or sys.executable


def ensure_backend_dependencies() -> None:
    python_path = find_python_in_venv()
    requirements = BACKEND_DIR / "requirements.txt"
    if requirements.exists():
        try:
            subprocess.run(
                [python_path, "-m", "pip", "install", "-r", str(requirements)],
                cwd=str(BACKEND_DIR),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            print("Backend dependency install failed. Please install requirements manually.")


def ensure_frontend_dependencies() -> None:
    if (FRONTEND_DIR / "node_modules").exists():
        return
    try:
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True)
    except subprocess.CalledProcessError:
        print("Frontend dependency install failed. Please run 'npm install' manually.")


def start_backend() -> subprocess.Popen:
    python_path = find_python_in_venv()
    cmd = [python_path, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    print(f"Starting backend: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(BACKEND_DIR))


def start_frontend() -> subprocess.Popen:
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    cmd = [npm_command, "run", "dev", "--", "--host", "0.0.0.0"]
    print(f"Starting frontend: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(FRONTEND_DIR))


def service_is_running(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return 200 <= response.status < 500
    except OSError:
        return False


def shutdown(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            if os.name == "nt":
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    ensure_backend_dependencies()
    ensure_frontend_dependencies()

    processes: list[subprocess.Popen] = []

    if service_is_running("http://localhost:8000/health"):
        print("Backend is already running on http://localhost:8000")
        backend = None
    else:
        backend = start_backend()
        processes.append(backend)

    if service_is_running("http://localhost:5173/"):
        print("Frontend is already running on http://localhost:5173")
        frontend = None
    else:
        try:
            frontend = start_frontend()
            processes.append(frontend)
        except OSError:
            shutdown(processes)
            raise

    print("Open http://localhost:5173 in your browser. Press Ctrl+C to stop processes started by this script.")

    try:
        while True:
            for process, label in [(backend, "backend"), (frontend, "frontend")]:
                if process is not None and process.poll() is not None:
                    print(f"{label} exited unexpectedly with code {process.returncode}")
                    shutdown(processes)
                    return process.returncode

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down frontend and backend...")
        shutdown(processes)
        return 0


if __name__ == "__main__":
    sys.exit(main())
