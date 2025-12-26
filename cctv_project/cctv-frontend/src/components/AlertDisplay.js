import React from 'react';
import './AlertDisplay.css';

function AlertDisplay({ alerts, onDismiss, onClearAll }) {
  return (
    <div className="alert-panel">
      <div className="panel-header">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Alert History
        </h3>
        <div className="header-actions">
          {alerts.length > 0 && (
            <button className="clear-all-btn" onClick={onClearAll} title="Clear all alerts">
              Clear All
            </button>
          )}
          <span className="alert-count">{alerts.length}</span>
        </div>
      </div>
      
      <div className="alerts-list">
        {alerts.length === 0 ? (
          <div className="no-alerts">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <p>No alerts recorded</p>
            <span>Alerts will appear here when suspicious activity is detected</span>
          </div>
        ) : (
          alerts.map((alert, index) => (
            <div 
              key={alert.id} 
              className="alert-item"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="alert-icon">⚠️</div>
              <div className="alert-content">
                <span className="alert-message">{alert.message}</span>
                <div className="alert-meta">
                  <span className="alert-time">{alert.time}</span>
                  <span className="alert-confidence">Confidence: {alert.confidence}%</span>
                </div>
              </div>
              <button 
                className="dismiss-btn"
                onClick={() => onDismiss(alert.id)}
                aria-label="Dismiss alert"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default AlertDisplay;
