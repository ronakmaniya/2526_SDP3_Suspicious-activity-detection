/**
 * LiveMonitor Component
 * Real-time CCTV monitoring with webcam capture at 24 FPS.
 * Sends frames to Django backend for AI analysis.
 * Draws bounding boxes on canvas overlay.
 */
import React, { useRef, useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { FiPlay, FiSquare, FiCamera, FiCircle, FiRefreshCw } from 'react-icons/fi';
import { analyzeFrame, startLiveSession, stopLiveSession } from '../services/api';

const TARGET_FPS = 24;
const JPEG_QUALITY = 0.5;  // Lower quality = smaller payload = faster transfer

function LiveMonitor() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [recordingId, setRecordingId] = useState(null);
  const [currentFps, setCurrentFps] = useState(0);
  const [detections, setDetections] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  const [frameCount, setFrameCount] = useState(0);
  const [timestamp, setTimestamp] = useState('');

  // Refs to always hold current recording/session state (avoids stale closures)
  const recordingIdRef = useRef(null);
  const sessionIdRef = useRef(null);
  const isRecordingRef = useRef(false);

  // Keep refs in sync with state
  useEffect(() => { recordingIdRef.current = recordingId; }, [recordingId]);
  useEffect(() => { sessionIdRef.current = sessionId; }, [sessionId]);
  useEffect(() => { isRecordingRef.current = isRecording; }, [isRecording]);

  // FPS counter
  const fpsCounterRef = useRef({ count: 0, lastTime: Date.now() });

  /**
   * Start webcam stream
   */
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: TARGET_FPS },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsStreaming(true);
      toast.success('Camera started');
      startProcessingLoop();
    } catch (err) {
      toast.error('Failed to access camera: ' + err.message);
      console.error('Camera error:', err);
    }
  }, []);

  /**
   * Stop webcam stream — also stops recording if active
   */
  const stopCamera = useCallback(async () => {
    // Stop any active recording first
    if (isRecordingRef.current && sessionIdRef.current) {
      try {
        await stopLiveSession(sessionIdRef.current, recordingIdRef.current);
        toast.info('Recording auto-saved');
      } catch (err) {
        console.warn('Failed to stop recording on camera stop:', err);
      }
      setSessionId(null);
      setRecordingId(null);
      setIsRecording(false);
    }

    if (intervalRef.current) {
      intervalRef.current.value = false;  // Signal the async loop to stop
      intervalRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    // Clear overlay canvas completely
    const overlay = overlayCanvasRef.current;
    if (overlay) {
      const ctx = overlay.getContext('2d');
      ctx.clearRect(0, 0, overlay.width, overlay.height);
      overlay.width = 0;
      overlay.height = 0;
    }

    setIsStreaming(false);
    setDetections([]);
    setTimestamp('');
    setCurrentFps(0);
    fpsCounterRef.current = { count: 0, lastTime: Date.now() };
    toast.info('Camera stopped');
  }, []);

  /**
   * Reset all session activity data for a fresh start
   */
  const resetSession = useCallback(() => {
    setDetections([]);
    setRecentEvents([]);
    setFrameCount(0);
    setTimestamp('');
    setCurrentFps(0);
    fpsCounterRef.current = { count: 0, lastTime: Date.now() };

    // Clear overlay canvas
    const overlay = overlayCanvasRef.current;
    if (overlay) {
      const ctx = overlay.getContext('2d');
      ctx.clearRect(0, 0, overlay.width, overlay.height);
    }

    toast.success('Session reset — activity cleared');
  }, []);

  /**
   * Start/Stop recording session
   */
  const toggleRecording = useCallback(async () => {
    try {
      if (!isRecording) {
        const result = await startLiveSession();
        setSessionId(result.session_id);
        setRecordingId(result.recording_id);
        setIsRecording(true);
        toast.success('Recording started');
      } else {
        if (sessionId) {
          await stopLiveSession(sessionId, recordingId);
        }
        setSessionId(null);
        setRecordingId(null);
        setIsRecording(false);
        toast.success('Recording saved');
      }
    } catch (err) {
      toast.error('Recording error: ' + err.message);
    }
  }, [isRecording, sessionId, recordingId]);

  /**
   * Main processing loop - captures frames and sends to backend SEQUENTIALLY.
   * Waits for backend response before sending the next frame.
   * Uses requestAnimationFrame for optimal browser scheduling.
   * Uses refs instead of state to always read the latest recording/session IDs.
   */
  const startProcessingLoop = useCallback(() => {
    if (intervalRef.current) return;

    // Flag to signal the loop to stop
    const running = { value: true };
    intervalRef.current = running;

    const processLoop = async () => {
      if (!running.value) return;

      if (!videoRef.current || !canvasRef.current) {
        if (running.value) requestAnimationFrame(processLoop);
        return;
      }

      try {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        const vw = video.videoWidth || 640;
        const vh = video.videoHeight || 480;
        canvas.width = vw;
        canvas.height = vh;

        ctx.drawImage(video, 0, 0, vw, vh);

        // Convert to base64 JPEG (lower quality for speed)
        const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
        // Strip the data URL prefix — saves bandwidth and backend parsing
        const frameBase64 = dataUrl.slice(dataUrl.indexOf(',') + 1);

        const currentRecordingId = recordingIdRef.current;
        const currentSessionId = sessionIdRef.current;

        // Send to backend and WAIT for response before sending next frame
        const result = await analyzeFrame(frameBase64, currentRecordingId, currentSessionId);

        // Update state with results
        setDetections(result.detections || []);
        setTimestamp(result.timestamp);
        setFrameCount((prev) => prev + 1);

        // Draw bounding boxes on overlay canvas
        drawOverlay(result.detections, result.timestamp, vw, vh);

        // Track suspicious events
        const suspicious = (result.detections || []).filter(
          (d) => d.activity_label === 'suspicious'
        );
        if (suspicious.length > 0) {
          setRecentEvents((prev) => [
            ...suspicious.map((d) => ({
              ...d,
              time: result.timestamp,
              id: Date.now() + Math.random(),
            })),
            ...prev,
          ].slice(0, 50));
        }

        // FPS counter
        fpsCounterRef.current.count++;
        const now = Date.now();
        if (now - fpsCounterRef.current.lastTime >= 1000) {
          setCurrentFps(fpsCounterRef.current.count);
          fpsCounterRef.current.count = 0;
          fpsCounterRef.current.lastTime = now;
        }
      } catch (err) {
        console.warn('Frame processing error:', err.message);
      }

      // Schedule next frame (sequential — only after this frame is done)
      if (running.value) {
        requestAnimationFrame(processLoop);
      }
    };

    // Start the loop
    requestAnimationFrame(processLoop);
  }, []); // No dependencies — uses refs for mutable state

  /**
   * Draw bounding boxes and labels on the overlay canvas.
   * Computes scale factors if the overlay CSS size differs from the
   * internal resolution so that boxes align with the video exactly.
   */
  const drawOverlay = (detections, timestamp, width, height) => {
    const overlay = overlayCanvasRef.current;
    if (!overlay) return;

    // Set internal resolution to match video (only if changed)
    if (overlay.width !== width || overlay.height !== height) {
      overlay.width = width;
      overlay.height = height;
    }

    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, width, height);

    // Draw each detection
    (detections || []).forEach((det) => {
      const [x1, y1, x2, y2] = det.bbox;
      const isSuspicious = det.activity_label === 'suspicious';

      // Box color: red for suspicious, green for normal
      const color = isSuspicious ? '#ff1744' : '#00e676';
      const glowColor = isSuspicious ? 'rgba(255,23,68,0.35)' : 'rgba(0,230,118,0.25)';

      // Glow effect
      ctx.shadowColor = glowColor;
      ctx.shadowBlur = 8;

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      // Reset shadow for labels
      ctx.shadowBlur = 0;

      // Corner decorations (tactical HUD style)
      const cornerLen = Math.min(16, (x2 - x1) * 0.15, (y2 - y1) * 0.15);
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      // Top-left
      ctx.beginPath(); ctx.moveTo(x1, y1 + cornerLen); ctx.lineTo(x1, y1); ctx.lineTo(x1 + cornerLen, y1); ctx.stroke();
      // Top-right
      ctx.beginPath(); ctx.moveTo(x2 - cornerLen, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1 + cornerLen); ctx.stroke();
      // Bottom-left
      ctx.beginPath(); ctx.moveTo(x1, y2 - cornerLen); ctx.lineTo(x1, y2); ctx.lineTo(x1 + cornerLen, y2); ctx.stroke();
      // Bottom-right
      ctx.beginPath(); ctx.moveTo(x2 - cornerLen, y2); ctx.lineTo(x2, y2); ctx.lineTo(x2, y2 - cornerLen); ctx.stroke();

      // Label — show status + confidence at top of box
      const label = `${det.activity_label.toUpperCase()} ${(det.activity_confidence * 100).toFixed(0)}%`;
      ctx.font = 'bold 12px monospace';
      const textWidth = ctx.measureText(label).width;

      // Label background
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.9;
      ctx.fillRect(x1, y1 - 20, textWidth + 10, 20);
      ctx.globalAlpha = 1.0;

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x1 + 5, y1 - 6);

      // Activity name tag at bottom-left corner of bounding box
      const activityName = det.activity || det.activity_label || '';
      if (activityName && activityName !== 'unknown') {
        ctx.font = 'bold 11px monospace';
        const actWidth = ctx.measureText(activityName).width;
        ctx.fillStyle = isSuspicious ? 'rgba(255,23,68,0.85)' : 'rgba(0,0,0,0.7)';
        ctx.fillRect(x1, y2, actWidth + 10, 18);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(activityName, x1 + 5, y2 + 13);
      }

      // Person ID tag on right side
      if (det.person_id) {
        const idLabel = det.person_id;
        ctx.font = '10px monospace';
        const idWidth = ctx.measureText(idLabel).width;
        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        ctx.fillRect(x2 - idWidth - 8, y2 - 16, idWidth + 8, 16);
        ctx.fillStyle = '#ccc';
        ctx.fillText(idLabel, x2 - idWidth - 4, y2 - 4);
      }
    });

    // Timestamp overlay (top-right)
    if (timestamp) {
      const tsText = `LIVE | ${timestamp}`;
      ctx.font = 'bold 14px monospace';
      const tsWidth = ctx.measureText(tsText).width;

      ctx.fillStyle = 'rgba(0,0,0,0.75)';
      ctx.fillRect(width - tsWidth - 20, 6, tsWidth + 16, 24);

      ctx.fillStyle = '#ffffff';
      ctx.fillText(tsText, width - tsWidth - 12, 22);

      // Live dot
      ctx.beginPath();
      ctx.arc(width - tsWidth - 30, 18, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ff1744';
      ctx.fill();
    }

    // Detection count (bottom-left)
    const count = (detections || []).length;
    const countText = `Persons: ${count}`;
    ctx.font = '12px monospace';
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    const cw = ctx.measureText(countText).width;
    ctx.fillRect(6, height - 24, cw + 12, 20);
    ctx.fillStyle = count > 0 ? '#00e676' : '#888';
    ctx.fillText(countText, 12, height - 10);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        intervalRef.current.value = false;  // Signal the async loop to stop
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return (
    <div>
      <h1 className="page-title">Live CCTV Monitor</h1>

      <div className="dashboard-grid">
        {/* Video Feed */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Camera Feed</span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {currentFps} FPS | Frame #{frameCount}
            </span>
          </div>

          <div className="video-container">
            <video
              ref={videoRef}
              style={{ display: isStreaming ? 'block' : 'none' }}
              muted
              playsInline
            />
            {isStreaming && (
              <canvas ref={overlayCanvasRef} className="overlay-canvas" />
            )}
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {!isStreaming && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--text-muted)',
                flexDirection: 'column',
                gap: '1rem',
              }}>
                <FiCamera size={48} />
                <p>Click "Start Camera" to begin monitoring</p>
              </div>
            )}

            {isRecording && (
              <div className="video-status">
                <span className="recording-indicator"></span>
                REC
              </div>
            )}

            {isStreaming && timestamp && (
              <div className="video-overlay">{timestamp}</div>
            )}
          </div>

          <div className="controls-bar">
            {!isStreaming ? (
              <button className="btn btn-primary" onClick={startCamera}>
                <FiPlay /> Start Camera
              </button>
            ) : (
              <button className="btn btn-danger" onClick={stopCamera}>
                <FiSquare /> Stop Camera
              </button>
            )}

            <button
              className={`btn ${isRecording ? 'btn-danger' : 'btn-success'}`}
              onClick={toggleRecording}
              disabled={!isStreaming}
            >
              <FiCircle />
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </button>

            <button
              className="btn btn-outline"
              onClick={resetSession}
              title="Clear all detection history and start fresh"
            >
              <FiRefreshCw /> Reset Session
            </button>
          </div>
        </div>

        {/* Detection Sidebar */}
        <div>
          {/* Current Detections */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header">
              <span className="card-title">Active Detections</span>
              <span className="log-badge normal">{detections.length} persons</span>
            </div>

            {detections.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
                No humans detected
              </p>
            ) : (
              detections.map((det, idx) => (
                <div key={idx} className="log-entry">
                  <span className={`log-badge ${det.activity_label}`}>
                    {det.activity_label}
                  </span>
                  <span className="log-confidence" style={{ flex: 1, textAlign: 'left', marginLeft: '0.5rem', fontSize: '0.8rem' }}>
                    {det.activity || det.activity_label}
                  </span>
                  <span className="log-confidence">
                    {(det.activity_confidence * 100).toFixed(1)}%
                  </span>
                  <span className="log-time">{det.person_id}</span>
                </div>
              ))
            )}
          </div>

          {/* Recent Suspicious Events */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Suspicious Events</span>
              <span className="log-badge suspicious">{recentEvents.length}</span>
            </div>

            <div className="detection-log">
              {recentEvents.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
                  No suspicious activity detected
                </p>
              ) : (
                recentEvents.slice(0, 20).map((evt) => (
                  <div key={evt.id} className="log-entry">
                    <span className="log-badge suspicious">ALERT</span>
                    <span className="log-confidence">
                      {(evt.activity_confidence * 100).toFixed(1)}%
                    </span>
                    <span className="log-time">{evt.time}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LiveMonitor;
