import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
        email,
        password
      });
      
      localStorage.setItem('token', res.data.token);
      localStorage.setItem('user', JSON.stringify(res.data.user));
      
      navigate('/chat');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    }
    setLoading(false);
  };

  const handleDemoLogin = (demoEmail) => {
    setEmail(demoEmail);
    setPassword('123456');
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-title">
          <h1>Millow</h1>
          <p>Welcome back! Please login.</p>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <div className="divider">
          <span>Demo Accounts (password: 123456)</span>
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
          <button 
            className="google-button"
            onClick={() => handleDemoLogin('bessie@millow.com')}
            style={{ background: '#374151', color: 'white' }}
          >
            👤 Login as Bessie Cooper
          </button>
          <button 
            className="google-button"
            onClick={() => handleDemoLogin('darrell@millow.com')}
            style={{ background: '#374151', color: 'white' }}
          >
            👤 Login as Darrell Steward
          </button>
          <button 
            className="google-button"
            onClick={() => handleDemoLogin('leslie@millow.com')}
            style={{ background: '#374151', color: 'white' }}
          >
            👤 Login as Leslie Alexander
          </button>
        </div>
        
        <div className="divider">
          <span>OR</span>
        </div>
        
        <button 
          className="google-button"
          onClick={() => {
            // Demo Google login
            const demoUser = {
              id: 'google_' + Date.now(),
              name: 'Google User',
              email: 'google@millow.com',
              avatar: 'https://ui-avatars.com/api/?name=Google+User&background=8B5CF6&color=fff',
              bio: 'Hey there! I am using Millow'
            };
            localStorage.setItem('token', 'demo_google_token');
            localStorage.setItem('user', JSON.stringify(demoUser));
            navigate('/chat');
          }}
        >
          <span style={{ fontSize: '18px' }}>G</span> Continue with Google
        </button>
        
        <div className="auth-footer">
          Don't have an account? <Link to="/register">Register</Link>
        </div>
      </div>
    </div>
  );
};

export default Login;