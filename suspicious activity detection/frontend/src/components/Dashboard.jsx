/**
 * Dashboard Component
 * Shows system statistics, recent events, and overall system health.
 */
import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { FiActivity, FiShield, FiAlertTriangle, FiCheckCircle, FiFilm, FiClock, FiRefreshCw } from 'react-icons/fi';
import { getStats, getEvents, healthCheck } from '../services/api';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsData, eventsData, healthData] = await Promise.all([
        getStats().catch(() => null),
        getEvents({ label: 'suspicious', page: 1 }).catch(() => ({ results: [] })),
        healthCheck().catch(() => null),
      ]);

      if (statsData) setStats(statsData);
      if (eventsData) setEvents(eventsData.results || []);
      if (healthData) setSystemHealth(healthData);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const formatTime = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleTimeString();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          <FiActivity style={{ verticalAlign: 'middle', marginRight: 8 }} />
          System Dashboard
        </h1>
        <button className="btn btn-outline" onClick={fetchData} disabled={loading}>
          <FiRefreshCw style={loading ? { animation: 'spin 1s linear infinite' } : {}} /> Refresh
        </button>
      </div>

      {/* System Health Banner */}
      <div className="card" style={{
        marginBottom: '1.5rem',
        background: systemHealth
          ? 'linear-gradient(135deg, rgba(0,230,118,0.08), rgba(41,121,255,0.08))'
          : 'linear-gradient(135deg, rgba(255,23,68,0.08), rgba(255,234,0,0.08))',
        borderColor: systemHealth ? 'rgba(0,230,118,0.3)' : 'rgba(255,23,68,0.3)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <FiShield size={28} style={{ color: systemHealth ? 'var(--accent-green)' : 'var(--accent-red)' }} />
          <div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: 2 }}>
              {systemHealth ? 'System Online & Operational' : 'System Status Unknown'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              AI Surveillance System v1.0 — YOLOv8x + Video Swin Transformer
              {systemHealth && ` — Last check: ${formatDate(systemHealth.timestamp)}`}
            </p>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className={`status-dot ${systemHealth ? '' : 'inactive'}`}></span>
            <span style={{ color: systemHealth ? 'var(--accent-green)' : 'var(--text-muted)', fontWeight: 600, fontSize: '0.9rem' }}>
              {systemHealth ? 'HEALTHY' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value blue">{stats?.total_events ?? '-'}</div>
          <div className="stat-label">Total Detections</div>
        </div>
        <div className="stat-card">
          <div className="stat-value red">{stats?.suspicious_events ?? '-'}</div>
          <div className="stat-label">Suspicious Events</div>
        </div>
        <div className="stat-card">
          <div className="stat-value green">{stats?.normal_events ?? '-'}</div>
          <div className="stat-label">Normal Events</div>
        </div>
        <div className="stat-card">
          <div className="stat-value yellow">{stats?.total_recordings ?? '-'}</div>
          <div className="stat-label">Total Recordings</div>
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="dashboard-grid">
        {/* Recent Suspicious Events */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <FiAlertTriangle style={{ color: 'var(--accent-red)', marginRight: 6, verticalAlign: 'middle' }} />
              Recent Suspicious Events
            </span>
            <span className="log-badge suspicious">{events.length} events</span>
          </div>

          <div className="detection-log">
            {events.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                <FiCheckCircle size={32} style={{ marginBottom: '0.5rem' }} />
                <p>No suspicious activity detected</p>
              </div>
            ) : (
              events.map((evt) => (
                <div key={evt.id} className="log-entry">
                  <span className="log-badge suspicious">SUSPICIOUS</span>
                  <span className="log-confidence">
                    {(evt.confidence * 100).toFixed(1)}%
                  </span>
                  {evt.bounding_box && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      [{evt.bounding_box.x1}, {evt.bounding_box.y1}]
                    </span>
                  )}
                  <span className="log-time">{formatDate(evt.timestamp)}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* System Info Panel */}
        <div>
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div className="card-header">
              <span className="card-title">System Info</span>
            </div>
            <div style={{ fontSize: '0.9rem' }}>
              {[
                { label: 'Human Detection', value: 'YOLOv8x', color: 'var(--accent-blue)' },
                { label: 'Activity Model', value: 'Video Swin', color: 'var(--accent-blue)' },
                { label: 'Target FPS', value: '24 FPS', color: 'var(--accent-green)' },
                { label: 'Sliding Window', value: '16 frames', color: 'var(--text-secondary)' },
                { label: 'Output Format', value: 'MP4', color: 'var(--text-secondary)' },
                { label: 'Backend', value: 'Django REST', color: 'var(--accent-yellow)' },
                { label: 'Frontend', value: 'React + Vite', color: 'var(--accent-yellow)' },
              ].map((item, i) => (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between',
                  padding: '0.5rem 0',
                  borderBottom: i < 6 ? '1px solid var(--border-color)' : 'none',
                }}>
                  <span style={{ color: 'var(--text-muted)' }}>{item.label}</span>
                  <span style={{ color: item.color, fontWeight: 600 }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">
                <FiFilm style={{ marginRight: 6, verticalAlign: 'middle' }} />
                Active Sessions
              </span>
            </div>
            <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>
              <p>{stats?.active_recordings ?? 0} active recording(s)</p>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default Dashboard;
