# 🛡️ Real-Time AI-Based Suspicious Activity Detection System

A professional-grade CCTV surveillance system that detects human presence, classifies activity as **Normal** or **Suspicious** in real-time at **24 FPS**, and stores annotated video recordings with bounding boxes and timestamps.

---

## 🏗️ Architecture

```
CCTV Camera / Webcam
       ↓
React Frontend (24 FPS Capture)
       ↓
Django REST API
       ↓
YOLOv8x → Human Detection
       ↓
Video Swin Transformer → Activity Classification
       ↓
Bounding Box + Timestamp Overlay
       ↓
Return Prediction to Frontend
       ↓
Store Processed MP4 Video + Log Events
```

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite |
| Backend | Django 4.2 + Django REST Framework |
| Human Detection | YOLOv8x (Ultralytics) |
| Activity Classification | Video Swin Transformer |
| Video Processing | OpenCV + FFmpeg |
| Training | PyTorch + Kaggle T4 GPU |
| Deployment | Docker + Gunicorn + Nginx |

---

## 📁 Project Structure

```
├── backend/                     # Django backend
│   ├── detection/               # Main detection app
│   │   ├── ai_engine/           # AI models & pipeline
│   │   │   ├── human_detector.py       # YOLOv8x wrapper
│   │   │   ├── activity_classifier.py  # Video Swin model
│   │   │   ├── pipeline.py             # Main processing pipeline
│   │   │   └── video_processor.py      # Video read/write/processing
│   │   ├── models.py            # Database models
│   │   ├── serializers.py       # DRF serializers
│   │   ├── views.py             # API endpoints
│   │   └── urls.py              # URL routing
│   ├── surveillance_backend/    # Django project config
│   ├── requirements.txt
│   ├── manage.py
│   └── Dockerfile
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveMonitor.jsx  # Real-time camera monitoring
│   │   │   ├── VideoUpload.jsx  # Video upload & processing
│   │   │   ├── Dashboard.jsx    # System dashboard & stats
│   │   │   └── Recordings.jsx   # Recording history
│   │   ├── services/
│   │   │   └── api.js           # API service layer
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── training/                    # Model training scripts
│   ├── train_model.py           # Video Swin training script
│   ├── prepare_dataset.py       # Dataset preparation utility
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- CUDA-compatible GPU (recommended)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend runs on http://localhost:3000 and proxies API calls to http://localhost:8000.

### 3. Docker (Full Stack)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/

---

## 🧠 Training the Video Swin Model

### 1. Prepare Dataset

Organize raw videos into `normal/` and `suspicious/` folders:

```bash
python training/prepare_dataset.py \
    --input_dir /path/to/raw_videos \
    --output_dir /path/to/dataset \
    --target_fps 8 \
    --val_split 0.2
```

### 2. Train on Kaggle (T4 x2 GPU)

```bash
python training/train_model.py \
    --data_dir /path/to/dataset \
    --epochs 30 \
    --batch_size 8 \
    --lr 1e-4
```

### 3. Deploy Trained Model

Copy the trained `video_swin_model.pth` to:
```
backend/ai_models/video_swin_model.pth
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze-frame/` | Analyze a single frame (base64) |
| POST | `/api/live-session/` | Start/stop live recording session |
| GET | `/api/live-session/` | List active sessions |
| POST | `/api/upload-video/` | Upload video for processing |
| GET | `/api/recordings/` | List all recordings |
| GET | `/api/recordings/{id}/` | Get recording details |
| GET | `/api/recordings/{id}/download/` | Download processed video |
| GET | `/api/events/` | List detection events |
| GET | `/api/stats/` | System statistics |
| GET | `/api/health/` | Health check |

---

## 🎯 Features

- **Real-time 24 FPS** processing with webcam
- **YOLOv8x** human detection with high accuracy
- **Video Swin Transformer** activity classification (Normal/Suspicious)
- **Green bounding boxes** for normal activity
- **Red bounding boxes** for suspicious activity
- **Timestamp overlay** on live display and stored video
- **MP4 video storage** with full annotations (boxes + labels + timestamps)
- **Video upload** mode for offline analysis
- **Event logging** with confidence scores to database
- **Dashboard** with real-time statistics

---

## 📊 Performance Targets

| Metric | Target |
|---|---|
| Processing FPS | 24 FPS |
| Detection delay | ≤ 1.5 seconds |
| API response | < 500ms |
| YOLO accuracy | ≥ 95% |
| Activity classification | ≥ 90% |
| System uptime | ≥ 95% |

---

## 📝 License

This project is for educational and research purposes.
