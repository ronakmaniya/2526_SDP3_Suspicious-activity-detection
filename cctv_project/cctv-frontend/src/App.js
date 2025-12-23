import React, { useState, useRef, useCallback, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import VideoFeed from './components/VideoFeed';
import StatusIndicator from './components/StatusIndicator';
import ControlPanel from './components/ControlPanel';
import AlertDisplay from './components/AlertDisplay';
import StatsPanel from './components/StatsPanel';

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
  const uptimeRef = useRef(null);

  // Simulate random detections for demo
  const simulateDetection = useCallback(() => {
    if (!isStreaming) return;

    const isSuspicious = Math.random() < 0.15; // 15% chance of suspicious
    const newStatus = isSuspicious ? 'suspicious' : 'normal';
    
    // Generate random bounding box position
    const newDetection = {
      id: Date.now(),
      x: Math.random() * 60 + 10, // 10-70%
      y: Math.random() * 50 + 10, // 10-60%
      width: Math.random() * 15 + 15, // 15-30%
      height: Math.random() * 20 + 25, // 25-45%
      status: newStatus,
      confidence: (Math.random() * 20 + 80).toFixed(1) // 80-100%
    };

    setDetections(prev => {
      const updated = [...prev, newDetection].slice(-3); // Keep max 3 detections
      return updated;
    });

    setActivityStatus(newStatus);

    setStats(prev => ({
      ...prev,
      totalDetections: prev.totalDetections + 1,
      normalCount: prev.normalCount + (newStatus === 'normal' ? 1 : 0),
      suspiciousCount: prev.suspiciousCount + (newStatus === 'suspicious' ? 1 : 0)
    }));

    if (isSuspicious) {
      const newAlert = {
        id: Date.now(),
        message: '⚠️ Suspicious Activity Detected!',
        time: new Date().toLocaleTimeString(),
        confidence: newDetection.confidence
      };
      setAlerts(prev => [newAlert, ...prev].slice(0, 5));
    }
  }, [isStreaming]);

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
        setIsStreaming(true);
        setActivityStatus('normal');

        // Start detection simulation
        intervalRef.current = setInterval(simulateDetection, 2000);

        // Start uptime counter
        uptimeRef.current = setInterval(() => {
          setStats(prev => ({ ...prev, uptime: prev.uptime + 1 }));
        }, 1000);
      }
    } catch (error) {
      console.error('Camera access error:', error);
      alert('Unable to access camera. Please check permissions.');
    }
  };

  // Stop camera stream
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    if (uptimeRef.current) {
      clearInterval(uptimeRef.current);
    }
    setIsStreaming(false);
    setActivityStatus('idle');
    setDetections([]);
  };

  // Reset everything
  const resetView = () => {
    stopCamera();
    setAlerts([]);
    setStats({
      totalDetections: 0,
      normalCount: 0,
      suspiciousCount: 0,
      uptime: 0
    });
  };

  // Dismiss alert
  const dismissAlert = (id) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id));
  };

  // Update detection simulation when streaming changes
  useEffect(() => {
    if (isStreaming && !intervalRef.current) {
      intervalRef.current = setInterval(simulateDetection, 2000);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isStreaming, simulateDetection]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="app">
      <Header />
      
      <main className="main-content">
        <div className="dashboard-grid">
          <div className="video-section">
            <VideoFeed 
              videoRef={videoRef}
              isStreaming={isStreaming}
              detections={detections}
              activityStatus={activityStatus}
            />
            <StatusIndicator status={activityStatus} />
            <ControlPanel 
              isStreaming={isStreaming}
              onStart={startCamera}
              onStop={stopCamera}
              onReset={resetView}
            />
          </div>
          
          <div className="side-panel">
            <StatsPanel stats={stats} isStreaming={isStreaming} />
            <AlertDisplay alerts={alerts} onDismiss={dismissAlert} />
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
