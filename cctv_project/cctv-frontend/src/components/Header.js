import React from 'react';
import './Header.css';

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo-section">
          <div className="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="url(#gradient)"/>
              <circle cx="12" cy="12" r="4" fill="#1a1a2e"/>
              <circle cx="12" cy="12" r="2" fill="#00d4ff"/>
              <defs>
                <linearGradient id="gradient" x1="2" y1="2" x2="22" y2="22">
                  <stop stopColor="#00d4ff"/>
                  <stop offset="1" stopColor="#7c3aed"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="title-section">
            <h1>CCTV Surveillance Dashboard</h1>
            <p className="subtitle">Real-time Activity Monitoring System</p>
          </div>
        </div>
        
        <div className="header-status">
          <div className="live-indicator">
            <span className="pulse"></span>
            <span>LIVE</span>
          </div>
          <div className="time-display">
            <TimeDisplay />
          </div>
        </div>
      </div>
    </header>
  );
}

function TimeDisplay() {
  const [time, setTime] = React.useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <span>
      {time.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
      })} • {time.toLocaleTimeString()}
    </span>
  );
}

export default Header;
