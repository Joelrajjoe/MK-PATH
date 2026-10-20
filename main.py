"""Root entrypoint for deployment platforms (Railway, Render, Fly.io, Heroku).

Provides the root-level 'app' instance so start commands like:
  uvicorn main:app --host 0.0.0.0 --port $PORT
or
  python main.py
work seamlessly out of the box.
"""
import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, app_dir=str(backend_dir))
