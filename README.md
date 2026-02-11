# Suspicious Activity Detection (CCTV) — React + Django

End-to-end suspicious activity detection demo for a CCTV-style web UI.

- **Frontend**: React (live camera feed UI, bounding boxes, alerts, recording)
- **Backend**: Django + Django REST Framework (API + model inference endpoints)
- **AI**:
  - **YOLO (Ultralytics)** for **human detection** (`/api/detect/`)
  - **Activity classifier** endpoint (`/api/classify/`) backed by a fine-tuned YOLO model downloaded from Hugging Face by default

The actual app lives under [cctv_project/](cctv_project/).

## Features

- Live webcam feed in the browser
- Real-time human detection with bounding boxes
- Activity classification (normal vs suspicious) and alerts
- Optional recording with timestamp overlay + upload to backend
- Simple REST API consumed by the React UI

## Repo layout

- [cctv_project/backend/](cctv_project/backend/) — Django backend API
- [cctv_project/cctv-frontend/](cctv_project/cctv-frontend/) — React frontend

## Prerequisites

- **Windows 10/11** (this repo includes Windows-first instructions)
- **Python**: 3.10+ recommended (Django 4.2+)
- **Node.js**: 18+ recommended (for the React dev server)

AI dependencies are heavier:

- CPU works, but **GPU (CUDA)** improves inference speed if available.
- Installing **torch** can be slow; use the official PyTorch install instructions if pip struggles.

## Quick start (Windows)

### Option A: one command dev (recommended)

This project is wired so **running Django can also start React** automatically.

1. Backend venv + deps

```powershell
cd cctv_project\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

2. Start dev servers

```powershell
python manage.py runserver
```

This starts:

- Django: `http://127.0.0.1:8000`
- React: `http://127.0.0.1:3000` (or a nearby port if 3000 is busy)

To run **backend only**:

```powershell
python manage.py runserver --noreact
```

### Option B: run with the custom `dev` management command

```powershell
cd cctv_project\backend
.\.venv\Scripts\Activate.ps1
python manage.py dev
```

### Option C: manual frontend + backend

Backend:

```powershell
cd cctv_project\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Frontend:

```powershell
cd cctv_project\cctv-frontend
npm install
npm start
```

## Configuration

### Frontend → Backend base URL

The frontend reads `REACT_APP_API_BASE_URL`.

- Example file: [cctv_project/cctv-frontend/.env.example](cctv_project/cctv-frontend/.env.example)
- Default if not set: `http://127.0.0.1:8000`

### Activity model configuration

The backend uses `VIDEOMAE_MODEL_DIR` (despite the name, it currently points to a YOLO weights source) to locate/download the activity model used by `/api/classify/`.

- Defined in: [cctv_project/backend/cctv_backend/settings.py](cctv_project/backend/cctv_backend/settings.py)
- Default: `Accurateinfosolution/Suspicious_activity_detection_Yolov11_Custom` (Hugging Face repo)

You can override it:

```powershell
$env:VIDEOMAE_MODEL_DIR = "path\\to\\weights_or_folder"
# or a HF repo id like "owner/repo"
python manage.py runserver
```

Note: downloading from Hugging Face requires internet access, and the backend may need `huggingface_hub` installed if it is not already available in your environment.

## API endpoints

Base path: `http://127.0.0.1:8000/api/`

### Health

- `GET /api/health/` → `{ "status": "ok" }`

### Session (UI control)

- `POST /api/session/start/` → start session
- `POST /api/session/stop/` → stop session
- `POST /api/session/reset/` → clear state
- `GET /api/state/` → returns current `activityStatus`, `detections`, `alerts`, `stats`

### Recordings

- `GET /api/recordings/` → list uploaded recordings
- `POST /api/recordings/upload/` → multipart upload
  - form field: `file`
  - optional: `startedAt`, `endedAt`

Files are saved under the backend media directory (defaults to `cctv_project/backend/recordings/`).

### AI inference

- `POST /api/detect/` → YOLO human detection
  - JSON: `{ "image": "data:image/jpeg;base64,...", "confidence": 0.2 }`
- `POST /api/classify/` → activity classification
  - JSON: `{ "frames": ["data:image/jpeg;base64,..."], "numFrames": 16 }`

## How it works (high level)

- The React app captures frames from the webcam periodically.
- It calls `/api/detect/` to get **person bounding boxes**.
- It buffers recent frames and calls `/api/classify/` every ~2 seconds.
- The UI combines detection + classification to color boxes and raise alerts.

## Troubleshooting

- **React doesn’t start when running Django**: ensure Node.js + `npm` are installed, then try `cd cctv_project\cctv-frontend; npm install` once.
- **Port 3000 busy**: the backend auto-selects a nearby port; check the terminal output.
- **Torch/Transformers install issues**: install PyTorch first (official instructions), then run `pip install -r requirements.txt` again.
- **CORS**: the backend is configured for development and allows localhost origins broadly.

## More docs

- Project dev notes: [cctv_project/README.md](cctv_project/README.md)
- Backend details: [cctv_project/backend/README.md](cctv_project/backend/README.md)
