/**
 * VideoUpload Component
 * Allows users to upload MP4 files for processing.
 * Shows upload progress and processing status.
 */
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { toast } from 'react-toastify';
import { FiUploadCloud, FiFile, FiCheck, FiLoader, FiX } from 'react-icons/fi';
import { uploadVideo, checkRecordingStatus, getRecordingDownloadUrl } from '../services/api';

function VideoUpload() {
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingId, setProcessingId] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const pollTimerRef = useRef(null);
  const pollErrorCountRef = useRef(0);
  const MAX_POLL_ERRORS = 5;

  // Cleanup poll timer on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  /**
   * Handle file selection
   */
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        toast.error('Please select a valid video file');
        return;
      }
      setSelectedFile(file);
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setDownloadUrl(null);
      setProcessingStatus(null);
    }
  };

  /**
   * Handle drag & drop
   */
  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
      setSelectedFile(file);
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
      setDownloadUrl(null);
      setProcessingStatus(null);
    } else {
      toast.error('Please drop a valid video file');
    }
  }, []);

  const handleDragOver = (e) => e.preventDefault();

  /**
   * Upload and process video
   */
  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select a video file first');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      const result = await uploadVideo(selectedFile, title || 'Uploaded Video', (progress) => {
        setUploadProgress(progress);
      });

      setProcessingId(result.recording_id);
      setUploading(false);
      toast.success('Video uploaded! Processing started...');

      // Poll for processing status
      pollProcessingStatus(result.recording_id);
    } catch (err) {
      setUploading(false);
      toast.error('Upload failed: ' + (err.response?.data?.error || err.message));
    }
  };

  /**
   * Poll backend for processing status.
   * Stops on completion, failure, 404 (deleted), or after too many consecutive errors.
   */
  const pollProcessingStatus = async (recordingId) => {
    // Cancel any existing poll
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    pollErrorCountRef.current = 0;

    const poll = async () => {
      try {
        const status = await checkRecordingStatus(recordingId);
        setProcessingStatus(status);
        pollErrorCountRef.current = 0; // reset on success

        if (status.status === 'completed') {
          setDownloadUrl(getRecordingDownloadUrl(recordingId));
          toast.success('Video processing complete!');
          pollTimerRef.current = null;
          return;
        } else if (status.status === 'failed') {
          toast.error('Video processing failed');
          pollTimerRef.current = null;
          return;
        }

        // Continue polling
        pollTimerRef.current = setTimeout(poll, 2000);
      } catch (err) {
        pollErrorCountRef.current += 1;
        const is404 = err.response && err.response.status === 404;

        if (is404) {
          // Recording was deleted — stop polling
          toast.error('Recording no longer exists');
          setProcessingId(null);
          setProcessingStatus(null);
          pollTimerRef.current = null;
          return;
        }

        if (pollErrorCountRef.current >= MAX_POLL_ERRORS) {
          toast.error('Lost connection to server. Status polling stopped.');
          pollTimerRef.current = null;
          return;
        }

        console.error('Status check error:', err);
        pollTimerRef.current = setTimeout(poll, 3000);
      }
    };

    poll();
  };

  /**
   * Reset form
   */
  const resetForm = () => {
    // Cancel any active polling
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    pollErrorCountRef.current = 0;
    setSelectedFile(null);
    setTitle('');
    setUploading(false);
    setUploadProgress(0);
    setProcessingId(null);
    setProcessingStatus(null);
    setDownloadUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div>
      <h1 className="page-title">Upload Video for Analysis</h1>

      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div className="card">
          {/* Upload Area */}
          {!processingId && (
            <>
              <div
                className="upload-area"
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
              >
                <FiUploadCloud className="icon" />
                <p style={{ marginBottom: '0.5rem', fontSize: '1.1rem' }}>
                  {selectedFile
                    ? selectedFile.name
                    : 'Click or drag & drop your video file here'}
                </p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Supports MP4, AVI, MOV — Max 500MB
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />

              {selectedFile && (
                <div style={{ marginTop: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                    Video Title
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter video title"
                    style={{
                      width: '100%',
                      padding: '0.6rem 1rem',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 8,
                      color: 'var(--text-primary)',
                      fontSize: '0.95rem',
                    }}
                  />
                </div>
              )}

              {/* Upload Progress */}
              {uploading && (
                <div style={{ marginTop: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Uploading...</span>
                    <span style={{ color: 'var(--accent-blue)' }}>{uploadProgress}%</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                </div>
              )}

              <div className="controls-bar" style={{ marginTop: '1.5rem' }}>
                <button
                  className="btn btn-primary"
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                >
                  {uploading ? <FiLoader className="spin" /> : <FiUploadCloud />}
                  {uploading ? 'Uploading...' : 'Upload & Process'}
                </button>

                {selectedFile && (
                  <button className="btn btn-outline" onClick={resetForm}>
                    <FiX /> Clear
                  </button>
                )}
              </div>
            </>
          )}

          {/* Processing Status */}
          {processingId && (
            <div style={{ textAlign: 'center', padding: '2rem 0' }}>
              {processingStatus?.status === 'completed' ? (
                <>
                  <FiCheck size={48} style={{ color: 'var(--accent-green)', marginBottom: '1rem' }} />
                  <h3 style={{ marginBottom: '0.5rem' }}>Processing Complete!</h3>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                    Found {processingStatus.suspicious_count} suspicious events
                    and {processingStatus.normal_count} normal events
                    across {processingStatus.total_frames} frames.
                  </p>

                  <div className="stats-grid" style={{ maxWidth: 400, margin: '1rem auto' }}>
                    <div className="stat-card">
                      <div className="stat-value red">{processingStatus.suspicious_count}</div>
                      <div className="stat-label">Suspicious</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value green">{processingStatus.normal_count}</div>
                      <div className="stat-label">Normal</div>
                    </div>
                  </div>

                  {downloadUrl && (
                    <a
                      href={downloadUrl}
                      className="btn btn-success"
                      style={{
                        display: 'inline-flex',
                        textDecoration: 'none',
                        marginTop: '1rem',
                      }}
                      download
                    >
                      Download Processed Video
                    </a>
                  )}

                  <div style={{ marginTop: '1.5rem' }}>
                    <button className="btn btn-outline" onClick={resetForm}>
                      Upload Another Video
                    </button>
                  </div>
                </>
              ) : processingStatus?.status === 'failed' ? (
                <>
                  <FiX size={48} style={{ color: 'var(--accent-red)', marginBottom: '1rem' }} />
                  <h3>Processing Failed</h3>
                  <p style={{ color: 'var(--text-secondary)' }}>
                    An error occurred while processing the video.
                  </p>
                  <button className="btn btn-outline" onClick={resetForm} style={{ marginTop: '1rem' }}>
                    Try Again
                  </button>
                </>
              ) : (
                <>
                  <div style={{
                    width: 48,
                    height: 48,
                    border: '3px solid var(--border-color)',
                    borderTopColor: 'var(--accent-blue)',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    margin: '0 auto 1rem',
                  }} />
                  <h3>Processing Video...</h3>
                  <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                    AI models are analyzing your video for suspicious activity.
                    This may take a few minutes.
                  </p>
                  {processingStatus && (
                    <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontSize: '0.85rem' }}>
                      Frames: {processingStatus.total_frames} |
                      Suspicious: {processingStatus.suspicious_count} |
                      Normal: {processingStatus.normal_count}
                    </p>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}

export default VideoUpload;
