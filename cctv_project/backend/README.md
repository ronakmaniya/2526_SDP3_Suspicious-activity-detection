# Django Backend (API)

This backend owns the **data processing / simulation** layer and exposes a small REST API consumed by the React frontend.

## Endpoints

- `GET /api/health/` → health check
- `POST /api/session/start/` → start a session (enables simulation)
- `POST /api/session/stop/` → stop a session
- `POST /api/session/reset/` → reset stats/detections/alerts
- `GET /api/state/` → returns current `activityStatus`, `detections`, `alerts`, `stats`

## Run (Windows / PowerShell)

From `cctv_project/backend`:

1) Create and activate a virtualenv

- `python -m venv .venv`
- `.\.venv\Scripts\Activate.ps1`

2) Install deps

- `pip install -r requirements.txt`

3) Run migrations + start server

- `python manage.py migrate`
- `python manage.py runserver`

By default this starts:
- Django on `http://127.0.0.1:8000`
- React on `http://localhost:3000`

Backend only:
- `python manage.py runserver --noreact`

## Run frontend + backend (one command)

From `cctv_project/backend`:

- `python manage.py dev`

This starts:
- Django on `http://127.0.0.1:8000`
- React on `http://localhost:3000`

## React CORS

This backend allows `http://localhost:3000` by default (see `cctv_backend/settings.py`).
