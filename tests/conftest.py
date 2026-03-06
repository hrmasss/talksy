"""Pytest configuration – adds src/backend to sys.path so ``app`` is importable."""

import sys
from pathlib import Path

# Ensure `import app.*` resolves to src/backend/app
_backend = Path(__file__).resolve().parent.parent / "src" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
