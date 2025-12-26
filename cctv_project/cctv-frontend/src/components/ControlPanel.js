import React from 'react';
import './ControlPanel.css';

function ControlPanel({
  isStreaming,
  onStart,
  onStop,
  onReset,
  isRecording,
  recordingUploadState,
  recordingUploadError,
  onStartRecording,
  onStopRecording
}) {
  return (
    <div className="control-panel">
      <button 
        className={`control-btn start ${isStreaming ? 'disabled' : ''}`}
        onClick={onStart}
        disabled={isStreaming}
      >
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4zM5 6h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span>Start Camera</span>
      </button>
      
      <button 
        className={`control-btn stop ${!isStreaming ? 'disabled' : ''}`}
        onClick={onStop}
        disabled={!isStreaming}
      >
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4zM5 6h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
        <span>Stop Camera</span>
      </button>

      <button
        className={`control-btn record ${(!isStreaming || recordingUploadState === 'uploading') ? 'disabled' : ''}`}
        onClick={isRecording ? onStopRecording : onStartRecording}
        disabled={!isStreaming || recordingUploadState === 'uploading'}
        title={recordingUploadState === 'uploading' ? 'Uploading…' : ''}
      >
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="2" />
          <circle cx="12" cy="12" r="3" fill="currentColor" />
        </svg>
        <span>
          {isRecording
            ? 'Stop Recording'
            : (recordingUploadState === 'uploading' ? 'Uploading…' : 'Start Recording')}
        </span>
      </button>
      
      <button 
        className="control-btn reset"
        onClick={onReset}
      >
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span>Reset</span>
      </button>

      {recordingUploadState === 'error' && (
        <div className="recording-status error">{recordingUploadError || 'Recording upload failed.'}</div>
      )}

      {recordingUploadState === 'uploaded' && (
        <div className="recording-status success">Recording saved to backend.</div>
      )}
    </div>
  );
}

export default ControlPanel;
