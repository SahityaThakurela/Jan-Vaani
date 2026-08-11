import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, Square, PhoneOff, Sparkles, 
  CheckCircle2, AlertTriangle, Headphones, LogOut, User
} from 'lucide-react';
import Login from './pages/Login';
import Register from './pages/Register';
import './index.css';
import Landing from './pages/Landing';

const API_BASE = 'http://localhost:8000';

// ── Auth helpers ──────────────────────────────────────────────
function getToken() {
  return localStorage.getItem('jv_token') || null;
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('jv_user') || 'null');
  } catch {
    return null;
  }
}

function authHeaders(extra = {}) {
  const token = getToken();
  return token
    ? { Authorization: `Bearer ${token}`, ...extra }
    : extra;
}

export default function App() {
  // Auth state
  const [authUser, setAuthUser] = useState(getStoredUser);
  const [authView, setAuthView] = useState('landing');

  // App state
  const [language, setLanguage] = useState('hi');
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('idle');
  const [turns, setTurns] = useState([]);
  const [profile, setProfile] = useState({});
  const [latestEligibility, setLatestEligibility] = useState(null);
  const [crossMatches, setCrossMatches] = useState([]);
  const [handoffData, setHandoffData] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const transcriptEndRef = useRef(null);

  // Initialize session on language change (only when authenticated)
  useEffect(() => {
    if (authUser) {
      initSession(language);
    }
  }, [language, authUser?.user_id]);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const handleAuthSuccess = (data) => {
    setAuthUser({ user_id: data.user_id, email: data.email, full_name: data.full_name });
  };

  const handleLogout = () => {
    localStorage.removeItem('jv_token');
    localStorage.removeItem('jv_user');
    setAuthUser(null);
    setSessionId(null);
    setTurns([]);
    setProfile({});
    setLatestEligibility(null);
    setCrossMatches([]);
    setHandoffData(null);
  };

  const initSession = async (lang) => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ language: lang }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 401) { handleLogout(); return; }
        console.error('Session init error:', data);
        return;
      }
      setSessionId(data.session_id);
      setTurns([]);
      setProfile({});
      setLatestEligibility(null);
      setCrossMatches([]);
      setHandoffData(null);
    } catch (err) {
      console.error('Session init failed:', err);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioTurn(audioBlob);
      };

      mediaRecorderRef.current.start(); // collect data when stopped
      setRecording(true);
      setStatus('listening');
    } catch (err) {
      console.error('Mic access denied or error:', err);
      alert('Microphone access is required for voice interaction. Please allow mic access in your browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      setStatus('processing');
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const sendAudioTurn = async (audioBlob) => {
    if (!sessionId) return;
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('language', language);
    formData.append('audio', audioBlob, 'turn.webm');

    try {
      const res = await fetch(`${API_BASE}/voice/turn`, {
        method: 'POST',
        headers: authHeaders(),   // no Content-Type — multipart handled by browser
        body: formData,
      });

      if (res.status === 401) { handleLogout(); return; }
      if (!res.ok) {
        const err = await res.json();
        console.error('Voice turn error:', err);
        setStatus('idle');
        return;
      }
      const data = await res.json();

      setTurns((prev) => [
        ...prev,
        {
          id: data.turn_id,
          userText: data.user_transcript,
          agentText: data.agent_text,
          action: data.action_taken,
        },
      ]);

      if (data.slots_extracted) {
        setProfile((prev) => ({ ...prev, ...data.slots_extracted }));
      }
      if (data.eligibility_result) {
        setLatestEligibility(data.eligibility_result);
      }
      if (data.cross_scheme_matches) {
        setCrossMatches(data.cross_scheme_matches);
      }
      if (data.handoff_triggered) {
        fetchHandoff(sessionId);
      }

      // Play Rime Coda TTS audio
      if (data.audio_b64) {
        setStatus('speaking');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
        audio.play().catch(() => {}); // ignore autoplay policy errors
        audio.onended = () => setStatus('idle');
      } else {
        setStatus('idle');
      }
    } catch (err) {
      console.error('Voice turn processing error:', err);
      setStatus('idle');
    }
  };

  const handleInterrupt = async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/voice/interrupt`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ session_id: sessionId }),
      });
      setStatus('idle');
      setTurns((prev) => [
        ...prev,
        {
          id: Date.now(),
          userText: '[Interrupted]',
          agentText: language === 'hi' 
            ? 'बातचीत रोकी गई। अब आप कुछ नया पूछ सकते हैं।'
            : 'Process interrupted. What would you like to do next?',
          action: 'INTERRUPT',
        },
      ]);
    } catch (err) {
      console.error('Interrupt failed:', err);
    }
  };

  const fetchHandoff = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/handoff/session/${sid}`, {
        headers: authHeaders(),
      });
      const list = await res.json();
      if (list && list.length > 0) {
        setHandoffData(list[list.length - 1]);
      }
    } catch (err) {
      console.error('Fetch handoff failed:', err);
    }
  };

  // ── Auth guard ─────────────────────────────────────────────
