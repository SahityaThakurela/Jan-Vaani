import React, { useState } from 'react';
import { Sparkles, Mail, Lock, Eye, EyeOff, User, ArrowRight, AlertCircle, CheckCircle2, Mic } from 'lucide-react';
import RuralBackground from '../components/RuralBackground';

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
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName || null }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || 'Registration failed. Please try again.'); return; }
      localStorage.setItem('jv_token', data.access_token);
      localStorage.setItem('jv_user', JSON.stringify({
        user_id: data.user_id, email: data.email, full_name: data.full_name
      }));
      onAuthSuccess(data);
    } catch {
      setError('Cannot connect to server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // Password strength
  const pwdStrength = password.length === 0 ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3;
  const strengthColors = ['', '#C1440E', '#E8803A', '#2D6A4F'];
  const strengthLabels = ['', 'Weak', 'Fair', 'Strong'];

  return (
    <div className="auth-page" style={{ position: 'relative' }}>
      <RuralBackground />

      <div className="auth-card">
        {/* Brand */}
        <div className="auth-brand">
          <div className="auth-brand-icon">
            <Sparkles size={24} color="white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="auth-brand-name">Jan Vaani</h1>
            <p className="auth-brand-sub">Voice AI for Welfare Schemes</p>
          </div>
        </div>

        <h2 className="auth-title">अकाउंट बनाएं</h2>
        <p className="auth-subtitle">Start checking welfare scheme eligibility for free</p>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          <div className="auth-field">
            <label className="auth-label">
              Full Name{' '}
              <span style={{ color: 'var(--text-muted)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                (optional)
              </span>
            </label>
            <div className="auth-input-wrap">
              <User size={15} className="auth-input-icon" />
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
              <Mail size={15} className="auth-input-icon" />
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
              <Lock size={15} className="auth-input-icon" />
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
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            {password.length > 0 && (
              <div className="pwd-strength-bar">
                <div className="pwd-strength-track">
                  <div
                    className="pwd-strength-fill"
                    style={{ width: `${(pwdStrength / 3) * 100}%`, background: strengthColors[pwdStrength] }}
                  />
                </div>
                <span style={{ color: strengthColors[pwdStrength], fontSize: '0.74rem', marginTop: '4px' }}>
                  {strengthLabels[pwdStrength]}
                </span>
              </div>
            )}
          </div>

          <div className="auth-field">
            <label className="auth-label">Confirm Password</label>
            <div className="auth-input-wrap">
              <Lock size={15} className="auth-input-icon" />
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
                    ? <CheckCircle2 size={15} color="var(--green-mid)" />
                    : <AlertCircle size={15} color="var(--terracotta)" />}
                </span>
              )}
            </div>
          </div>

          <button id="register-submit" type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? (
              <span className="auth-spinner" />
            ) : (
              <>
                Create Account
                <ArrowRight size={17} />
              </>
            )}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{' '}
          <button className="auth-link-btn" onClick={onGoLogin}>Sign in</button>
        </p>

        <div className="auth-divider">
          <span>StarForge Hackathon 2026</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <Mic size={11} style={{ color: 'rgba(212,114,12,0.5)' }} />
          <p className="auth-demo-note">Jan Vaani · Voice-first Welfare AI for Rural India</p>
        </div>
      </div>
    </div>
  );
}
