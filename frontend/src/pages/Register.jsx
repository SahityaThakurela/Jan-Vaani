import React, { useState } from 'react';
import { Sparkles, Mail, Lock, Eye, EyeOff, User, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function Register({ onAuthSuccess, onGoLogin }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName || null }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Registration failed. Please try again.');
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

  // Password strength
  const pwdStrength = password.length === 0 ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3;
  const strengthColors = ['', '#ef4444', '#f59e0b', '#10b981'];
  const strengthLabels = ['', 'Weak', 'Fair', 'Strong'];

  return (
    <div className="auth-page">
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

        <h2 className="auth-title">Create your account</h2>
        <p className="auth-subtitle">Start checking welfare scheme eligibility for free</p>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="auth-field">
            <label className="auth-label">Full Name <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span></label>
            <div className="auth-input-wrap">
              <User size={16} className="auth-input-icon" />
              <input
                id="register-name"
                type="text"
                className="auth-input"
                placeholder="Rajesh Kumar"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
            </div>
          </div>

          <div className="auth-field">
            <label className="auth-label">Email Address</label>
            <div className="auth-input-wrap">
              <Mail size={16} className="auth-input-icon" />
              <input
                id="register-email"
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
                id="register-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                placeholder="Min 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
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
            {password.length > 0 && (
              <div className="pwd-strength-bar">
                <div
                  className="pwd-strength-fill"
                  style={{
                    width: `${(pwdStrength / 3) * 100}%`,
                    background: strengthColors[pwdStrength],
                  }}
                />
                <span style={{ color: strengthColors[pwdStrength], fontSize: '0.75rem', marginTop: '4px' }}>
                  {strengthLabels[pwdStrength]}
                </span>
              </div>
            )}
          </div>

          <div className="auth-field">
            <label className="auth-label">Confirm Password</label>
            <div className="auth-input-wrap">
              <Lock size={16} className="auth-input-icon" />
              <input
                id="register-confirm-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                placeholder="Repeat password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
              {confirmPassword.length > 0 && (
                <span className="auth-match-indicator">
                  {password === confirmPassword
                    ? <CheckCircle2 size={16} color="#10b981" />
                    : <AlertCircle size={16} color="#ef4444" />}
                </span>
              )}
            </div>
          </div>

          <button
            id="register-submit"
            type="submit"
            className="auth-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="auth-spinner" />
            ) : (
              <>
                Create Account
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{' '}
          <button className="auth-link-btn" onClick={onGoLogin}>
            Sign in
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
