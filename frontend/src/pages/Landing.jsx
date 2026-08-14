import React, { useState } from 'react';
import {
  ArrowRight,
  Mic,
  Search,
  ShieldCheck,
  Languages,
  Sparkles,
  Menu,
  X
} from "lucide-react";

export default function Landing({ onGetStarted, onLogin }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  return (
    <div className="landing-page">

      {/* ── Navbar ── */}
      <nav className="landing-navbar">
        <div className="landing-brand">
          <div className="landing-logo">
            <Sparkles size={20} color="white" />
          </div>
          <div>
            <h2>Jan Vaani</h2>
            <span>जन की आवाज़ · AI Scheme Finder</span>
          </div>
        </div>

        <button 
          className="mobile-menu-btn" 
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        <div className={`landing-nav-actions ${isMobileMenuOpen ? 'open' : ''}`}>
          <button className="landing-login" onClick={onLogin}>
            Login
          </button>
          <button className="landing-get-started" onClick={onGetStarted}>
            Get Started
            <ArrowRight size={17} />
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <main className="landing-hero">
        <div className="landing-hero-content">

          <div className="landing-badge">
            <span />
            AI-powered · Rural India · Government Schemes
          </div>

          <h1>
            सरकारी योजनाएँ,
            <br />
            <span>आपकी आवाज़ में।</span>
          </h1>

          <p>
            Jan Vaani helps you discover government welfare schemes, understand
            your eligibility, and get answers in Hindi or English — simply by
            speaking.
          </p>

          <div className="landing-cta">
            <button className="landing-primary-btn" onClick={onGetStarted}>
              <Mic size={20} />
              बोलकर पूछें
              <ArrowRight size={18} />
            </button>
            <button className="landing-secondary-btn" onClick={onLogin}>
              <Search size={18} />
              Explore Schemes
            </button>
          </div>

          <div className="landing-trust">
            <div>
              <ShieldCheck size={17} />
              Secure & Private
            </div>
            <div>
              <Languages size={17} />
              Hindi & English
            </div>
          </div>
        </div>

        {/* ── Visual ── */}
        <div className="landing-visual">
          <div className="voice-preview-card">
            <div className="voice-preview-header">
              <span className="online-dot" />
              Jan Vaani Assistant
            </div>

            {/* Rural scene */}
            <div style={{ position: 'relative', marginBottom: '8px' }}>
              {/* Decorative rural image */}
              <svg viewBox="0 0 300 140" style={{ width: '100%', maxHeight: '120px' }} fill="none">
                {/* Sky background */}
                <rect width="300" height="140" fill="#FEF9F0" rx="12"/>
                {/* Sun */}
                <circle cx="260" cy="28" r="18" fill="#F5A623" opacity="0.7"/>
                {/* Hills */}
                <ellipse cx="60" cy="135" rx="70" ry="35" fill="#2D6A4F" opacity="0.15"/>
                <ellipse cx="220" cy="140" rx="90" ry="40" fill="#52B788" opacity="0.12"/>
                {/* Tree 1 */}
                <rect x="38" y="88" width="5" height="30" fill="#A0663A"/>
                <ellipse cx="40" cy="82" rx="14" ry="18" fill="#2D6A4F" opacity="0.85"/>
                {/* Tree 2 */}
                <rect x="255" y="95" width="4" height="22" fill="#A0663A"/>
                <ellipse cx="257" cy="90" rx="11" ry="14" fill="#52B788" opacity="0.85"/>
                {/* Farmer */}
                <circle cx="90" cy="88" r="8" fill="#FDBF6F"/>
                <path d="M82 85 Q90 76 98 85" fill="#D4720C"/>
                <path d="M84 96 Q90 92 96 96 L98 112 L82 112 Z" fill="#E8803A"/>
                <path d="M84 99 Q80 105 76 108" stroke="#FDBF6F" strokeWidth="4" strokeLinecap="round" fill="none"/>
                {/* Woman */}
                <circle cx="200" cy="90" r="8" fill="#FDBF6F"/>
                <circle cx="200" cy="82" r="5" fill="#3D2B1F"/>
                <ellipse cx="200" cy="78" rx="9" ry="5" fill="#C1440E"/>
                <path d="M193 98 Q200 93 207 98 L209 116 L191 116 Z" fill="#C1440E"/>
                {/* Ground */}
                <rect x="0" y="116" width="300" height="24" fill="#2D6A4F" opacity="0.12" rx="4"/>
              </svg>
            </div>

            <div className="voice-mic-area">
              <div className="voice-ring ring-one" />
              <div className="voice-ring ring-two" />
              <div className="voice-mic">
                <Mic size={38} />
              </div>
            </div>

            <h3>बोलिए, हम सुन रहे हैं</h3>
            <p>"मुझे किसानों के लिए सरकारी योजना बताइए"</p>

            <div className="voice-wave">
              <span /><span /><span /><span /><span />
              <span /><span /><span /><span />
            </div>
          </div>
        </div>
      </main>

      {/* ── Features ── */}
      <section className="landing-features">
        <div className="landing-feature">
          <div className="feature-icon"><Mic size={21} /></div>
          <div>
            <h3>आवाज़ से पूछें</h3>
            <p>लंबे फॉर्म भरने की जरूरत नहीं — बस बोलें।</p>
          </div>
        </div>

        <div className="landing-feature">
          <div className="feature-icon"><Search size={21} /></div>
          <div>
            <h3>योजनाएँ खोजें</h3>
            <p>अपनी जरूरत के अनुसार सरकारी योजनाएँ खोजें।</p>
          </div>
        </div>

        <div className="landing-feature">
          <div className="feature-icon"><ShieldCheck size={21} /></div>
          <div>
            <h3>पात्रता जाँचें</h3>
            <p>जानें कि आप कौन सी योजनाओं के लिए योग्य हैं।</p>
          </div>
        </div>
      </section>

    </div>
  );
}