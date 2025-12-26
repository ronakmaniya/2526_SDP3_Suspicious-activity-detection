const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

export const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, '');

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }

  return res.json();
}

export function apiHealth() {
  return request('/api/health/');
}

export function apiSessionStart() {
  return request('/api/session/start/', { method: 'POST', body: '{}' });
}

export function apiSessionStop() {
  return request('/api/session/stop/', { method: 'POST', body: '{}' });
}

export function apiSessionReset() {
  return request('/api/session/reset/', { method: 'POST', body: '{}' });
}

export function apiGetState() {
  return request('/api/state/');
}

export async function apiUploadRecording(fileBlob, { startedAt, endedAt } = {}) {
  const formData = new FormData();
  formData.append('file', fileBlob, `recording_${Date.now()}.webm`);
  if (startedAt) formData.append('startedAt', startedAt);
  if (endedAt) formData.append('endedAt', endedAt);

  const res = await fetch(`${API_BASE_URL}/api/recordings/upload/`, {
    method: 'POST',
    body: formData
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed ${res.status}: ${text}`);
  }
  return res.json();
}

export function apiListRecordings() {
  return request('/api/recordings/');
}
