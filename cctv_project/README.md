# CCTV Project (React + Django)

This repo contains:
- React frontend: `cctv-frontend/`
- Django backend API: `backend/`

## One-command dev (Windows)

From this folder (`cctv_project/`):

- PowerShell: `./run_dev.ps1`
- CMD: `run_dev.bat`

Alternative (single command from backend folder):
- `cd backend`
- `python manage.py runserver`

Backend only:
- `python manage.py runserver --noreact`

This launches **two terminals**:
- Django at `http://127.0.0.1:8000`
- React at `http://localhost:3000`

## Manual dev

### Backend

- `cd backend`
- `python -m venv .venv`
- `.\.venv\Scripts\Activate.ps1`
- `pip install -r requirements.txt`
- `python manage.py migrate`
- `python manage.py runserver 127.0.0.1:8000`

### Frontend

- `cd cctv-frontend`
- `npm install`
- `npm start`

## Frontend → Backend URL

React reads `REACT_APP_API_BASE_URL` (see `cctv-frontend/.env.example`).
Default is `http://127.0.0.1:8000`.
