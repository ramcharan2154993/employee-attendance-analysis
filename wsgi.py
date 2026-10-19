"""WSGI entrypoint for production hosting (PythonAnywhere, Gunicorn, Waitress)."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded
project_root = Path(__file__).resolve().parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

from src.web import create_app

# Expose WSGI application object
application = create_app()
app = application  # Alias for hosts or runners expecting `app`

if __name__ == "__main__":
    application.run(host="127.0.0.1", port=5000, debug=False)
