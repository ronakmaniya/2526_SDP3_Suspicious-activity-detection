/**
 * API Service - Handles all communication with the Django backend.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==================== Frame Analysis ====================

/**
 * Send a single frame for AI analysis.
 * @param {string} frameBase64 - Base64 encoded frame (data URL or raw base64)
 * @param {number|null} recordingId - Optional recording database ID
 * @param {string|null} sessionId - Optional live session ID (for saving frames to recording)
 * @returns {Promise} Analysis results with annotated frame
 */
export const analyzeFrame = async (frameBase64, recordingId = null, sessionId = null) => {
  const payload = {
    frame: frameBase64,
  };
  if (recordingId) {
    payload.recording_id = recordingId;
  }
  if (sessionId) {
    payload.session_id = sessionId;
  }
  const response = await api.post('/analyze-frame/', payload);
  return response.data;
};

// ==================== Live Session ====================

/**
 * Start a new live recording session.
 * @returns {Promise} Session info with session_id and recording_id
 */
export const startLiveSession = async () => {
  const response = await api.post('/live-session/', { action: 'start' });
  return response.data;
};

/**
 * Stop an active live recording session.
 * @param {string} sessionId
 * @param {number|null} recordingId - Optional recording database ID for finalization
 * @returns {Promise}
 */
export const stopLiveSession = async (sessionId, recordingId = null) => {
  const payload = {
    action: 'stop',
    session_id: sessionId,
  };
  if (recordingId) {
    payload.recording_id = recordingId;
  }
  const response = await api.post('/live-session/', payload);
  return response.data;
};

/**
 * Get all active live sessions.
 * @returns {Promise}
 */
export const getActiveSessions = async () => {
  const response = await api.get('/live-session/');
  return response.data;
};

// ==================== Video Upload ====================

/**
 * Upload a video file for processing.
 * @param {File} videoFile
 * @param {string} title
 * @param {Function} onProgress - Progress callback
 * @returns {Promise}
 */
export const uploadVideo = async (videoFile, title = 'Uploaded Video', onProgress = null) => {
  const formData = new FormData();
  formData.append('video', videoFile);
  formData.append('title', title);

  const response = await api.post('/upload-video/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
  return response.data;
};

// ==================== Recordings ====================

/**
 * Get all video recordings.
 * @param {number} page
 * @returns {Promise}
 */
export const getRecordings = async (page = 1) => {
  const response = await api.get(`/recordings/?page=${page}`);
  return response.data;
};

/**
 * Get a specific recording with all events.
 * @param {number} id
 * @returns {Promise}
 */
export const getRecording = async (id) => {
  const response = await api.get(`/recordings/${id}/`);
  return response.data;
};

/**
 * Check recording processing status.
 * @param {number} id
 * @returns {Promise}
 */
export const checkRecordingStatus = async (id) => {
  const response = await api.get(`/recordings/${id}/status_check/`);
  return response.data;
};

/**
 * Get download URL for a processed recording.
 * @param {number} id
 * @returns {string}
 */
export const getRecordingDownloadUrl = (id) => {
  return `${API_BASE}/recordings/${id}/download/`;
};

/**
 * Delete a recording and its video files.
 * @param {number} id
 * @returns {Promise}
 */
export const deleteRecording = async (id) => {
  const response = await api.delete(`/recordings/${id}/`);
  return response;
};

// ==================== Events ====================

/**
 * Get detection events.
 * @param {Object} filters - { label, recording_id, min_confidence, page }
 * @returns {Promise}
 */
export const getEvents = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.label) params.append('label', filters.label);
  if (filters.recording_id) params.append('recording_id', filters.recording_id);
  if (filters.min_confidence) params.append('min_confidence', filters.min_confidence);
  if (filters.page) params.append('page', filters.page);

  const response = await api.get(`/events/?${params.toString()}`);
  return response.data;
};

// ==================== System ====================

/**
 * Health check.
 * @returns {Promise}
 */
export const healthCheck = async () => {
  const response = await api.get('/health/');
  return response.data;
};

/**
 * Get system statistics.
 * @returns {Promise}
 */
export const getStats = async () => {
  const response = await api.get('/stats/');
  return response.data;
};

export default api;
