"""
Talksy Development Server

Runs both the API backend and frontend dev server concurrently.
"""

import os
import subprocess
import sys
import socket
import time
import shutil
from contextlib import closing
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def is_port_in_use(host: str, port: int) -> bool:
    """Check whether a TCP port is already bound."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def backend_is_healthy(port: int) -> bool:
    """Check whether an existing backend on the configured port is healthy."""
    try:
        with urlopen(f"http://127.0.0.1:{port}/health/live", timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def stop_process(proc: subprocess.Popen) -> None:
    """Terminate a subprocess if it's still running."""
    if proc.poll() is not None:
        return

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def find_preferred_executable(root_dir: Path, name: str) -> str | None:
    """Prefer repo-local virtualenv executables before falling back to PATH."""
    candidates = [
        root_dir / ".venv" / "Scripts" / f"{name}.exe",
        root_dir / ".venv" / "bin" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def main():
    """Run development servers."""
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "src" / "backend"
    frontend_dir = root_dir / "src" / "web"
    
    # Load environment variables
    env = os.environ.copy()
    env_file = root_dir / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    
    api_port = env.get("PORT", "8000")
    api_port_int = int(api_port)

    venv_scripts = root_dir / ".venv" / "Scripts"
    venv_bin = root_dir / ".venv" / "bin"
    if venv_scripts.exists():
        env["PATH"] = f"{venv_scripts}{os.pathsep}{env.get('PATH', '')}"
    elif venv_bin.exists():
        env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    
    # Set PYTHONPATH so imports work correctly
    env["PYTHONPATH"] = str(backend_dir)
    
    print("\n" + "=" * 50)
    print("  Talksy Development Server")
    print("=" * 50)
    print(f"\n  API:      http://localhost:{api_port}")
    print("  Frontend: http://localhost:5173")
    print("\n  Press Ctrl+C to stop all servers")
    print("=" * 50 + "\n")
    
    processes = []
    backend_proc = None
    frontend_proc = None
    backend_started = False
    
    try:
        if is_port_in_use("127.0.0.1", api_port_int):
            if backend_is_healthy(api_port_int):
                print(f"Backend already running on http://localhost:{api_port}; reusing existing instance.")
            else:
                print(
                    f"Port {api_port} is already in use, but no healthy Talksy backend responded on /health/live."
                )
                print("Stop the process using that port or change PORT before starting the dev server.")
                return 1
        else:
            granian_cmd = find_preferred_executable(root_dir, "granian")
            uvicorn_cmd = find_preferred_executable(root_dir, "uvicorn")

            if granian_cmd:
                backend_cmd = [
                    granian_cmd,
                    "app.main:app",
                    "--interface", "asgi",
                    "--host", "0.0.0.0",
                    "--port", api_port,
                    "--loop", "auto" if sys.platform == "win32" else "uvloop",
                    "--reload",
                    "--reload-paths", str(backend_dir / "app"),
                    "--reload-ignore-patterns", r".*\\.(sqlite|db|wal|shm)$",
                ]
                print("Starting backend with Granian.")
            elif uvicorn_cmd:
                backend_cmd = [
                    uvicorn_cmd,
                    "app.main:app",
                    "--host", "0.0.0.0",
                    "--port", api_port,
                    "--reload",
                    "--reload-dir", str(backend_dir / "app"),
                ]
                print("Granian not found; starting backend with Uvicorn instead.")
            else:
                print("Neither 'granian' nor 'uvicorn' is installed in the current environment.")
                print("Install project dependencies first, then rerun the dev server.")
                return 1

            backend_proc = subprocess.Popen(
                backend_cmd,
                cwd=backend_dir,
                env=env,
            )
            processes.append(backend_proc)
            backend_started = True
        
        # Start frontend
        frontend_cmd = ["pnpm", "dev"]
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=frontend_dir,
            env=env,
            shell=True,
        )
        processes.append(frontend_proc)
        
        # Keep the frontend and backend lifecycles in sync so failures are obvious.
        while processes:
            for proc in list(processes):
                return_code = proc.poll()
                if return_code is None:
                    continue

                processes.remove(proc)
                if return_code == 0:
                    continue

                role = "backend" if proc is backend_proc and backend_started else "frontend"
                print(f"\n{role.capitalize()} process exited with code {return_code}.")
                for other_proc in processes:
                    stop_process(other_proc)
                return return_code

            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nShutting down servers...")
        for proc in processes:
            stop_process(proc)
        print("All servers stopped.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
