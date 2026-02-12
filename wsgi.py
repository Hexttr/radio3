"""WSGI entry point for gunicorn/uWSGI."""
from src.main import create_app

app = create_app()
