import React, { useState, useEffect } from 'react';
import { Sparkles, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle, Mic } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const TAGLINES = [
  'सरकारी योजनाएँ, आपकी आवाज़ में।',
  'हिंदी में बोलें — हम समझते हैं।',
  'किसान, महिला, बुजुर्ग — सबके लिए।',
  'Gramin AI Scheme Navigator.',
];

export default function Login({ onAuthSuccess, onGoRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [taglineIdx, setTaglineIdx] = useState(0);
  const [taglineText, setTaglineText] = useState('');
  const [typing, setTyping] = useState(true);

  // Typewriter effect
  useEffect(() => {
    const target = TAGLINES[taglineIdx];
    let i = 0;
    let timeout;
    setTaglineText('');
    setTyping(true);

    const typeNext = () => {
      if (i <= target.length) {
        setTaglineText(target.slice(0, i));
        i++;
        timeout = setTimeout(typeNext, 45);
      } else {
        setTyping(false);
        timeout = setTimeout(() => {
          setTaglineIdx(prev => (prev + 1) % TAGLINES.length);
        }, 2400);
      }
    };
    typeNext();
    return () => clearTimeout(timeout);
  }, [taglineIdx]);

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

  return (
    <div className="auth-page">
      {/* Decorative rural SVG background elements */}
      <svg style={{ position: 'absolute', bottom: 0, left: 0, opacity: 0.08, pointerEvents: 'none' }}
        width="280" height="200" viewBox="0 0 280 200" fill="none">
        <ellipse cx="80" cy="180" rx="80" ry="40" fill="#2D6A4F"/>
        <rect x="76" y="130" width="8" height="50" fill="#A0663A"/>
        <ellipse cx="80" cy="122" rx="22" ry="28" fill="#2D6A4F"/>
        <rect x="200" y="145" width="6" height="35" fill="#A0663A"/>
        <ellipse cx="203" cy="138" rx="16" ry="20" fill="#52B788"/>
        <circle cx="240" cy="30" r="22" fill="#F5A623"/>
      </svg>

      <svg style={{ position: 'absolute', top: 0, right: 0, opacity: 0.08, pointerEvents: 'none', transform: 'scaleX(-1)' }}
        width="220" height="180" viewBox="0 0 280 200" fill="none">
        <ellipse cx="80" cy="180" rx="80" ry="40" fill="#D4720C"/>
        <rect x="76" y="130" width="8" height="50" fill="#A0663A"/>
        <ellipse cx="80" cy="122" rx="22" ry="28" fill="#C1440E"/>
      </svg>

      <div className="auth-card">
        {/* Brand */}
        <div className="auth-brand">
          <div className="auth-brand-icon">
            <Sparkles size={24} color="white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="auth-brand-name">Jan Vaani</h1>
            <p className="auth-brand-sub" style={{ minHeight: '1.1rem' }}>
              {taglineText}
              {typing && <span style={{ opacity: 0.7, color: 'var(--saffron)' }}>|</span>}
            </p>
          </div>
        </div>

        <h2 className="auth-title">नमस्ते! 🙏</h2>
        <p className="auth-subtitle">Sign in to access your welfare scheme assistant</p>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="auth-error">
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          <div className="auth-field">
            <label className="auth-label">Email Address</label>
            <div className="auth-input-wrap">
              <Mail size={15} className="auth-input-icon" />
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
              <Lock size={15} className="auth-input-icon" />
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
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <button id="login-submit" type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? (
              <span className="auth-spinner" />
            ) : (
              <>
                Sign In
                <ArrowRight size={17} />
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
