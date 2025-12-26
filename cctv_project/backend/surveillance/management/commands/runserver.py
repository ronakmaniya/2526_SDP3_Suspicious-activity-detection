"""Intentionally left blank.

We start the React dev server from `backend/manage.py` when running `python manage.py runserver`.
Keeping this file as a no-op avoids confusion if someone expects an app-level runserver override.
"""

from django.core.management.commands.runserver import Command as Command  # noqa: F401
