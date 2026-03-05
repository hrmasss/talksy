"""
Talksy Development Server

Runs both the API backend and frontend dev server concurrently.
"""

import os
import subprocess
import sys
import signal
from pathlib import Path


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
    
    try:
        # Start backend
        backend_cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", api_port,
            "--reload",
        ]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=backend_dir,
            env=env,
        )
        processes.append(backend_proc)
        
        # Start frontend
        frontend_cmd = ["pnpm", "dev"]
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=frontend_dir,
            env=env,
            shell=True,
        )
        processes.append(frontend_proc)
        
        # Wait for processes
        for proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        print("\n\nShutting down servers...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()
        print("All servers stopped.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
