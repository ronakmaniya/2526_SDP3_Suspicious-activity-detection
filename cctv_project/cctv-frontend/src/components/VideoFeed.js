import React, { useState, useEffect, useCallback, useRef } from 'react';
import './VideoFeed.css';

function VideoFeed({ videoRef, recordingCanvasRef, isStreaming, isRecording, detections, activityStatus }) {
  const [videoRect, setVideoRect] = useState(null);
  const recalcIntervalRef = useRef(null);

  // Calculate the actual video display area within the container
  const calculateVideoRect = useCallback(() => {
    const video = videoRef?.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      console.log('VideoFeed: Video not ready for rect calculation');
      return;
    }

    const container = video.parentElement;
    if (!container) return;

    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    if (containerWidth === 0 || containerHeight === 0) {
      console.log('VideoFeed: Container has zero dimensions');
      return;
    }

    const videoAspect = video.videoWidth / video.videoHeight;
    const containerAspect = containerWidth / containerHeight;

    let displayWidth, displayHeight, offsetX, offsetY;

    // object-fit: contain keeps aspect ratio and fits inside container
    if (videoAspect > containerAspect) {
      // Video is wider than container - letterbox top/bottom
      displayWidth = containerWidth;
      displayHeight = containerWidth / videoAspect;
      offsetX = 0;
      offsetY = (containerHeight - displayHeight) / 2;
    } else {
      // Video is taller than container - letterbox left/right
      displayHeight = containerHeight;
      displayWidth = containerHeight * videoAspect;
      offsetX = (containerWidth - displayWidth) / 2;
      offsetY = 0;
    }

    console.log('VideoFeed: Calculated videoRect', { offsetX, offsetY, width: displayWidth, height: displayHeight });
    setVideoRect({
      offsetX,
      offsetY,
      width: displayWidth,
      height: displayHeight
    });
  }, [videoRef]);

  // Recalculate on video metadata load, resize, and when streaming starts
  useEffect(() => {
    const video = videoRef?.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      console.log('VideoFeed: loadedmetadata event');
      calculateVideoRect();
    };
    const handlePlaying = () => {
      console.log('VideoFeed: playing event');
      calculateVideoRect();
    };
    const handleResize = () => calculateVideoRect();

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('playing', handlePlaying);
    video.addEventListener('canplay', handlePlaying);
    window.addEventListener('resize', handleResize);

    // When streaming starts, recalculate periodically until we get valid dimensions
    if (isStreaming) {
      recalcIntervalRef.current = setInterval(() => {
        if (video.videoWidth && video.videoHeight) {
          calculateVideoRect();
          clearInterval(recalcIntervalRef.current);
        }
      }, 100);
      
      // Also try immediately
      if (video.videoWidth && video.videoHeight) {
        calculateVideoRect();
      }
    }

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('playing', handlePlaying);
      video.removeEventListener('canplay', handlePlaying);
      window.removeEventListener('resize', handleResize);
      if (recalcIntervalRef.current) {
        clearInterval(recalcIntervalRef.current);
      }
    };
  }, [videoRef, calculateVideoRect, isStreaming]);

  // Convert detection percentage coordinates to actual pixel positions
  const getBoxStyle = (detection) => {
    // Debug log
    console.log('VideoFeed: getBoxStyle', { detection, videoRect });
    
    if (!videoRect || !videoRect.width || !videoRect.height) {
      // Fallback: use percentage directly (works if video fills container)
      console.log('VideoFeed: Using percentage fallback for box positioning');
      return {
        left: `${detection.x}%`,
        top: `${detection.y}%`,
        width: `${detection.width}%`,
        height: `${detection.height}%`,
        zIndex: 10
      };
    }

    // Calculate pixel position within the actual video display area
    const left = videoRect.offsetX + (detection.x / 100) * videoRect.width;
    const top = videoRect.offsetY + (detection.y / 100) * videoRect.height;
    const width = (detection.width / 100) * videoRect.width;
    const height = (detection.height / 100) * videoRect.height;

    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
      zIndex: 10
    };
  };

  return (
    <div className={`video-container ${activityStatus}`}>
      <div className="video-wrapper">
        {!isStreaming && (
          <div className="video-placeholder">
            <div className="placeholder-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <rect x="3" y="6" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="2"/>
              </svg>
            </div>
            <h3>Camera Feed Offline</h3>
            <p>Click "Start Camera" to begin surveillance</p>
          </div>
        )}
        
        <video 
          ref={videoRef}
          autoPlay 
          playsInline 
          muted
          className={isStreaming ? 'active' : ''}
        />

        <canvas ref={recordingCanvasRef} className="recording-canvas" />
        
        {/* Detection Bounding Boxes */}
        {isStreaming && detections && detections.length > 0 && detections.map(detection => (
          <div
            key={detection.id}
            className={`detection-box ${detection.status || 'normal'}`}
            style={getBoxStyle(detection)}
          >
            <span className="detection-label">
              {detection.status === 'suspicious' ? '⚠️ Suspicious' : '✓ Normal'}
              <span className="confidence">{Math.round(detection.confidence || 0)}%</span>
            </span>
          </div>
        ))}
        
        {/* Corner Brackets */}
        {isStreaming && (
          <>
            <div className="corner corner-tl"></div>
            <div className="corner corner-tr"></div>
            <div className="corner corner-bl"></div>
            <div className="corner corner-br"></div>
          </>
        )}
        
        {/* Recording Indicator */}
        {isStreaming && isRecording && (
          <div className="recording-badge">
            <span className="rec-dot"></span>
            REC
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoFeed;
