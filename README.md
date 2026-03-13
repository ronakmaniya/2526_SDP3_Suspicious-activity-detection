<div align="center">

# 🛡️ Real-Time AI-Based Suspicious Activity Detection System

**An intelligent CCTV surveillance platform that detects human presence and classifies activity as Normal or Suspicious in real-time using deep learning.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Docker Deployment](#-docker-deployment)
- [API Reference](#-api-reference)
- [AI Pipeline](#-ai-pipeline)
- [Model Training](#-model-training)
- [Environment Variables](#-environment-variables)
- [Performance](#-performance)
- [Troubleshooting](#-troubleshooting)
- [Team](#-team)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

This system provides an end-to-end solution for real-time surveillance and suspicious activity detection. It combines a **React 18** frontend with a **Django REST** backend, powered by two deep learning models working in tandem:

1. **YOLOv8** — Real-time human detection with bounding boxes
2. **SlowFast-R101** — Temporal activity classification using a 32-frame sliding window

### Key Features

| Feature | Description |
|---------|-------------|
| 🎥 **Live Monitoring** | Real-time webcam feed with AI-powered analysis at 24 FPS |
| 🧠 **Dual-Model Pipeline** | YOLOv8 detection + SlowFast-R101 classification |
| 🟢🔴 **Visual Alerts** | Green bounding boxes (normal) / Red bounding boxes (suspicious) |
| 📹 **Video Upload** | Upload pre-recorded videos for offline analysis |
| 💾 **Recording Storage** | Annotated MP4 recordings with bounding boxes & timestamps |
| 📊 **Analytics Dashboard** | Real-time statistics, event history, and confidence metrics |
| ⚡ **Optimized Inference** | Frame skipping, classifier cooldown, and temporal smoothing |
| 🐳 **Docker Support** | One-command deployment with Docker Compose |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐  │
│  │Dashboard │ │  Live    │ │  Video    │ │  Recordings  │  │
│  │          │ │ Monitor  │ │  Upload   │ │              │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────────┘  │
│                        │ Axios REST API                      │
└────────────────────────┼────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Django REST API    │
              │   (DRF + CORS)      │
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
   ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
   │  YOLOv8   │  │ SlowFast  │  │  Video    │
   │  Human    │  │   R101    │  │ Processor │
   │ Detector  │  │ Classifier│  │ (OpenCV)  │
   └───────────┘  └───────────┘  └───────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
              ┌──────────▼──────────┐
              │  SQLite Database +   │
              │  Media Storage       │
              └─────────────────────┘
```

---

## 🔧 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite 5 | SPA with real-time camera integration |
| **UI Libraries** | React Router, React Toastify, React Icons | Navigation, notifications, iconography |
| **Backend** | Django 4.2 + Django REST Framework | RESTful API server |
| **Human Detection** | YOLOv8 (Ultralytics) | Real-time person detection |
| **Activity Classification** | SlowFast-R101 (PyTorchVideo) | Temporal action recognition (Kinetics-400) |
| **Video Processing** | OpenCV + FFmpeg | Frame capture, annotation, encoding |
| **Training** | PyTorch + TensorBoard | Model fine-tuning on custom data |
| **Deployment** | Docker + Gunicorn + Nginx | Production-ready containerization |
| **Database** | SQLite (dev) | Event logging and recording metadata |

---

## 📁 Project Structure

```
suspicious activity detection/
│
├── backend/                          # Django REST API
│   ├── detection/                    # Main detection app
│   │   ├── ai_engine/               # AI models & processing pipeline
│   │   │   ├── human_detector.py    # YOLOv8 wrapper for person detection
│   │   │   ├── activity_classifier.py  # SlowFast-R101 action classifier
│   │   │   ├── pipeline.py          # Orchestration: detection → classification → annotation
│   │   │   └── video_processor.py   # Video I/O, stream management, encoding
│   │   ├── models.py               # DetectionEvent & VideoRecording models
│   │   ├── serializers.py          # DRF serializers for API I/O
│   │   ├── views.py                # API endpoint handlers
│   │   └── urls.py                 # URL routing
│   ├── surveillance_backend/        # Django project settings
│   ├── ai_models/                   # Model weights directory (.gitkeep)
│   ├── requirements.txt
│   ├── manage.py
│   └── Dockerfile
│
├── frontend/                        # React SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx        # System overview & real-time stats
│   │   │   ├── LiveMonitor.jsx      # Webcam feed with AI overlay
│   │   │   ├── VideoUpload.jsx      # Drag-and-drop video analysis
│   │   │   └── Recordings.jsx       # History & playback of recordings
│   │   ├── services/
│   │   │   └── api.js              # Axios API client
│   │   ├── App.jsx                 # Root component & routing
│   │   └── main.jsx                # Entry point
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf                   # Production Nginx config
│   └── Dockerfile
│
├── training/                        # Model training scripts
│   ├── train_model.py              # SlowFast-R101 fine-tuning (Kaggle T4 GPU)
│   ├── prepare_dataset.py          # Video → frame extraction utility
│   └── requirements.txt
│
├── pytorchvideo-main/               # PyTorchVideo library (SlowFast models)
├── docker-compose.yml               # Full-stack Docker orchestration
├── start.py                         # One-command dev server launcher
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.10+ | Backend & AI models |
| Node.js | 18+ | Frontend dev server |
| CUDA (optional) | 11.8+ | GPU acceleration for inference |

### Option 1: One-Command Start (Recommended)

```bash
cd "suspicious activity detection"
python start.py
```

This launches both servers simultaneously:
- **Backend:** http://127.0.0.1:8000
- **Frontend:** http://localhost:3000

### Option 2: Manual Setup

#### Backend

```bash
cd "suspicious activity detection/backend"

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Start the API server
python manage.py runserver 8000
```

#### Frontend

```bash
cd "suspicious activity detection/frontend"

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend runs on http://localhost:3000 and proxies API calls to http://localhost:8000.

---

## 🐳 Docker Deployment

Deploy the full stack with a single command:

```bash
cd "suspicious activity detection"
docker-compose up --build
```

| Service | URL | Container |
|---------|-----|-----------|
| Frontend | http://localhost:3000 | `surveillance-frontend` |
| Backend API | http://localhost:8000/api/ | `surveillance-backend` |

The Docker setup uses **Gunicorn** (backend) and **Nginx** (frontend) for production-grade serving.

---

## 📡 API Reference

**Base URL:** `http://localhost:8000/api/`

### AI Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze-frame/` | Analyze a single base64-encoded frame through the full AI pipeline |
| `POST` | `/api/upload-video/` | Upload a video file for offline processing |
| `POST` | `/api/live-session/` | Start or stop a live recording session |
| `GET`  | `/api/live-session/` | List active live sessions |

### Data & Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/recordings/` | List all video recordings with metadata |
| `GET` | `/api/recordings/{id}/` | Get recording details |
| `GET` | `/api/recordings/{id}/download/` | Download processed video with annotations |
| `GET` | `/api/events/` | List detection events (filterable by label, date) |
| `GET` | `/api/stats/` | System statistics (counts, averages, uptime) |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health/` | Health check → `{ "status": "ok" }` |

### Example: Analyze a Frame

```bash
curl -X POST http://localhost:8000/api/analyze-frame/ \
  -H "Content-Type: application/json" \
  -d '{"frame": "data:image/jpeg;base64,/9j/4AAQ..."}'
```

**Response:**
```json
{
  "detections": [
    {
      "bbox": [120, 80, 340, 460],
      "confidence": 0.92,
      "activity_label": "suspicious",
      "activity_confidence": 0.87
    }
  ],
  "frame_number": 142,
  "timestamp": "2026-02-18T14:30:00Z"
}
```

---

## 🧠 AI Pipeline

### How It Works

```
Webcam Frame (24 FPS)
       │
       ▼
┌──────────────────┐
│  YOLOv8 Detector │──── Runs every 3rd frame (frame skipping)
│  (Person boxes)  │     Reuses cached detections on skipped frames
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  32-Frame Sliding│──── Maintains per-person frame buffer
│     Window       │     Early classification at 16+ frames
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   SlowFast-R101  │──── Dual-pathway temporal model
│  (Normal / Susp) │     8-frame slow + 32-frame fast pathway
└────────┬─────────┘     Cooldown: re-classifies every 8 frames
         │
         ▼
┌──────────────────┐
│ Temporal Smoothing│──── EMA probability (α=0.55) + majority vote (window=3)
│  (Stable Labels)  │    Prevents label flickering
└────────┬──────────┘
         │
         ▼
   Final Prediction
  (label + confidence)
```

### Performance Optimizations

| Optimization | Description | Impact |
|-------------|-------------|--------|
| **Frame Skipping** | YOLO runs every Nth frame (default: 3) | ~3x throughput |
| **Classifier Cooldown** | SlowFast re-classifies every 8 frames | Reduces GPU load |
| **Temporal Smoothing** | EMA + majority vote over recent predictions | Stable labels |
| **Configurable Resolution** | YOLO input size adjustable (default: 320px) | Speed vs accuracy trade-off |

### Model Details

| Model | Architecture | Pretrained On | Task |
|-------|-------------|---------------|------|
| **YOLOv8n** | Ultralytics YOLOv8-Nano | COCO (80 classes) | Person detection (class 0) |
| **SlowFast-R101** | ResNet-101 + dual pathway | Kinetics-400 (400 actions) | Binary activity classification |

> **Note:** YOLOv8 model weights auto-download on first run. SlowFast-R101 loads from PyTorchVideo's model hub.

---

## 🏋️ Model Training

### 1. Prepare Dataset

Organize raw videos into `normal/` and `suspicious/` categories:

```bash
python training/prepare_dataset.py \
    --input_dir /path/to/raw_videos \
    --output_dir /path/to/dataset \
    --target_fps 8 \
    --val_split 0.2
```

**Expected input:**
```
raw_videos/
├── normal/
│   ├── video1.mp4
│   └── video2.mp4
└── suspicious/
    ├── video1.mp4
    └── video2.mp4
```

### 2. Train the Model

Fine-tune SlowFast-R101 on your custom dataset (designed for Kaggle T4 GPU):

```bash
cd training
pip install -r requirements.txt

python train_model.py \
    --data_dir /path/to/dataset \
    --epochs 30 \
    --batch_size 4 \
    --lr 1e-4
```

Training progress is logged to **TensorBoard**:

```bash
tensorboard --logdir runs/
```

### 3. Deploy Trained Model

Copy the trained weights to the backend:

```bash
cp trained_model.pth "suspicious activity detection/backend/ai_models/"
```

---

## ⚙️ Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Auto-generated | Django secret key (change in production) |
| `DJANGO_DEBUG` | `True` | Debug mode toggle |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | YOLO model weights path |
| `YOLO_IMGSZ` | `320` | YOLO input image size (pixels) |
| `YOLO_CONFIDENCE` | `0.4` | Minimum detection confidence |
| `ACTIVITY_CONFIDENCE` | `0.6` | Minimum classification confidence |
| `DETECT_EVERY_N` | `3` | Run detection every N frames |
| `CLASSIFY_COOLDOWN` | `8` | Re-classify every N frames |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

> See `.env.example` files in `backend/` and `frontend/` for templates.

---

## 📊 Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Processing FPS | 24 FPS | With frame skipping enabled |
| Detection Latency | ≤ 1.5s | YOLOv8n at 320px input |
| API Response Time | < 500ms | Single frame analysis |
| YOLO Accuracy | ≥ 95% | Person detection (COCO pretrained) |
| Classification Accuracy | ≥ 90% | Normal vs Suspicious (fine-tuned) |

> GPU (CUDA) significantly improves inference speed. CPU mode works but with reduced FPS.

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **PyTorch installation fails** | Install PyTorch first from [pytorch.org](https://pytorch.org/get-started/locally/), then run `pip install -r requirements.txt` |
| **CUDA not detected** | Ensure NVIDIA drivers + CUDA toolkit are installed; install the CUDA version of PyTorch |
| **Frontend can't reach API** | Check that the backend is running on port 8000; verify `VITE_API_BASE_URL` in `.env` |
| **Port 3000 already in use** | Kill the process using the port or change the Vite port in `vite.config.js` |
| **CORS errors in browser** | The backend allows `localhost:3000` and `localhost:5173` by default; add your origin to `CORS_ALLOWED_ORIGINS` in `settings.py` |
| **Model weights not found** | YOLOv8 auto-downloads on first run; ensure internet access or manually place weights in `backend/` |
| **Out of memory (GPU)** | Reduce `YOLO_IMGSZ`, increase `DETECT_EVERY_N`, or switch to CPU mode |

---

## 👥 Team

<table align="center">
  <tr>
    <td align="center">
      <a href="https://github.com/apurv9090">
        <img src="https://github.com/apurv9090.png" width="120px;" alt="Apoorv Jadav" style="border-radius:50%"/><br />
        <sub><b>Apoorv Jadav</b></sub>
      </a><br />
      <a href="https://github.com/apurv9090">🔗 GitHub</a>
    </td>
    <td align="center">
      <a href="https://github.com/ronakmaniya">
        <img src="https://github.com/ronakmaniya.png" width="120px;" alt="Ronak Maniya" style="border-radius:50%"/><br />
        <sub><b>Ronak Maniya</b></sub>
      </a><br />
      <a href="https://github.com/ronakmaniya">🔗 GitHub</a>
    </td>
  </tr>
</table>

**Project Guide:** Prof. Hariom Pandya

### Task Distribution

| Area | Apoorv Jadav | Ronak Maniya |
|------|-------------|-------------|
| **AI Engine & Detection Pipeline** | YOLOv8 human detection, SlowFast-R101 activity classifier, surveillance pipeline orchestration, temporal smoothing & frame optimization | — |
| **Backend API & Database** | — | Django REST API, database models, serializers, API views & URL routing, video processing endpoints |
| **Frontend Development** | React dashboard, live monitoring component with webcam integration | Video upload component, recordings page, API service layer |
| **Model Training** | Training pipeline (`train_model.py`), SlowFast-R101 fine-tuning, TensorBoard integration | Dataset preparation (`prepare_dataset.py`), video-to-frame extraction, data augmentation |
| **DevOps & Deployment** | Backend Dockerfile, Gunicorn configuration | Frontend Dockerfile, Nginx configuration, Docker Compose orchestration |
| **Documentation & Testing** | SRS document, project structure documentation | README, API documentation, system testing |
| **Integration** | PyTorchVideo library integration, model weight management | Frontend-backend integration, CORS configuration, environment setup |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📝 License

This project is developed for **educational and research purposes** as part of the **System Design Practice (SDP)** coursework (Group 3) at **Dharmsinh Desai University**, Faculty of Technology, B.Tech in Computer Engineering (6th Semester).

---

<div align="center">

**Built with ❤️ by Apoorv Jadav & Ronak Maniya**

**B.Tech Computer Engineering, 3rd Year — Dharmsinh Desai University**

**Guided by Prof. Hariom Pandya**

</div>
