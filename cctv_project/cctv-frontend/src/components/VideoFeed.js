import React from 'react';
import './VideoFeed.css';

function VideoFeed({ videoRef, recordingCanvasRef, isStreaming, isRecording, detections, activityStatus }) {
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
        {isStreaming && detections.map(detection => (
          <div
            key={detection.id}
            className={`detection-box ${detection.status}`}
            style={{
              left: `${detection.x}%`,
              top: `${detection.y}%`,
              width: `${detection.width}%`,
              height: `${detection.height}%`
            }}
          >
            <span className="detection-label">
              {detection.status === 'suspicious' ? '⚠️ Suspicious' : '✓ Normal'} 
              <span className="confidence">{detection.confidence}%</span>
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
