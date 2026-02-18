import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import LiveMonitor from './components/LiveMonitor';
import VideoUpload from './components/VideoUpload';
import Recordings from './components/Recordings';
import Dashboard from './components/Dashboard';

import { FiShield, FiMonitor, FiUpload, FiFilm, FiActivity } from 'react-icons/fi';

function App() {
  return (
    <Router>
      <div className="app-container">
        {/* Navigation Bar */}
        <nav className="navbar">
          <NavLink to="/" className="navbar-brand">
            <FiShield className="icon" />
            AI Surveillance System
          </NavLink>

          <ul className="navbar-links">
            <li>
              <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
                <FiActivity style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Dashboard
              </NavLink>
            </li>
            <li>
              <NavLink to="/live" className={({ isActive }) => isActive ? 'active' : ''}>
                <FiMonitor style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Live Monitor
              </NavLink>
            </li>
            <li>
              <NavLink to="/upload" className={({ isActive }) => isActive ? 'active' : ''}>
                <FiUpload style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Upload Video
              </NavLink>
            </li>
            <li>
              <NavLink to="/recordings" className={({ isActive }) => isActive ? 'active' : ''}>
                <FiFilm style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Recordings
              </NavLink>
            </li>
          </ul>

          <div className="navbar-status">
            <span className="status-dot"></span>
            System Online
          </div>
        </nav>

        {/* Main Content */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/live" element={<LiveMonitor />} />
            <Route path="/upload" element={<VideoUpload />} />
            <Route path="/recordings" element={<Recordings />} />
          </Routes>
        </main>

        <ToastContainer
          position="bottom-right"
          theme="dark"
          autoClose={4000}
        />
      </div>
    </Router>
  );
}

export default App;
