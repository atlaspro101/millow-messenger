import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Chat from './pages/Chat';
import Profile from './pages/Profile';
import './App.css';

function App() {
  useEffect(() => {
    const theme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/" element={<WelcomeScreen />} />
      </Routes>
    </BrowserRouter>
  );
}

const WelcomeScreen = () => {
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      window.location.href = '/chat';
    }
  }, []);

  return (
    <div className="welcome-container">
      <div className="welcome-content">
        <h1 className="welcome-title">Millow</h1>
        <p className="welcome-subtitle">Connect with friends and the world around you</p>
        <div className="welcome-buttons">
          <button 
            className="welcome-btn primary"
            onClick={() => window.location.href = '/login'}
          >
            Get Started
          </button>
          <button 
            className="welcome-btn secondary"
            onClick={() => window.location.href = '/register'}
          >
            Create Account
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;