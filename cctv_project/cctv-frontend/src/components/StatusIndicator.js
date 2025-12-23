import React from 'react';
import './StatusIndicator.css';

function StatusIndicator({ status }) {
  const getStatusInfo = () => {
    switch (status) {
      case 'normal':
        return {
          label: 'Normal Activity',
          icon: '✓',
          description: 'All clear - No suspicious behavior detected'
        };
      case 'suspicious':
        return {
          label: 'Suspicious Activity',
          icon: '⚠',
          description: 'Alert! Unusual behavior detected'
        };
      default:
        return {
          label: 'System Idle',
          icon: '○',
          description: 'Camera is offline - Start surveillance to monitor'
        };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div className={`status-indicator ${status}`}>
      <div className="status-content">
        <div className="status-icon-wrapper">
          <span className="status-icon">{statusInfo.icon}</span>
          <span className="status-ring"></span>
        </div>
        <div className="status-text">
          <span className="status-label">Status: {statusInfo.label}</span>
          <span className="status-description">{statusInfo.description}</span>
        </div>
      </div>
      <div className="status-bar">
        <div className="status-bar-fill"></div>
      </div>
    </div>
  );
}

export default StatusIndicator;
