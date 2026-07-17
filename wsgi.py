"""WSGI entry point for production servers.

PythonAnywhere: point the WSGI config at this file (it imports `application`).
gunicorn: `gunicorn wsgi:application`.
"""
from app import app as application  # noqa: F401
