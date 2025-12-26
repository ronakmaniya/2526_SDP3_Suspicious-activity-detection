import React, { useState, useRef, useCallback, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import VideoFeed from './components/VideoFeed';
import StatusIndicator from './components/StatusIndicator';
import ControlPanel from './components/ControlPanel';
import AlertDisplay from './components/AlertDisplay';
import StatsPanel from './components/StatsPanel';
import { apiGetState, apiSessionReset, apiSessionStart, apiSessionStop, apiUploadRecording, apiDetectHumans } from './api';

function App() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [activityStatus, setActivityStatus] = useState('idle'); // idle, normal, suspicious
  const [alerts, setAlerts] = useState([]);
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState({
    totalDetections: 0,
    normalCount: 0,
    suspiciousCount: 0,
    uptime: 0
  });
  
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const isFetchingRef = useRef(false);
  const detectionIntervalRef = useRef(null);
  const detectionCanvasRef = useRef(null);

  const recordingCanvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaRecorderChunksRef = useRef([]);
  const drawRafRef = useRef(null);
  const recordingStartedAtMsRef = useRef(null);
  const startRecordingRef = useRef(null);
  const detectionsRef = useRef([]);

  const [isRecording, setIsRecording] = useState(false);
  const [recordingUploadState, setRecordingUploadState] = useState('idle'); // idle | uploading | uploaded | error
  const [recordingUploadError, setRecordingUploadError] = useState(null);

  // Capture frame from video and send to YOLO detection
  const captureAndDetect = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !video.srcObject) return;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    console.log('Capturing frame for detection...', video.videoWidth, 'x', video.videoHeight);

    // Create or reuse canvas for frame capture
    if (!detectionCanvasRef.current) {
      detectionCanvasRef.current = document.createElement('canvas');
    }
    const canvas = detectionCanvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    // Convert to base64
    const imageBase64 = canvas.toDataURL('image/jpeg', 0.8);
    console.log('Sending frame to backend, size:', imageBase64.length);
    
    try {
      const result = await apiDetectHumans(imageBase64, 0.5);
      console.log('Detection result:', result);
      if (result.success && result.detections) {
        // Analyze detections for suspicious activity
        // Suspicious criteria: multiple people, unusual positions, rapid movements
        const detectionsWithStatus = result.detections.map((det, idx) => {
          // Simple suspicious activity detection logic:
          // - More than 3 people detected = suspicious
          // - Person at edge of frame (possible intrusion) = suspicious
          // - Very high confidence rapid detection = suspicious
          let status = 'normal';
          
          const isAtEdge = det.x < 5 || det.x + det.width > 95 || det.y < 5;
          const multiplePeople = result.detections.length > 3;
          const largePresence = det.width > 40 || det.height > 60;
          
          if (multiplePeople || (isAtEdge && det.confidence > 70) || largePresence) {
            status = 'suspicious';
          }
          
          return { ...det, status };
        });
        
        setDetections(detectionsWithStatus);
        detectionsRef.current = detectionsWithStatus;
        
        // Check if any detection is suspicious
        const hasSuspicious = detectionsWithStatus.some(d => d.status === 'suspicious');
        
        // Update stats
        setStats(prev => ({
          ...prev,
          totalDetections: prev.totalDetections + detectionsWithStatus.length,
          normalCount: prev.normalCount + detectionsWithStatus.filter(d => d.status === 'normal').length,
          suspiciousCount: prev.suspiciousCount + detectionsWithStatus.filter(d => d.status === 'suspicious').length
        }));
        
        // Set activity status based on detections
        if (detectionsWithStatus.length > 0) {
          setActivityStatus(hasSuspicious ? 'suspicious' : 'normal');
          
          // Create alert for suspicious activity
          if (hasSuspicious) {
            const newAlert = {
              id: `alert_${Date.now()}`,
              message: `Suspicious activity detected - ${detectionsWithStatus.filter(d => d.status === 'suspicious').length} person(s)`,
              time: new Date().toLocaleTimeString(),
              confidence: Math.round(detectionsWithStatus.filter(d => d.status === 'suspicious')[0]?.confidence || 0)
            };
            setAlerts(prev => [newAlert, ...prev].slice(0, 50));
          }
        } else {
          setActivityStatus('idle');
        }
      }
    } catch (error) {
      console.error('Detection error:', error);
    }
  }, [isStreaming]);

  const fetchBackendState = useCallback(async () => {
    if (!isStreaming || isFetchingRef.current) return;
    isFetchingRef.current = true;
    try {
      const state = await apiGetState();
      // Only update alerts from backend, detections come from YOLO
      setAlerts(Array.isArray(state.alerts) ? state.alerts : []);
      if (state.stats?.uptime) {
        setStats(prev => ({ ...prev, uptime: state.stats.uptime }));
      }
    } catch (error) {
      console.error('Backend state fetch error:', error);
    } finally {
      isFetchingRef.current = false;
    }
  }, [isStreaming]);

  const stopDrawingOverlay = useCallback(() => {
    if (drawRafRef.current) {
      cancelAnimationFrame(drawRafRef.current);
      drawRafRef.current = null;
    }
  }, []);

  const formatElapsed = (elapsedMs) => {
    const totalSeconds = Math.max(0, Math.floor(elapsedMs / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const pad2 = (n) => String(n).padStart(2, '0');
    if (hours > 0) return `${hours}:${pad2(minutes)}:${pad2(seconds)}`;
    return `${pad2(minutes)}:${pad2(seconds)}`;
  };

  const formatLocalDateTime = (date) => {
    const pad2 = (n) => String(n).padStart(2, '0');
    const y = date.getFullYear();
    const m = pad2(date.getMonth() + 1);
    const d = pad2(date.getDate());
    const hh = pad2(date.getHours());
    const mm = pad2(date.getMinutes());
    const ss = pad2(date.getSeconds());
    return `${y}-${m}-${d} ${hh}:${mm}:${ss}`;
  };

  const ensureVideoReady = async (videoEl) => {
    if (!videoEl) return;
    if (videoEl.videoWidth && videoEl.videoHeight && videoEl.readyState >= 2) return;

    await new Promise((resolve) => {
      const checkReady = () => {
        if (videoEl.videoWidth && videoEl.videoHeight && videoEl.readyState >= 2) {
          resolve();
          return;
        }
        // Try again shortly
        setTimeout(checkReady, 50);
      };
      checkReady();
    });
  };

  const startDrawingOverlay = useCallback(async () => {
    const videoEl = videoRef.current;
    const canvasEl = recordingCanvasRef.current;
    if (!videoEl || !canvasEl) return;

    await ensureVideoReady(videoEl);

    const width = videoEl.videoWidth || 1280;
    const height = videoEl.videoHeight || 720;
    if (canvasEl.width !== width) canvasEl.width = width;
    if (canvasEl.height !== height) canvasEl.height = height;

    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      // If recording stopped, stop scheduling frames.
      if (!recordingStartedAtMsRef.current) {
        drawRafRef.current = null;
        return;
      }

      const now = new Date();
      const elapsedMs = Date.now() - recordingStartedAtMsRef.current;

      ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);

      // Overlay text (burned into the recording)
      const padding = Math.max(12, Math.floor(canvasEl.width * 0.015));
      const fontSize = Math.max(18, Math.floor(canvasEl.width * 0.02));

      ctx.font = `bold ${fontSize}px Arial`;
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.75)';
      ctx.lineWidth = Math.max(3, Math.floor(fontSize * 0.18));

      const dtText = `DATE/TIME: ${formatLocalDateTime(now)}`;
      const elapsedText = `ELAPSED: ${formatElapsed(elapsedMs)}`;

      ctx.strokeText(dtText, padding, padding);
      ctx.fillText(dtText, padding, padding);

      ctx.strokeText(elapsedText, padding, padding + fontSize + 8);
      ctx.fillText(elapsedText, padding, padding + fontSize + 8);

      // Draw detection boxes on recording
      const currentDetections = detectionsRef.current || [];
      currentDetections.forEach(det => {
        const boxX = (det.x / 100) * canvasEl.width;
        const boxY = (det.y / 100) * canvasEl.height;
        const boxW = (det.width / 100) * canvasEl.width;
        const boxH = (det.height / 100) * canvasEl.height;
        
        // Set color based on status
        const isNormal = det.status === 'normal';
        const boxColor = isNormal ? '#22c55e' : '#ef4444'; // Green for normal, Red for suspicious
        const bgColor = isNormal ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)';
        
        // Draw box background
        ctx.fillStyle = bgColor;
        ctx.fillRect(boxX, boxY, boxW, boxH);
        
        // Draw box border
        ctx.strokeStyle = boxColor;
        ctx.lineWidth = 3;
        ctx.strokeRect(boxX, boxY, boxW, boxH);
        
        // Draw label background
        const labelText = isNormal ? `✓ Normal ${det.confidence}%` : `⚠ Suspicious ${det.confidence}%`;
        const labelFontSize = Math.max(14, Math.floor(canvasEl.width * 0.015));
        ctx.font = `bold ${labelFontSize}px Arial`;
        const labelWidth = ctx.measureText(labelText).width + 12;
        const labelHeight = labelFontSize + 8;
        
        ctx.fillStyle = boxColor;
        ctx.fillRect(boxX, boxY - labelHeight - 2, labelWidth, labelHeight);
        
        // Draw label text
        ctx.fillStyle = 'white';
        ctx.textBaseline = 'middle';
        ctx.fillText(labelText, boxX + 6, boxY - labelHeight/2 - 2);
      });

      drawRafRef.current = requestAnimationFrame(draw);
    };

    stopDrawingOverlay();
    drawRafRef.current = requestAnimationFrame(draw);
  }, [stopDrawingOverlay]);

  const pickRecorderMimeType = () => {
    const candidates = [
      'video/mp4;codecs=avc1',
      'video/mp4;codecs=h264',
      'video/mp4',
      'video/webm;codecs=vp9',
      'video/webm;codecs=vp8',
      'video/webm'
    ];
    if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return null;
    for (const t of candidates) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return null;
  };

  const startRecording = useCallback(async () => {
    if (!isStreaming || isRecording) return;

    const canvasEl = recordingCanvasRef.current;
    const videoEl = videoRef.current;
    if (!canvasEl || !videoEl) {
      console.error('Recording canvas or video ref not ready');
      alert('Recording is not ready yet. Try again.');
      return;
    }

    if (typeof MediaRecorder === 'undefined') {
      alert('Your browser does not support MediaRecorder recording.');
      return;
    }

    // Set recording start time BEFORE starting the overlay
    const startTime = Date.now();
    recordingStartedAtMsRef.current = startTime;

    setRecordingUploadState('idle');
    setRecordingUploadError(null);
    setIsRecording(true);

    try {
      await startDrawingOverlay();
    } catch (err) {
      console.error('Failed to start overlay:', err);
    }

    const mimeType = pickRecorderMimeType();
    let stream;
    try {
      stream = canvasEl.captureStream(30);
    } catch (err) {
      console.error('captureStream failed:', err);
      alert('Failed to capture canvas stream. Recording not supported in this browser.');
      setIsRecording(false);
      recordingStartedAtMsRef.current = null;
      return;
    }

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    console.log('MediaRecorder created:', recorder.state, 'mimeType:', recorder.mimeType);

    mediaRecorderChunksRef.current = [];
    recorder.ondataavailable = (e) => {
      console.log('Recording chunk received:', e.data?.size, 'bytes');
      if (e.data && e.data.size > 0) {
        mediaRecorderChunksRef.current.push(e.data);
      }
    };

    recorder.onerror = (e) => {
      console.error('MediaRecorder error:', e);
      setRecordingUploadState('error');
      setRecordingUploadError('Recording failed.');
    };

    recorder.onstop = async () => {
      console.log('MediaRecorder stopped, processing...');
      try {
        const chunks = mediaRecorderChunksRef.current;
        console.log('Chunks to upload:', chunks.length, 'total size:', chunks.reduce((a, b) => a + b.size, 0));
        if (!chunks || chunks.length === 0) {
          console.warn('No recording data available');
          setRecordingUploadState('error');
          setRecordingUploadError('No recording data captured.');
          return;
        }
        const blob = new Blob(chunks, { type: recorder.mimeType || 'video/webm' });
        console.log('Blob created:', blob.size, 'bytes');

        setRecordingUploadState('uploading');
        const startedAt = new Date(startTime).toISOString();
        const endedAt = new Date().toISOString();
        console.log('Uploading recording...');
        await apiUploadRecording(blob, { startedAt, endedAt });
        console.log('Upload complete!');
        setRecordingUploadState('uploaded');
      } catch (error) {
        console.error('Recording upload error:', error);
        setRecordingUploadState('error');
        setRecordingUploadError(error?.message || 'Upload failed.');
      } finally {
        // cleanup canvas stream tracks
        try {
          stream.getTracks().forEach((t) => t.stop());
        } catch (_) {
          // ignore
        }
      }
    };

    mediaRecorderRef.current = recorder;
    recorder.start(1000);
    console.log('Recording started, recorder state:', recorder.state, 'canvas:', canvasEl.width, 'x', canvasEl.height);
  }, [isStreaming, isRecording, startDrawingOverlay]);

  // Keep startRecordingRef in sync with the latest startRecording function
  useEffect(() => {
    startRecordingRef.current = startRecording;
  }, [startRecording]);

  const stopRecording = useCallback(() => {
    if (!isRecording) return;
    console.log('Stopping recording, chunks collected:', mediaRecorderChunksRef.current.length);
    setIsRecording(false);
    stopDrawingOverlay();

    recordingStartedAtMsRef.current = null;
    const recorder = mediaRecorderRef.current;
    mediaRecorderRef.current = null;

    try {
      if (recorder && recorder.state !== 'inactive') {
        recorder.stop();
      }
    } catch (error) {
      console.error('Error stopping recorder:', error);
    }
  }, [isRecording, stopDrawingOverlay]);

  // Start camera stream
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;

        // Start backend session (simulation/data processing lives in Django)
        try {
          await apiSessionStart();
        } catch (error) {
          console.error('Backend session start error:', error);
        }

        setIsStreaming(true);
        // Let backend drive alerts/uptime
        intervalRef.current = setInterval(fetchBackendState, 2000);
        fetchBackendState();

        // Start YOLO human detection every 500ms
        detectionIntervalRef.current = setInterval(() => {
          captureAndDetect();
        }, 500);

        // Auto-start recording when camera starts
        // Small delay to ensure video is ready
        setTimeout(() => {
          startRecordingRef.current?.();
        }, 500);
      }
    } catch (error) {
      console.error('Camera access error:', error);
      alert('Unable to access camera. Please check permissions.');
    }
  };

  // Stop camera stream
  const stopCamera = async () => {
    if (isRecording) {
      stopRecording();
    }
    // Stop detection interval
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
      detectionIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    try {
      await apiSessionStop();
    } catch (error) {
      console.error('Backend session stop error:', error);
    }

    setIsStreaming(false);
    setActivityStatus('idle');
    setDetections([]);
  };

  // Reset everything
  const resetView = async () => {
    await stopCamera();
    try {
      await apiSessionReset();
    } catch (error) {
      console.error('Backend session reset error:', error);
    }
    setAlerts([]);
    setStats({
      totalDetections: 0,
      normalCount: 0,
      suspiciousCount: 0,
      uptime: 0
    });
  };

  // Dismiss alert (frontend-only: hides it locally)
  const dismissAlert = (id) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id));
  };

  // Keep polling lifecycle aligned with streaming state
  useEffect(() => {
    if (isStreaming && !intervalRef.current) {
      intervalRef.current = setInterval(fetchBackendState, 2000);
      fetchBackendState();
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isStreaming, fetchBackendState]);

  // Cleanup on unmount
  useEffect(() => {
    const videoEl = videoRef.current;
    return () => {
      try {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
      } catch (_) {
        // ignore
      }
      stopDrawingOverlay();
      recordingStartedAtMsRef.current = null;

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoEl) {
        videoEl.srcObject = null;
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [stopDrawingOverlay]);

  return (
    <div className="app">
      <Header />
      
      <main className="main-content">
        <div className="dashboard-grid">
          <div className="video-section">
            <VideoFeed 
              videoRef={videoRef}
              recordingCanvasRef={recordingCanvasRef}
              isStreaming={isStreaming}
              isRecording={isRecording}
              detections={detections}
              activityStatus={activityStatus}
            />
            <StatusIndicator status={activityStatus} />
            <ControlPanel 
              isStreaming={isStreaming}
              onStart={startCamera}
              onStop={stopCamera}
              onReset={resetView}
              isRecording={isRecording}
              recordingUploadState={recordingUploadState}
              recordingUploadError={recordingUploadError}
            />
          </div>
          
          <div className="side-panel">
            <StatsPanel stats={stats} isStreaming={isStreaming} />
            <AlertDisplay alerts={alerts} onDismiss={dismissAlert} onClearAll={() => setAlerts([])} />
          </div>
        </div>
      </main>

      <footer className="footer">
        <p>🔒 CCTV Surveillance System • All feeds are processed locally • No data transmitted</p>
      </footer>
    </div>
  );
}

export default App;
