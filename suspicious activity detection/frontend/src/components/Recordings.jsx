/**
 * Recordings Component
 * Lists all video recordings with status, stats, and download links.
 */
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { FiFilm, FiDownload, FiClock, FiAlertTriangle, FiCheckCircle, FiRefreshCw, FiTrash2 } from 'react-icons/fi';
import { getRecordings, getRecordingDownloadUrl, deleteRecording } from '../services/api';

function Recordings() {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  const fetchRecordings = async (pageNum = 1) => {
    setLoading(true);
    try {
      const data = await getRecordings(pageNum);
      setRecordings(data.results || []);
      setHasNext(!!data.next);
    } catch (err) {
      toast.error('Failed to load recordings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecordings(page);
  }, [page]);

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleString();
  };

  const handleDelete = async (rec) => {
    const confirmed = window.confirm(
      `Delete "${rec.title}"?\n\nThis will permanently remove the recording and all associated detection events.`
    );
    if (!confirmed) return;

    try {
      await deleteRecording(rec.id);
      toast.success('Recording deleted');
      fetchRecordings(page);
    } catch (err) {
      toast.error('Failed to delete recording');
      console.error(err);
    }
  };

  const getStatusBadge = (status) => {
    const map = {
      recording: { color: 'var(--accent-red)', icon: <FiClock size={12} />, text: 'Recording' },
      processing: { color: 'var(--accent-yellow)', icon: <FiRefreshCw size={12} />, text: 'Processing' },
      completed: { color: 'var(--accent-green)', icon: <FiCheckCircle size={12} />, text: 'Completed' },
      failed: { color: 'var(--accent-red)', icon: <FiAlertTriangle size={12} />, text: 'Failed' },
    };
    const s = map[status] || map.completed;
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 600,
        background: `${s.color}22`, color: s.color,
      }}>
        {s.icon} {s.text}
      </span>
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Video Recordings</h1>
        <button className="btn btn-outline" onClick={() => fetchRecordings(page)}>
          <FiRefreshCw /> Refresh
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <FiRefreshCw size={32} style={{ animation: 'spin 1s linear infinite' }} />
            <p style={{ marginTop: '0.5rem' }}>Loading recordings...</p>
          </div>
        ) : recordings.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <FiFilm size={48} />
            <p style={{ marginTop: '1rem' }}>No recordings yet</p>
            <p style={{ fontSize: '0.85rem' }}>Start a live recording or upload a video to get started.</p>
          </div>
        ) : (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Suspicious</th>
                  <th>Normal</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recordings.map((rec) => (
                  <tr key={rec.id}>
                    <td style={{ fontWeight: 500 }}>{rec.title}</td>
                    <td>
                      <span style={{
                        padding: '2px 6px', borderRadius: 4, fontSize: '0.75rem',
                        background: rec.source_type === 'live' ? 'rgba(41,121,255,0.15)' : 'rgba(255,234,0,0.15)',
                        color: rec.source_type === 'live' ? 'var(--accent-blue)' : 'var(--accent-yellow)',
                      }}>
                        {rec.source_type === 'live' ? 'LIVE' : 'UPLOAD'}
                      </span>
                    </td>
                    <td>{getStatusBadge(rec.status)}</td>
                    <td style={{ fontFamily: 'monospace' }}>{formatDuration(rec.duration)}</td>
                    <td style={{ color: rec.suspicious_count > 0 ? 'var(--accent-red)' : 'var(--text-muted)', fontWeight: 600 }}>
                      {rec.suspicious_count}
                    </td>
                    <td style={{ color: 'var(--accent-green)' }}>{rec.normal_count}</td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      {formatDate(rec.created_at)}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {rec.status === 'completed' && (
                          <a
                            href={getRecordingDownloadUrl(rec.id)}
                            className="btn btn-outline"
                            style={{ padding: '4px 10px', fontSize: '0.8rem', textDecoration: 'none' }}
                            download
                          >
                            <FiDownload /> Download
                          </a>
                        )}
                        <button
                          className="btn btn-outline"
                          style={{
                            padding: '4px 10px', fontSize: '0.8rem',
                            color: 'var(--accent-red)', borderColor: 'rgba(255,23,68,0.3)',
                          }}
                          onClick={() => handleDelete(rec)}
                          title="Delete recording"
                        >
                          <FiTrash2 /> Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '1.5rem' }}>
              <button
                className="btn btn-outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span style={{ padding: '0.6rem 1rem', color: 'var(--text-secondary)' }}>
                Page {page}
              </span>
              <button
                className="btn btn-outline"
                disabled={!hasNext}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default Recordings;
