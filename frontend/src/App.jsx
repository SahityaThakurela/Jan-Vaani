import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic, Square, PhoneOff, Sparkles,
  CheckCircle2, AlertTriangle, Headphones, LogOut, User,
  Zap, Activity, Radio, ChevronRight, StopCircle, History, X,
  MessageSquare, Clock
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
  try { return JSON.parse(localStorage.getItem('jv_user') || 'null'); }
  catch { return null; }
}
function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}`, ...extra } : extra;
}

// ── Slot icon map ─────────────────────────────────────────────
const SLOT_ICONS = {
  age: '🎂', gender: '👤', income: '💰', state: '🗺️',
  caste: '📋', occupation: '💼', land: '🌾', scheme: '📜',
  name: '✦', default: '◆'
};
function getSlotIcon(key) {
  const k = key.toLowerCase();
  for (const [kw, icon] of Object.entries(SLOT_ICONS)) {
    if (k.includes(kw)) return icon;
  }
  return SLOT_ICONS.default;
}

// ── Format date helper ────────────────────────────────────────
// Backend stores datetimes as UTC but isoformat() has no 'Z' suffix.
// Append 'Z' to force UTC interpretation → browser converts to local time.
function formatDate(isoStr) {
  if (!isoStr) return '';
  const utcStr = isoStr.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(isoStr)
    ? isoStr
    : isoStr + 'Z';
  const d = new Date(utcStr);
  return d.toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
}

// ── Waveform component ────────────────────────────────────────
function Waveform() {
  return (
    <div className="waveform">
      {[...Array(7)].map((_, i) => (
        <div key={i} className="wave-bar" />
      ))}
    </div>
  );
}

export default function App() {
  // Auth state
  const [authUser, setAuthUser] = useState(getStoredUser);
  const [authView, setAuthView] = useState('login');

  // App state
  const [language, setLanguage] = useState('hi');
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | listening | processing | speaking
  const [turns, setTurns] = useState([]);
  const [profile, setProfile] = useState({});
  const [latestEligibility, setLatestEligibility] = useState(null);
  const [crossMatches, setCrossMatches] = useState([]);
  const [handoffData, setHandoffData] = useState(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [endingChat, setEndingChat] = useState(false);

  // History panel state
  const [showHistory, setShowHistory] = useState(false);
  const [pastSessions, setPastSessions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Transcript viewer state
  const [viewingSession, setViewingSession] = useState(null); // {session, profile, turns}
  const [viewLoading, setViewLoading] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const transcriptEndRef = useRef(null);

  useEffect(() => {
    if (authUser) initSession(language);
  }, [language, authUser?.user_id]);

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
    setShowHistory(false);
    setPastSessions([]);
  };

  // ── Load profile from DB for a session ───────────────────────
  const loadProfileFromDB = useCallback(async (sid) => {
    if (!sid) return;
    try {
      const res = await fetch(`${API_BASE}/sessions/${sid}`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      if (data.profile && data.profile.length > 0) {
        const profileMap = {};
        data.profile.forEach(slot => {
          profileMap[slot.slot_name] = slot.value;
        });
        setProfile(profileMap);
      }
    } catch (err) {
      console.error('Profile load failed:', err);
    }
  }, []);

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
        return;
      }
      setSessionId(data.session_id);
      setTurns([]);
      setProfile({});
      setLatestEligibility(null);
      setCrossMatches([]);
      setHandoffData(null);
      // Load any existing profile slots for this new session (usually empty)
      await loadProfileFromDB(data.session_id);
    } catch (err) {
      console.error('Session init failed:', err);
    }
  };

  // ── End Chat ─────────────────────────────────────────────────
  const handleEndChat = async () => {
    if (!sessionId || endingChat) return;
    setEndingChat(true);
    try {
      await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
    } catch (err) {
      console.error('End session failed:', err);
    }
    // Reset and start a new session
    setTurns([]);
    setProfile({});
    setLatestEligibility(null);
    setCrossMatches([]);
    setHandoffData(null);
    setSessionId(null);
    setEndingChat(false);
    await initSession(language);
  };

  // ── History panel ─────────────────────────────────────────────
  const openHistory = async () => {
    setShowHistory(true);
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/sessions`, { headers: authHeaders() });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) {
        const data = await res.json();
        setPastSessions(data);
      }
    } catch (err) {
      console.error('History load failed:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const closeHistory = () => {
    setShowHistory(false);
    setViewingSession(null);
  };

  const openSessionTranscript = async (sid) => {
    setViewLoading(true);
    setViewingSession({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/sessions/${sid}`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      setViewingSession(data);
    } catch (err) {
      console.error('Session detail load failed:', err);
      setViewingSession(null);
    } finally {
      setViewLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus' : 'audio/webm';
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioTurn(audioBlob);
      };
      mediaRecorderRef.current.start();
      setRecording(true);
      setStatus('listening');
    } catch (err) {
      console.error('Mic error:', err);
      alert('Microphone access is required. Please allow mic access in your browser.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      setStatus('processing');
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
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
        headers: authHeaders(),
        body: formData,
      });
      if (res.status === 401) { handleLogout(); return; }
      if (!res.ok) { setStatus('idle'); return; }
      const data = await res.json();
      setTurns(prev => [...prev, {
        id: data.turn_id,
        userText: data.user_transcript,
        agentText: data.agent_text,
        action: data.action_taken,
      }]);
      // Merge slots from live response
      if (data.slots_extracted) setProfile(prev => ({ ...prev, ...data.slots_extracted }));
      if (data.eligibility_result) setLatestEligibility(data.eligibility_result);
      if (data.cross_scheme_matches) setCrossMatches(data.cross_scheme_matches);
      if (data.handoff_triggered) fetchHandoff(sessionId);

      // Always re-fetch profile from DB after each turn to catch any DB-persisted slots
      await loadProfileFromDB(sessionId);

      if (data.audio_b64) {
        setStatus('speaking');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
        audio.play().catch(() => {});
        audio.onended = () => setStatus('idle');
      } else {
        setStatus('idle');
      }
    } catch (err) {
      console.error('Voice turn error:', err);
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
      setTurns(prev => [...prev, {
        id: Date.now(),
        userText: '[Interrupted]',
        agentText: language === 'hi'
          ? 'बातचीत रोकी गई। अब आप कुछ नया पूछ सकते हैं।'
          : 'Process interrupted. What would you like to do next?',
        action: 'INTERRUPT',
      }]);
    } catch (err) {
      console.error('Interrupt failed:', err);
    }
  };

  const fetchHandoff = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/handoff/session/${sid}`, { headers: authHeaders() });
      const list = await res.json();
      if (list && list.length > 0) setHandoffData(list[list.length - 1]);
    } catch (err) {
      console.error('Fetch handoff failed:', err);
    }
  };

  // ── Status label helper ──────────────────────────────────────
  const statusLabel = {
    idle:       language === 'hi' ? 'बोलने के लिए माइक दबाएं'        : 'Hold Mic to Speak',
    listening:  language === 'hi' ? 'सुन रहे हैं…'                  : 'Listening…',
    processing: language === 'hi' ? 'सोच रहे हैं (Gemini & Engine)…' : 'Thinking (Gemini & Rules)…',
    speaking:   language === 'hi' ? 'बोल रहे हैं (Rime Coda)…'      : 'Speaking (Rime Coda)…',
  }[status];

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

      {/* ── Navbar ── */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles size={20} color="#003824" strokeWidth={2.5} />
          </div>
          <div className="brand-title">
            <h1>Jan Vaani</h1>
            <p>Voice AI for Welfare Schemes · StarForge 2026</p>
          </div>
        </div>

        <div className="navbar-right">
          <div className="lang-selector">
            <button
              id="lang-hi"
              className={`lang-btn ${language === 'hi' ? 'active' : ''}`}
              onClick={() => setLanguage('hi')}
            >हिंदी</button>
            <button
              id="lang-en"
              className={`lang-btn ${language === 'en' ? 'active' : ''}`}
              onClick={() => setLanguage('en')}
            >English</button>
          </div>

          {/* Previous Chats button */}
          <button
            id="history-btn"
            className={`history-toggle-btn ${showHistory ? 'active' : ''}`}
            onClick={showHistory ? closeHistory : openHistory}
            title="View previous chats"
          >
            <History size={14} />
            <span>{language === 'hi' ? 'पिछली चैट' : 'Previous Chats'}</span>
          </button>

          <div className="user-pill">
            <User size={13} />
            <span className="user-pill-name">
              {authUser.full_name || authUser.email.split('@')[0]}
            </span>
            <button id="logout-btn" className="logout-btn" onClick={() => setShowLogoutConfirm(true)} title="Sign out">
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Grid ── */}
      <div className="main-grid">

        {/* ── Left: Voice + Transcript ── */}
        <div className="workspace">

          {/* Voice Hero */}
          <div className="glass-panel voice-hero">

            {/* Status chip */}
            <div className={`status-chip ${status}`}>
              <div className="status-dot" />
              <span>{statusLabel}</span>
            </div>

            {/* Mic button + rings */}
            <div className="mic-button-wrapper">

              {/* Idle breathing rings */}
              {status === 'idle' && (
                <>
                  <div className="mic-ring-idle" />
                  <div className="mic-ring-idle" />
                  <div className="mic-ring-idle" />
                </>
              )}

              {/* Recording ripple rings */}
              {status === 'listening' && (
                <>
                  <div className="mic-ripple" />
                  <div className="mic-ripple" />
                  <div className="mic-ripple" />
                </>
              )}

              {/* Processing spinner ring */}
              {status === 'processing' && <div className="mic-spinner-ring" />}

              {/* Speaking waveform */}
              {status === 'speaking' && <Waveform />}

              {/* The mic button itself (hidden behind waveform when speaking) */}
              {status !== 'speaking' && (
                <button
                  id="mic-btn"
                  className={`mic-btn ${recording ? 'active' : ''} ${status === 'processing' ? 'processing' : ''}`}
                  onMouseDown={status === 'idle' ? startRecording : undefined}
                  onMouseUp={status === 'listening' ? stopRecording : undefined}
                  onTouchStart={(e) => { if (status === 'idle') { e.preventDefault(); startRecording(); } }}
                  onTouchEnd={(e) => { if (status === 'listening') { e.preventDefault(); stopRecording(); } }}
                  disabled={status === 'processing'}
                >
                  {recording ? <Square size={32} /> : <Mic size={40} />}
                </button>
              )}
            </div>

            <p className="mic-hint">
              {language === 'hi' ? 'दबाकर रखें → बोलें → छोड़ें' : 'Hold → Speak → Release'}
            </p>

            <button id="interrupt-btn" className="interrupt-btn" onClick={handleInterrupt}>
              <PhoneOff size={13} />
              <span>{language === 'hi' ? 'रोकें' : 'Interrupt'}</span>
            </button>
          </div>

          {/* Transcript Panel */}
          <div className="glass-panel transcript-panel">
            <h3 className="panel-title">
              <Activity size={15} className="text-teal" />
              {language === 'hi' ? 'बातचीत' : 'Conversation'}
            </h3>
            <div className="transcript-box">
              {turns.length === 0 ? (
                <div className="transcript-empty">
                  <div className="transcript-empty-icon">
                    <Mic size={22} />
                  </div>
                  <p>
                    {language === 'hi'
                      ? 'माइक दबाएं और सरकारी योजनाओं के बारे में पूछें!'
                      : 'Hold the mic and ask about welfare schemes or check eligibility!'}
                  </p>
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

        {/* ── Right: Dashboard ── */}
        <div className="side-panel">

          {/* Profile Slots */}
          <div className="glass-panel">
            <h3 className="panel-title">
              <Radio size={14} className="text-saffron" />
              <span className="text-saffron">
                {language === 'hi' ? 'आपकी जानकारी' : 'Extracted Profile'}
              </span>
            </h3>
            <div className="slot-list">
              {Object.keys(profile).length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.83rem', textAlign: 'center', padding: '14px 0', lineHeight: 1.6 }}>
                  {language === 'hi' ? 'अभी कोई जानकारी नहीं मिली।' : 'No facts collected yet.'}
                </p>
              ) : (
                Object.entries(profile).map(([k, v]) => (
                  <div key={k} className="slot-item">
                    <span className="slot-name">
                      <span style={{ marginRight: 6 }}>{getSlotIcon(k)}</span>
                      {k.replace(/_/g, ' ')}
                    </span>
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
                  ? <CheckCircle2 size={22} color="var(--teal)" />
                  : <AlertTriangle size={22} color="var(--crimson)" />}
                <div>
                  <div className="result-title">{latestEligibility.scheme_name}</div>
                  <div className="result-meta">
                    Rules: {latestEligibility.matched_rules} / {latestEligibility.total_rules} passed
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.83rem', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                {latestEligibility.explanation}
              </p>
              {latestEligibility.eligible && (
                <div className="eligible-badge">
                  <CheckCircle2 size={12} />
                  Eligible
                </div>
              )}
            </div>
          )}

          {/* Cross-scheme matches */}
          {crossMatches.length > 0 && (
            <div className="glass-panel">
              <h4 className="panel-title" style={{ color: 'var(--teal)', fontSize: '0.88rem' }}>
                <Zap size={13} className="text-teal" />
                {language === 'hi' ? 'अन्य योजनाएं' : 'Cross-Scheme Matches'}
              </h4>
              {crossMatches.map((m) => (
                <div key={m.scheme_id} className="cross-match-item">
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.82rem' }}>{m.scheme_name}</span>
                  <span className={`cross-badge ${m.eligible ? 'eligible' : 'ineligible'}`}>
                    {m.eligible ? `✓ Qualifies` : `${m.matched_rules}/${m.total_rules}`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Session Info + End Chat */}
          {sessionId && (
            <div className="glass-panel session-info-card">
              <p className="session-label">Session ID</p>
              <p className="session-id">{sessionId.slice(0, 18)}…</p>
              <button
                id="new-session-btn"
                className="new-session-btn"
                onClick={() => initSession(language)}
              >
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                  <ChevronRight size={14} />
                  {language === 'hi' ? 'नया सत्र शुरू करें' : 'Start New Session'}
                </span>
              </button>

              {/* End Chat Button */}
              <button
                id="end-chat-btn"
                className="end-chat-btn"
                onClick={handleEndChat}
                disabled={endingChat || turns.length === 0}
                title={turns.length === 0 ? 'No conversation to save' : 'End this chat and save it'}
              >
                <StopCircle size={14} />
                {endingChat
                  ? (language === 'hi' ? 'सहेजा जा रहा है…' : 'Saving…')
                  : (language === 'hi' ? 'चैट समाप्त करें और सहेजें' : 'End Chat & Save')
                }
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Human Handoff Modal ── */}
      {handoffData && (
        <div className="handoff-overlay" onClick={() => setHandoffData(null)}>
          <div className="handoff-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
              <div style={{
                width: 48, height: 48, borderRadius: 14,
                background: 'rgba(255,140,56,0.12)',
                border: '1px solid rgba(255,140,56,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0
              }}>
                <Headphones size={24} color="var(--saffron)" />
              </div>
              <div>
                <h2 style={{ fontSize: '1.15rem', color: 'var(--text-white)', fontWeight: 800 }}>
                  Human Handoff Triggered
                </h2>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 3 }}>
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

      {/* ── Logout Confirmation Modal ── */}
      {showLogoutConfirm && (
        <div className="handoff-overlay" onClick={() => setShowLogoutConfirm(false)}>
          <div className="handoff-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '400px', textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--text-white)', fontWeight: 800, marginBottom: '8px' }}>
              {language === 'hi' ? 'लॉगआउट करें?' : 'Logout?'}
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
              {language === 'hi' ? 'क्या आप वाकई लॉगआउट करना चाहते हैं?' : 'Are you sure you want to logout?'}
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                className="close-btn"
                style={{ marginTop: 0, flex: 1 }}
                onClick={() => setShowLogoutConfirm(false)}
              >
                {language === 'hi' ? 'रद्द करें' : 'Cancel'}
              </button>
              <button
                className="close-btn"
                style={{ marginTop: 0, flex: 1, background: 'rgba(255, 90, 90, 0.12)', borderColor: 'rgba(255, 90, 90, 0.3)', color: '#ff9090' }}
                onClick={() => {
                  setShowLogoutConfirm(false);
                  handleLogout();
                }}
              >
                {language === 'hi' ? 'लॉगआउट' : 'Logout'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Previous Chats Drawer ── */}
      {showHistory && (
        <>
          <div className="history-overlay" onClick={closeHistory} />
          <div className="history-drawer">
            <div className="history-drawer-header">
              <div className="history-drawer-title">
                <History size={18} color="var(--indigo)" />
                {language === 'hi' ? 'पिछली चैट' : 'Previous Chats'}
              </div>
              <button className="history-drawer-close" onClick={closeHistory}>
                <X size={16} />
              </button>
            </div>

            <div className="history-list">
              {historyLoading ? (
                <div className="history-empty">
                  <div className="history-empty-icon">⏳</div>
                  <p style={{ fontSize: '0.85rem' }}>
                    {language === 'hi' ? 'लोड हो रहा है…' : 'Loading sessions…'}
                  </p>
                </div>
              ) : pastSessions.length === 0 ? (
                <div className="history-empty">
                  <div className="history-empty-icon">💬</div>
                  <p style={{ fontSize: '0.85rem' }}>
                    {language === 'hi'
                      ? 'अभी कोई पिछली चैट नहीं है।'
                      : 'No previous chats found.'}
                  </p>
                </div>
              ) : (
                pastSessions.map((s) => (
                  <div
                    key={s.session_id}
                    className={`history-session-card ${s.session_id === sessionId ? 'current' : ''}`}
                    onClick={() => openSessionTranscript(s.session_id)}
                  >
                    <div className={`history-session-icon ${s.status === 'completed' ? 'completed' : ''}`}>
                      {s.status === 'completed' ? '✅' : '💬'}
                    </div>
                    <div className="history-session-info">
                      <div className="history-session-date">
                        {s.session_id === sessionId
                          ? `⚡ ${language === 'hi' ? 'वर्तमान सत्र' : 'Current Session'}`
                          : formatDate(s.created_at)
                        }
                      </div>
                      <div className="history-session-meta">
                        <span className={`history-session-badge ${s.status}`}>
                          {s.status}
                        </span>
                        <span className="history-session-turns">
                          <MessageSquare size={10} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 3 }} />
                          {s.turn_count} {language === 'hi' ? 'बातें' : 'turns'}
                        </span>
                        <span className="history-session-turns">
                          {s.language === 'hi' ? '🇮🇳 हिंदी' : '🇬🇧 English'}
                        </span>
                      </div>
                    </div>
                    <ChevronRight size={14} color="var(--text-muted)" />
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}

      {/* ── Session Transcript Viewer Modal ── */}
      {viewingSession && (
        <div className="transcript-modal-overlay" onClick={() => setViewingSession(null)}>
          <div className="transcript-modal" onClick={(e) => e.stopPropagation()}>
            <div className="transcript-modal-header">
              <div>
                <div className="transcript-modal-title">
                  {viewingSession.loading
                    ? (language === 'hi' ? 'लोड हो रहा है…' : 'Loading…')
                    : `${language === 'hi' ? 'चैट' : 'Chat'} — ${viewingSession.session?.session_id?.slice(0, 16)}…`
                  }
                </div>
                {!viewingSession.loading && viewingSession.session && (
                  <div className="transcript-modal-subtitle">
                    <Clock size={11} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
                    {formatDate(viewingSession.session.created_at)}
                    {' · '}
                    {viewingSession.session.language === 'hi' ? '🇮🇳 Hindi' : '🇬🇧 English'}
                    {' · '}
                    <span style={{ textTransform: 'capitalize' }}>{viewingSession.session.status}</span>
                    {' · '}
                    {viewingSession.turns?.length || 0} {language === 'hi' ? 'बातें' : 'turns'}
                  </div>
                )}
              </div>
              <button className="history-drawer-close" onClick={() => setViewingSession(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="transcript-modal-body">
              {viewingSession.loading ? (
                <div className="transcript-loading">
                  <span>⏳</span>
                  <span>{language === 'hi' ? 'बातचीत लोड हो रही है…' : 'Loading conversation…'}</span>
                </div>
              ) : (
                <>
                  {/* Profile slots section */}
                  {viewingSession.profile && viewingSession.profile.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <p style={{
                        fontSize: '0.72rem', fontWeight: 700, letterSpacing: '1px',
                        textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8
                      }}>
                        {language === 'hi' ? '📋 एकत्रित जानकारी' : '📋 Collected Profile'}
                      </p>
                      {viewingSession.profile.map(slot => (
                        <div key={slot.slot_name} className="profile-slot-row">
                          <span className="profile-slot-row-name">
                            {getSlotIcon(slot.slot_name)} {slot.slot_name.replace(/_/g, ' ')}
                          </span>
                          <span className="profile-slot-row-val">{slot.value}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Conversation turns */}
                  {(!viewingSession.turns || viewingSession.turns.length === 0) ? (
                    <div className="transcript-empty" style={{ padding: '30px 0' }}>
                      <div className="transcript-empty-icon">
                        <Mic size={20} />
                      </div>
                      <p style={{ fontSize: '0.85rem' }}>
                        {language === 'hi' ? 'इस सत्र में कोई बातचीत नहीं हुई।' : 'No conversations in this session.'}
                      </p>
                    </div>
                  ) : (
                    viewingSession.turns.map((t) => (
                      <div key={t.turn_id} className="turn-card">
                        {t.user_text && (
                          <div className="chat-bubble user">{t.user_text}</div>
                        )}
                        {t.agent_text && (
                          <div className={`chat-bubble agent ${viewingSession.session?.language === 'hi' ? 'hindi-text' : ''}`}>
                            {t.agent_text}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </>
              )}
            </div>

            <div className="transcript-modal-footer">
              <button className="modal-close-btn" onClick={() => setViewingSession(null)}>
                {language === 'hi' ? 'बंद करें' : 'Close'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