if (!authUser) {

  if (authView === 'landing') {
    return (
      <Landing
        onGetStarted={() => setAuthView('register')}
        onLogin={() => setAuthView('login')}
      />
    );
  }

  if (authView === 'login') {
    return (
      <Login
        onAuthSuccess={handleAuthSuccess}
        onGoRegister={() => setAuthView('register')}
      />
    );
  }

  return (
    <Register
      onAuthSuccess={handleAuthSuccess}
      onGoLogin={() => setAuthView('login')}
    />
  );
}

  // ── Main App UI ────────────────────────────────────────────
  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles className="w-6 h-6 text-white" size={22} />
          </div>
          <div className="brand-title">
            <h1>Jan Vaani</h1>
            <p>janvaani.ai • StarForge Hackathon 2026</p>
          </div>
        </div>

        <div className="navbar-right">
          <div className="lang-selector">
            <button 
              className={`lang-btn ${language === 'hi' ? 'active' : ''}`}
              onClick={() => setLanguage('hi')}
            >
              हिंदी
            </button>
            <button 
              className={`lang-btn ${language === 'en' ? 'active' : ''}`}
              onClick={() => setLanguage('en')}
            >
              English
            </button>
          </div>

          {/* User info + logout */}
          <div className="user-pill">
            <User size={14} />
            <span className="user-pill-name">
              {authUser.full_name || authUser.email.split('@')[0]}
            </span>
            <button
              id="logout-btn"
              className="logout-btn"
              onClick={handleLogout}
              title="Sign out"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="main-grid">
        {/* Left — Voice Interface & Transcript */}
        <div className="workspace">
          <div className="glass-panel voice-hero">
            {/* Status Chip */}
            <div className={`status-chip ${status}`}>
              <div className="status-dot" />
              <span>
                {status === 'idle' && (language === 'hi' ? 'बोलने के लिए माइक दबाएं' : 'Hold Mic to Speak')}
                {status === 'listening' && (language === 'hi' ? 'सुन रहे हैं...' : 'Listening...')}
                {status === 'processing' && (language === 'hi' ? 'सोच रहे हैं (Gemini & Engine)...' : 'Thinking (Gemini & Rules)...')}
                {status === 'speaking' && (language === 'hi' ? 'बोल रहे हैं (Rime Coda)...' : 'Speaking (Rime Coda)...')}
              </span>
            </div>

            {/* Mic Push-to-Talk */}
            <div className="mic-button-wrapper">
              {recording && <div className="mic-ripple" />}
              <button 
                id="mic-btn"
                className={`mic-btn ${recording ? 'active' : ''}`}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
                onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
              >
                {recording ? <Square size={34} /> : <Mic size={42} />}
              </button>
            </div>

            <p className="mic-hint">
              {language === 'hi'
                ? 'दबाकर रखें → बोलें → छोड़ें'
                : 'Hold → Speak → Release'}
            </p>

            {/* Interrupt Button */}
            <button id="interrupt-btn" className="interrupt-btn" onClick={handleInterrupt}>
              <PhoneOff size={14} />
              <span>Tap to Interrupt</span>
            </button>
          </div>

          {/* Transcript Panel */}
          <div className="glass-panel transcript-panel">
            <h3 className="panel-title">
              {language === 'hi' ? '💬 बातचीत' : '💬 Conversation'}
            </h3>
            <div className="transcript-box">
              {turns.length === 0 ? (
                <div className="transcript-empty">
                  <Mic size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
                  <p>{language === 'hi'
                    ? 'माइक दबाएं और सरकारी योजनाओं के बारे में पूछें!'
                    : 'Hold the mic and ask about welfare schemes or check eligibility!'}</p>
                </div>
              ) : (
                turns.map((t) => (
                  <div key={t.id} className="turn-card">
                    {t.userText && (
                      <div className="chat-bubble user">{t.userText}</div>
                    )}
                    {t.agentText && (
                      <div className={`chat-bubble agent ${language === 'hi' ? 'hindi-text' : ''}`}>
                        {t.agentText}
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={transcriptEndRef} />
            </div>
          </div>
        </div>

        {/* Right — Dashboard */}
        <div className="side-panel">
          {/* Profile Slots */}
          <div className="glass-panel">
            <h3 className="panel-title" style={{ color: '#ff8c38' }}>
              📋 {language === 'hi' ? 'आपकी जानकारी' : 'Extracted Profile'}
            </h3>
            <div className="slot-list">
              {Object.keys(profile).length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '12px 0' }}>
                  {language === 'hi' ? 'अभी कोई जानकारी नहीं मिली।' : 'No facts collected yet.'}
                </p>
              ) : (
                Object.entries(profile).map(([k, v]) => (
                  <div key={k} className="slot-item">
                    <span className="slot-name">{k.replace(/_/g, ' ')}</span>
                    <span className="slot-val">{String(v)}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Eligibility Result */}
          {latestEligibility && (
            <div className={`glass-panel result-banner ${latestEligibility.eligible ? '' : 'ineligible'}`}>
              <div className="result-header">
                {latestEligibility.eligible
                  ? <CheckCircle2 size={24} color="#10b981" />
                  : <AlertTriangle size={24} color="#ef4444" />}
                <div>
                  <div className="result-title">{latestEligibility.scheme_name}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Rules passed: {latestEligibility.matched_rules} / {latestEligibility.total_rules}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.85rem', marginTop: 8, lineHeight: 1.5 }}>
                {latestEligibility.explanation}
              </p>
              {latestEligibility.eligible && (
                <div className="eligible-badge">✅ Eligible</div>
              )}
            </div>
          )}

          {/* Cross-scheme matches */}
          {crossMatches.length > 0 && (
            <div className="glass-panel">
              <h4 className="panel-title" style={{ color: '#10b981', fontSize: '0.9rem' }}>
                🔗 {language === 'hi' ? 'अन्य योजनाएं' : 'Cross-Scheme Matches'}
              </h4>
              {crossMatches.map((m) => (
                <div key={m.scheme_id} className="cross-match-item">
                  <strong style={{ color: 'var(--text-main)' }}>{m.scheme_name}</strong>
                  <span className={`cross-badge ${m.eligible ? 'eligible' : 'ineligible'}`}>
                    {m.eligible ? `✅ Qualifies` : `${m.matched_rules}/${m.total_rules}`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Session Info */}
          {sessionId && (
            <div className="glass-panel session-info-card">
              <p className="session-label">Session ID</p>
              <p className="session-id">{sessionId.slice(0, 16)}…</p>
              <button
                id="new-session-btn"
                className="new-session-btn"
                onClick={() => initSession(language)}
              >
                Start New Session
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Human Handoff Modal */}
      {handoffData && (
        <div className="handoff-overlay" onClick={() => setHandoffData(null)}>
          <div className="handoff-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <Headphones size={32} color="#ff8c38" />
              <div>
                <h2 style={{ fontSize: '1.2rem', color: '#fff' }}>Safe Human Handoff Triggered</h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Reason: {handoffData.reason}
                </p>
              </div>
            </div>
            <pre className="handoff-json">
              {JSON.stringify(handoffData.summary, null, 2)}
            </pre>
            <button className="close-btn" onClick={() => setHandoffData(null)}>
              Dismiss Handoff Screen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
