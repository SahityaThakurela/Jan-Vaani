import React, { useState } from 'react';
import { Sparkles, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function Login({ onAuthSuccess, onGoRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Login failed. Please check your credentials.');
        return;
      }
      localStorage.setItem('jv_token', data.access_token);
      localStorage.setItem('jv_user', JSON.stringify({ user_id: data.user_id, email: data.email, full_name: data.full_name }));
      onAuthSuccess(data);
    } catch (err) {
      setError('Cannot connect to server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Ambient glow blobs */}
      <div className="auth-blob auth-blob-orange" />
      <div className="auth-blob auth-blob-green" />

      <div className="auth-card">
        {/* Header */}
        <div className="auth-brand">
          <div className="auth-brand-icon">
            <Sparkles size={28} color="#fff" />
          </div>
          <div>
            <h1 className="auth-brand-name">Jan Vaani</h1>
            <p className="auth-brand-sub">Voice AI for Welfare Schemes</p>
          </div>
        </div>

        <h2 className="auth-title">Welcome back</h2>
        <p className="auth-subtitle">Sign in to continue your session</p>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="auth-field">
            <label className="auth-label">Email Address</label>
            <div className="auth-input-wrap">
              <Mail size={16} className="auth-input-icon" />
              <input
                id="login-email"
                type="email"
                className="auth-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="auth-field">
            <label className="auth-label">Password</label>
            <div className="auth-input-wrap">
              <Lock size={16} className="auth-input-icon" />
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                className="auth-eye-btn"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            id="login-submit"
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-spinner" />
            ) : (
              <>
                Sign In
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account?{' '}
          <button className="auth-link-btn" onClick={onGoRegister}>
            Create one free
          </button>
        </p>

        <div className="auth-divider">
          <span>Hackathon Demo</span>
        </div>
        <p className="auth-demo-note">
          Jan Vaani • StarForge Hackathon 2026 • Voice-first welfare AI
        </p>
      </div>
    </div>
  );
}
