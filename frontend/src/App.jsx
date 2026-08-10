import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, Square, PhoneOff, Globe, Sparkles, 
  CheckCircle2, AlertTriangle, Headphones, HelpCircle, RefreshCw 
} from 'lucide-react';
import './index.css';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [language, setLanguage] = useState('hi');
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | listening | processing | speaking
  const [turns, setTurns] = useState([]);
  const [profile, setProfile] = useState({});
  const [latestEligibility, setLatestEligibility] = useState(null);
  const [crossMatches, setCrossMatches] = useState([]);
  const [handoffData, setHandoffData] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Initialize session on mount or language change
  useEffect(() => {
    initSession(language);
  }, [language]);

  const initSession = async (lang) => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang }),
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setTurns([]);
      setProfile({});
      setLatestEligibility(null);
      setCrossMatches([]);
      setHandoffData(null);
      console.log('Session initialized:', data.session_id);
    } catch (err) {
      console.error('Session init failed:', err);
    }
  };

  // Start recording audio from browser mic
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
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

      mediaRecorderRef.current.start();
      setRecording(true);
      setStatus('listening');
    } catch (err) {
      console.error('Mic access denied or error:', err);
      alert('Microphone access is required for voice interaction.');
    }
  };

  // Stop recording and send audio to backend
  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
      setStatus('processing');
      // Stop stream tracks
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  // Send turn audio to POST /voice/turn
  const sendAudioTurn = async (audioBlob) => {
    if (!sessionId) return;
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('language', language);
    formData.append('audio', audioBlob, 'turn.webm');

    try {
      const res = await fetch(`${API_BASE}/voice/turn`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Voice turn request failed');
      const data = await res.json();

      // Append user turn & agent reply to transcript stream
      setTurns((prev) => [
        ...prev,
        { id: data.turn_id, userText: data.user_transcript, agentText: data.agent_text, action: data.action_taken }
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

      // Play returned Rime Coda audio if available
      if (data.audio_b64) {
        setStatus('speaking');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
        audio.play();
        audio.onended = () => setStatus('idle');
      } else {
        setStatus('idle');
      }

    } catch (err) {
      console.error('Voice turn processing error:', err);
      setStatus('idle');
    }
  };

  // Tap to Interrupt endpoint call
  const handleInterrupt = async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/voice/interrupt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setStatus('idle');
      setTurns((prev) => [
        ...prev,
        { id: Date.now(), userText: '[Interrupted]', agentText: 'Process interrupted. What would you like to do next?', action: 'INTERRUPT' }
      ]);
    } catch (err) {
      console.error('Interrupt failed:', err);
    }
  };

  // Fetch Handoff detail if triggered
  const fetchHandoff = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/handoff/session/${sid}`);
      const list = await res.json();
      if (list && list.length > 0) {
        setHandoffData(list[list.length - 1]);
      }
    } catch (err) {
      console.error('Fetch handoff failed:', err);
    }
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div className="brand-title">
            <h1>Jan Vaani</h1>
            <p>janvaani.ai • StarForge Hackathon 2026</p>
          </div>
        </div>

        <div className="lang-selector">
          <button 
            className={`lang-btn ${language === 'hi' ? 'active' : ''}`}
            onClick={() => setLanguage('hi')}
          >
            हिंदी (Hindi)
          </button>
          <button 
            className={`lang-btn ${language === 'en' ? 'active' : ''}`}
            onClick={() => setLanguage('en')}
          >
            English
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <div className="main-grid">
        {/* Left Voice Interface & Transcript */}
        <div className="workspace">
          <div className="glass-panel voice-hero">
            {/* Status Chip */}
            <div className={`status-chip ${status}`}>
              <div className="status-dot"></div>
              <span>
                {status === 'idle' && (language === 'hi' ? 'बोलने के लिए माइक दबाएं' : 'Push Mic to Speak')}
                {status === 'listening' && (language === 'hi' ? 'सुन रहे हैं...' : 'Listening...')}
                {status === 'processing' && (language === 'hi' ? 'सोच रहे हैं (Gemini & Engine)...' : 'Thinking (Gemini & Rules)...')}
                {status === 'speaking' && (language === 'hi' ? 'बोल रहे हैं (Rime Coda)...' : 'Speaking (Rime Coda)...')}
              </span>
            </div>

            {/* Mic Push-to-Talk Button */}
            <div className="mic-button-wrapper">
              <button 
                className={`mic-btn ${recording ? 'active' : ''}`}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onTouchStart={startRecording}
                onTouchEnd={stopRecording}
              >
                {recording ? <Square size={36} /> : <Mic size={42} />}
              </button>
            </div>

            {/* Tap to Interrupt Button */}
            <button className="interrupt-btn" onClick={handleInterrupt}>
              <PhoneOff size={16} />
              <span>Tap to Interrupt</span>
            </button>
          </div>

          {/* Transcript Panel */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '16px', fontSize: '1.05rem', color: '#ffb74d' }}>
              Conversation History / लाइव बातचीत
            </h3>
            <div className="transcript-box">
              {turns.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', margin: '20px 0' }}>
                  No messages yet. Press and hold the mic to ask about schemes or check eligibility!
                </p>
              ) : (
                turns.map((t) => (
                  <div key={t.id} className="turn-card">
                    {t.userText && (
                      <div className="chat-bubble user">
                        {t.userText}
                      </div>
                    )}
                    {t.agentText && (
                      <div className="chat-bubble agent hindi-text">
                        {t.agentText}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Side Debug & Status Panel */}
        <div className="side-panel">
          {/* User Profile Slots Captured */}
          <div className="glass-panel">
            <h3 style={{ marginBottom: '14px', fontSize: '1rem', color: '#ff8c38' }}>
              Extracted Profile Slots (Ground Truth)
            </h3>
            <div className="slot-list">
              {Object.keys(profile).length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  No profile facts collected yet.
                </p>
              ) : (
                Object.entries(profile).map(([k, v]) => (
                  <div key={k} className="slot-item">
                    <span className="slot-name">{k.replace('_', ' ')}</span>
                    <span className="slot-val">{String(v)}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Latest Eligibility Result Card */}
          {latestEligibility && (
            <div className={`glass-panel result-banner ${latestEligibility.eligible ? '' : 'ineligible'}`}>
              <div className="result-header">
                {latestEligibility.eligible ? (
                  <CheckCircle2 className="text-emerald-400" size={24} />
                ) : (
                  <AlertTriangle className="text-red-400" size={24} />
                )}
                <div>
                  <div className="result-title">{latestEligibility.scheme_name}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Rules passed: {latestEligibility.matched_rules} / {latestEligibility.total_rules}
                  </div>
                </div>
              </div>
              <p style={{ fontSize: '0.85rem', marginTop: '8px' }}>
                {latestEligibility.explanation}
              </p>
            </div>
          )}

          {/* Cross-scheme matches */}
          {crossMatches.length > 0 && (
            <div className="glass-panel">
              <h4 style={{ fontSize: '0.9rem', color: '#10b981', marginBottom: '10px' }}>
                Cross-Scheme Matches
              </h4>
              {crossMatches.map((m) => (
                <div key={m.scheme_id} style={{ fontSize: '0.85rem', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <strong>{m.scheme_name}</strong>: {m.eligible ? 'Qualifies ✅' : `Ineligible (${m.matched_rules}/${m.total_rules})`}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Simulated Human Handoff Modal Overlay */}
      {handoffData && (
        <div className="handoff-overlay">
          <div className="handoff-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <Headphones size={32} color="#ff8c38" />
              <div>
                <h2 style={{ fontSize: '1.2rem', color: '#fff' }}>Safe Human Handoff Triggered</h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Reason: {handoffData.reason}
                </p>
              </div>
            </div>
            <pre style={{ background: '#000', padding: '16px', borderRadius: '12px', overflowX: 'auto', fontSize: '0.8rem', color: '#10b981' }}>
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
