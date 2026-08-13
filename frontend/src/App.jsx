import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic, Square, PhoneOff, Sparkles,
  CheckCircle2, AlertTriangle, Headphones, LogOut, User,
  Zap, Activity, Radio, ChevronRight, StopCircle, History, X,
  MessageSquare, Clock, Menu, Calendar, Send, MessageCircle
} from 'lucide-react';
import Login from './pages/Login';
import Register from './pages/Register';
import './index.css';
import './schemes-modal.css';
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

// ── Rural Character SVGs ──────────────────────────────────────
function RuralFarmer({ className }) {
  return (
    <svg viewBox="0 0 120 130" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <circle cx="90" cy="20" r="12" fill="#F5A623" opacity="0.85" />
      <g stroke="#F5A623" strokeWidth="2" opacity="0.6">
        <line x1="90" y1="2" x2="90" y2="6" />
        <line x1="90" y1="34" x2="90" y2="38" />
        <line x1="72" y1="20" x2="68" y2="20" />
        <line x1="108" y1="20" x2="112" y2="20" />
      </g>
      <ellipse cx="30" cy="88" rx="22" ry="13" fill="#E8D5B7" />
      <ellipse cx="30" cy="88" rx="22" ry="13" fill="none" stroke="#C4A882" strokeWidth="1.5" />
      <ellipse cx="24" cy="84" rx="5" ry="4" fill="#C4A882" opacity="0.5" />
      <ellipse cx="36" cy="92" rx="4" ry="3" fill="#C4A882" opacity="0.5" />
      <ellipse cx="52" cy="82" rx="10" ry="9" fill="#E8D5B7" stroke="#C4A882" strokeWidth="1.5" />
      <ellipse cx="47" cy="74" rx="4" ry="3" fill="#E8D5B7" stroke="#C4A882" strokeWidth="1" />
      <ellipse cx="57" cy="74" rx="4" ry="3" fill="#E8D5B7" stroke="#C4A882" strokeWidth="1" />
      <path d="M44 74 Q40 65 43 62" stroke="#A0663A" strokeWidth="2" fill="none" />
      <path d="M55 74 Q59 65 57 62" stroke="#A0663A" strokeWidth="2" fill="none" />
      <rect x="14" y="98" width="5" height="16" rx="2" fill="#C4A882" />
      <rect x="23" y="98" width="5" height="16" rx="2" fill="#C4A882" />
      <rect x="34" y="98" width="5" height="16" rx="2" fill="#C4A882" />
      <rect x="43" y="98" width="5" height="16" rx="2" fill="#C4A882" />
      <path d="M8 86 Q2 80 6 74 Q8 72 10 76" stroke="#C4A882" strokeWidth="2" fill="none" />
      <circle cx="72" cy="62" r="10" fill="#FDBF6F" />
      <path d="M62 58 Q72 48 82 58" fill="#D4720C" />
      <circle cx="72" cy="50" r="4" fill="#D4720C" />
      <circle cx="69" cy="62" r="1.5" fill="#3D2B1F" />
      <circle cx="75" cy="62" r="1.5" fill="#3D2B1F" />
      <path d="M68 66 Q72 70 76 66" stroke="#3D2B1F" strokeWidth="1.5" fill="none" />
      <path d="M65 72 Q72 68 79 72 L82 95 L62 95 Z" fill="#F5F0E8" />
      <path d="M64 72 Q72 68 80 72 L79 82 L65 82 Z" fill="#E8803A" />
      <path d="M65 74 Q54 78 52 82" stroke="#FDBF6F" strokeWidth="5" strokeLinecap="round" fill="none" />
      <path d="M79 74 Q85 80 82 86" stroke="#FDBF6F" strokeWidth="5" strokeLinecap="round" fill="none" />
      <path d="M65 95 L60 115" stroke="#F5F0E8" strokeWidth="7" strokeLinecap="round" />
      <path d="M79 95 L84 115" stroke="#F5F0E8" strokeWidth="7" strokeLinecap="round" />
      <ellipse cx="60" cy="118" rx="55" ry="5" fill="#2D6A4F" opacity="0.15" />
    </svg>
  );
}

function RuralWomanWater({ className }) {
  return (
    <svg viewBox="0 0 80 150" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <ellipse cx="40" cy="16" rx="18" ry="10" fill="#C1440E" opacity="0.9" />
      <rect x="22" y="12" width="36" height="20" rx="2" fill="#C1440E" />
      <ellipse cx="40" cy="32" rx="18" ry="8" fill="#A03008" />
      <ellipse cx="40" cy="14" rx="12" ry="5" fill="#87CEEB" opacity="0.6" />
      <ellipse cx="40" cy="42" rx="12" ry="6" fill="#D4720C" opacity="0.8" />
      <circle cx="40" cy="52" r="13" fill="#FDBF6F" />
      <circle cx="40" cy="42" r="7" fill="#3D2B1F" />
      <circle cx="36" cy="52" r="1.8" fill="#3D2B1F" />
      <circle cx="44" cy="52" r="1.8" fill="#3D2B1F" />
      <circle cx="36.5" cy="51.5" r="0.5" fill="white" />
      <circle cx="44.5" cy="51.5" r="0.5" fill="white" />
      <circle cx="40" cy="56" r="0.8" fill="#A0663A" />
      <path d="M36 59 Q40 63 44 59" stroke="#A0663A" strokeWidth="1.5" fill="none" />
      <path d="M28 65 Q40 60 52 65 L55 105 L25 105 Z" fill="#E8803A" />
      <path d="M52 65 Q58 70 55 80 L52 75 Z" fill="#D4720C" />
      <rect x="25" y="100" width="30" height="5" fill="#D4720C" />
      <path d="M28 68 L22 45 L26 43" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d="M52 68 L58 45 L54 43" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d="M25 105 Q30 130 35 135 L45 135 Q50 130 55 105 Z" fill="#E8803A" />
      <ellipse cx="35" cy="136" rx="7" ry="4" fill="#FDBF6F" />
      <ellipse cx="45" cy="136" rx="7" ry="4" fill="#FDBF6F" />
      <rect x="28" y="132" width="14" height="2" rx="1" fill="#E8C547" />
      <rect x="38" y="132" width="14" height="2" rx="1" fill="#E8C547" />
    </svg>
  );
}

function RuralPlanter({ className }) {
  return (
    <svg viewBox="0 0 110 130" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M72 110 L80 90 L100 90 L108 110 Z" fill="#C1440E" opacity="0.85" />
      <ellipse cx="90" cy="90" rx="14" ry="6" fill="#A03008" />
      <path d="M90 90 Q75 70 70 55 Q85 65 90 90" fill="#2D6A4F" />
      <path d="M90 90 Q105 70 110 55 Q95 65 90 90" fill="#52B788" />
      <path d="M90 90 Q80 75 75 65 Q88 72 90 90" fill="#1A4A2E" />
      <rect x="10" y="68" width="22" height="16" rx="4" fill="#6B4226" />
      <path d="M32 74 Q45 72 48 78 Q45 84 32 80 Z" fill="#6B4226" />
      <circle cx="50" cy="82" r="2" fill="#87CEEB" opacity="0.8" />
      <circle cx="54" cy="86" r="1.5" fill="#87CEEB" opacity="0.7" />
      <circle cx="52" cy="91" r="1" fill="#87CEEB" opacity="0.6" />
      <path d="M10 68 Q5 62 10 56 L18 56 Q14 62 18 68" fill="#6B4226" />
      <circle cx="35" cy="35" r="12" fill="#FDBF6F" />
      <path d="M24 32 Q35 22 46 32" fill="#3D2B1F" />
      <circle cx="31" cy="36" r="1.5" fill="#3D2B1F" />
      <circle cx="39" cy="36" r="1.5" fill="#3D2B1F" />
      <path d="M30 41 Q35 45 40 41" stroke="#A0663A" strokeWidth="1.5" fill="none" />
      <path d="M28 47 Q35 44 42 47 L50 75 L20 75 Z" fill="#2D6A4F" />
      <rect x="20" y="70" width="30" height="4" rx="2" fill="#1A4A2E" />
      <path d="M20 75 L18 110 Q35 115 52 110 L50 75 Z" fill="#F5F0E8" />
      <path d="M28 50 Q18 60 12 72" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d="M42 50 Q48 58 46 65" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none" />
      <ellipse cx="24" cy="112" rx="8" ry="4" fill="#FDBF6F" />
      <ellipse cx="46" cy="112" rx="8" ry="4" fill="#FDBF6F" />
    </svg>
  );
}

function RuralHarvestWoman({ className }) {
  return (
    <svg viewBox="0 0 80 150" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <ellipse cx="40" cy="18" rx="24" ry="10" fill="#E8C547" opacity="0.9" />
      <g stroke="#A0663A" strokeWidth="2">
        <line x1="30" y1="8" x2="24" y2="-2" />
        <line x1="35" y1="6" x2="32" y2="-4" />
        <line x1="40" y1="5" x2="40" y2="-5" />
        <line x1="45" y1="6" x2="48" y2="-4" />
        <line x1="50" y1="8" x2="56" y2="-2" />
      </g>
      <ellipse cx="24" cy="-3" rx="4" ry="7" fill="#E8C547" />
      <ellipse cx="32" cy="-5" rx="3" ry="6" fill="#D4A020" />
      <ellipse cx="40" cy="-6" rx="4" ry="7" fill="#E8C547" />
      <ellipse cx="48" cy="-5" rx="3" ry="6" fill="#D4A020" />
      <ellipse cx="56" cy="-3" rx="4" ry="7" fill="#E8C547" />
      <path d="M16 14 L20 36 L60 36 L64 14 Z" fill="#C1440E" opacity="0.8" />
      <ellipse cx="40" cy="36" rx="20" ry="7" fill="#A03008" />
      <path d="M20 20 L60 20" stroke="#A03008" strokeWidth="1" opacity="0.5" />
      <path d="M19 26 L61 26" stroke="#A03008" strokeWidth="1" opacity="0.5" />
      <ellipse cx="40" cy="46" rx="13" ry="7" fill="#E8803A" opacity="0.8" />
      <circle cx="40" cy="56" r="13" fill="#FDBF6F" />
      <circle cx="40" cy="46" r="8" fill="#3D2B1F" />
      <circle cx="28" cy="56" r="2.5" fill="#E8C547" />
      <circle cx="52" cy="56" r="2.5" fill="#E8C547" />
      <circle cx="36" cy="55" r="1.8" fill="#3D2B1F" />
      <circle cx="44" cy="55" r="1.8" fill="#3D2B1F" />
      <circle cx="36.5" cy="54.5" r="0.5" fill="white" />
      <circle cx="40" cy="51" r="1.2" fill="#C1440E" />
      <path d="M35 60 Q40 64 45 60" stroke="#A0663A" strokeWidth="1.5" fill="none" />
      <path d="M28 69 Q40 63 52 69 L54 88 L26 88 Z" fill="#C1440E" />
      <path d="M52 69 Q58 72 56 82 L52 78 Z" fill="#A03008" />
      <path d="M28 70 L24 47 L28 45" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d="M52 70 L56 47 L52 45" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none" />
      <path d="M26 88 Q28 118 32 128 L48 128 Q52 118 54 88 Z" fill="#E8803A" />
      <rect x="26" y="120" width="28" height="5" fill="#C1440E" />
      <ellipse cx="33" cy="130" rx="7" ry="4" fill="#FDBF6F" />
      <ellipse cx="47" cy="130" rx="7" ry="4" fill="#FDBF6F" />
      <rect x="29" y="128" width="8" height="1.5" rx="1" fill="#E8C547" />
      <rect x="43" y="128" width="8" height="1.5" rx="1" fill="#E8C547" />
    </svg>
  );
}

// ── Premium Abstract Elements ───────────────────────────────────
function FloatingElements() {
  return (
    <>
      {/* Aesthetic glowing background orbs */}
      <div className="glass-blob blob-1" />
      <div className="glass-blob blob-2" />
      <div className="glass-blob blob-3" />
      <div className="glass-blob blob-4" />

      {/* SVG Characters with modern layout */}
      <RuralFarmer className="floating-svg img-1" />
      <RuralWomanWater className="floating-svg img-2" />
      <RuralPlanter className="floating-svg img-3" />
      <RuralHarvestWoman className="floating-svg img-4" />
    </>
  );
}


// ── Typewriter component ────────────────────────────────────────
function TypewriterText({ texts, speed = 50, pause = 2000 }) {
  const [textIndex, setTextIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let timer;
    const currentText = texts[textIndex];

    if (isDeleting) {
      if (displayedText === '') {
        setIsDeleting(false);
        setTextIndex((prev) => (prev + 1) % texts.length);
        timer = setTimeout(() => { }, 500);
      } else {
        timer = setTimeout(() => {
          setDisplayedText(currentText.substring(0, displayedText.length - 1));
        }, speed / 2);
      }
    } else {
      if (displayedText === currentText) {
        timer = setTimeout(() => {
          setIsDeleting(true);
        }, pause);
      } else {
        timer = setTimeout(() => {
          setDisplayedText(currentText.substring(0, displayedText.length + 1));
        }, speed);
      }
    }
    return () => clearTimeout(timer);
  }, [displayedText, isDeleting, textIndex, texts, speed, pause]);

  return <span className="typewriter-text">{displayedText}<span className="cursor">|</span></span>;
}

export default function App() {
  // Auth state
  const [authUser, setAuthUser] = useState(getStoredUser);
  const [authView, setAuthView] = useState('login');
  const [showUserMenu, setShowUserMenu] = useState(false);

  // App state
  const [language, setLanguage] = useState('hi');
  const [sessionId, setSessionId] = useState(null);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | listening | processing | speaking
  const [turns, setTurns] = useState([]);
  const [profile, setProfile] = useState({});
  const [userInfo, setUserInfo] = useState(null);
  const [latestEligibility, setLatestEligibility] = useState(null);
  const [crossMatches, setCrossMatches] = useState([]);
  const [handoffData, setHandoffData] = useState(null);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [endingChat, setEndingChat] = useState(false);
  const [schemeRecommendations, setSchemeRecommendations] = useState([]);
  const [profileComplete, setProfileComplete] = useState(false);
  const [showAllSchemes, setShowAllSchemes] = useState(false);
  const [howToApplyState, setHowToApplyState] = useState({ loading: false, data: null, error: null, audio: null });

  // History panel state
  const [showHistory, setShowHistory] = useState(false);
  const [pastSessions, setPastSessions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Transcript viewer state
  const [viewingSession, setViewingSession] = useState(null); // {session, profile, turns}
  const [viewLoading, setViewLoading] = useState(false);
  const [sessionActionLoading, setSessionActionLoading] = useState(false);
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  // ── Text chat / questionnaire state ──────────────────────────
  const [chatModeActive, setChatModeActive] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatSending, setChatSending] = useState(false);
  const [chatTyping, setChatTyping] = useState(false);
  // { state: 'GREETING'|'COLLECTING'|'COMPLETE', currentQuestion: number|null }
  const [chatQState, setChatQState] = useState({ state: 'GREETING', currentQuestion: null });
  const chatInputRef = useRef(null);
  // Ref that mirrors chatModeActive for use inside closures (e.g. MediaRecorder.onstop)
  const chatModeActiveRef = useRef(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const transcriptEndRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const audioContextRef = useRef(null);


  useEffect(() => {
    if (authUser) {
      initSession(language);
      fetchUserProfile();
    }
  }, [language, authUser?.user_id]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  // ── Fetch user profile from /auth/me ─────────────────────
  const fetchUserProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        setUserInfo(data);
      }
    } catch (err) {
      console.error('Failed to fetch user profile:', err);
    }
  };

  const handleAuthSuccess = (data) => {
    setAuthUser({ user_id: data.user_id, email: data.email, full_name: data.full_name });
    // Fetch full user profile after login/register
    setTimeout(fetchUserProfile, 100);
  };

  const handleLogout = () => {
    localStorage.removeItem('jv_token');
    localStorage.removeItem('jv_user');
    setAuthUser(null);
    setUserInfo(null);
    setSessionId(null);
    setTurns([]);
    setProfile({});
    setLatestEligibility(null);
    setCrossMatches([]);
    setHandoffData(null);
    setShowHistory(false);
    setPastSessions([]);
    setSchemeRecommendations([]);
    setProfileComplete(false);
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
      setSchemeRecommendations([]);
      setProfileComplete(false);
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

  // ── End a viewed session (mark completed) ───────────────────
  const handleEndViewingSession = async () => {
    if (!viewingSession?.session?.session_id || sessionActionLoading) return;
    const sid = viewingSession.session.session_id;
    setSessionActionLoading(true);
    try {
      await fetch(`${API_BASE}/sessions/${sid}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setViewingSession(prev => ({
        ...prev,
        session: { ...prev.session, status: 'completed' },
      }));
      const res = await fetch(`${API_BASE}/sessions`, { headers: authHeaders() });
      if (res.ok) setPastSessions(await res.json());
    } catch (err) {
      console.error('End session failed:', err);
    } finally {
      setSessionActionLoading(false);
      setShowEndConfirm(false);
    }
  };

  // ── Continue a viewed session ────────────────────────────────
  const handleContinueSession = async () => {
    if (!viewingSession?.session?.session_id || sessionActionLoading) return;
    const sid = viewingSession.session.session_id;
    setSessionActionLoading(true);
    try {
      const patchRes = await fetch(`${API_BASE}/sessions/${sid}/reactivate`, {
        method: 'PATCH',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
      });
      if (!patchRes.ok) {
        console.error('Reactivate failed:', await patchRes.text());
        setSessionActionLoading(false);
        return;
      }
      const turns = (viewingSession.turns || []).map((t, i) => ({
        id: t.turn_id || i,
        userText: t.user_text,
        agentText: t.agent_text,
        action: t.action_taken,
      }));
      const profileMap = {};
      (viewingSession.profile || []).forEach(slot => {
        profileMap[slot.slot_name] = slot.value;
      });
      setSessionId(sid);
      setTurns(turns);
      setProfile(profileMap);
      setLatestEligibility(null);
      setCrossMatches([]);
      setHandoffData(null);
      const res = await fetch(`${API_BASE}/sessions`, { headers: authHeaders() });
      if (res.ok) setPastSessions(await res.json());
      setViewingSession(null);
      setShowHistory(false);
    } catch (err) {
      console.error('Continue session failed:', err);
    } finally {
      setSessionActionLoading(false);
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
        // If the questionnaire chat mode is active, route through STT-only → chat turn
        if (chatModeActiveRef.current) {
          await sendVoiceForChat(audioBlob);
        } else {
          await sendAudioTurn(audioBlob);
        }
      };
      mediaRecorderRef.current.start();
      setRecording(true);
      setStatus('listening');

      // ── Silence Detection (Auto-stop) ──
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      const microphone = audioCtx.createMediaStreamSource(stream);
      microphone.connect(analyser);
      analyser.fftSize = 512;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      let hasSpoken = false;
      let lastSpokenTime = Date.now();

      const checkSilence = () => {
        if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') return;
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const average = sum / bufferLength;

        if (average > 15) { // volume threshold
          hasSpoken = true;
          lastSpokenTime = Date.now();
        } else {
          const now = Date.now();
          // If spoken, wait 3s of silence to auto-stop
          if (hasSpoken && (now - lastSpokenTime > 3000)) {
            stopRecording();
            return;
          }
          // If nothing spoken at all for 4 seconds, auto-stop
          else if (!hasSpoken && (now - lastSpokenTime > 4000)) {
            stopRecording();
            return;
          }
        }
        silenceTimerRef.current = requestAnimationFrame(checkSilence);
      };
      checkSilence();

    } catch (err) {
      console.error('Mic error:', err);
      alert('Microphone access is required. Please allow mic access in your browser.');
    }
  };

  const stopRecording = () => {
    if (silenceTimerRef.current) cancelAnimationFrame(silenceTimerRef.current);
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => { });
    }
    audioContextRef.current = null;

    // Use mediaRecorderRef.current.state directly — avoids stale React state in closures
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
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
      if (data.scheme_recommendations) setSchemeRecommendations(data.scheme_recommendations);
      if (data.profile_complete !== undefined) setProfileComplete(data.profile_complete);

      // Always re-fetch profile from DB after each turn to catch any DB-persisted slots
      await loadProfileFromDB(sessionId);

      if (data.audio_b64) {
        setStatus('speaking');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
        audio.play().catch(() => { });
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

  // ── Voice-for-chat: STT only → questionnaire pipeline ────────
  // Called when chatModeActive=true and user uses the mic.
  // Sends audio to /voice/transcribe for STT, then feeds text to sendChatMessage.
  const sendVoiceForChat = async (audioBlob) => {
    if (!sessionId) return;
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('language', language);
    formData.append('audio', audioBlob, 'turn.webm');
    try {
      // Step 1: STT only — get transcript without running the full voice pipeline
      const sttRes = await fetch(`${API_BASE}/voice/transcribe`, {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      });
      if (sttRes.status === 401) { handleLogout(); return; }
      if (!sttRes.ok) { setStatus('idle'); return; }
      const sttData = await sttRes.json();
      const transcript = sttData.transcript?.trim();
      if (!transcript) { setStatus('idle'); return; }

      // Step 2: Feed transcript into questionnaire with audio reply + auto-record next
      setStatus('idle');
      await sendChatMessage(transcript, true, true);   // with_audio=true, autoRecord=true
    } catch (err) {
      console.error('Voice-for-chat error:', err);
      setStatus('idle');
    }
  };

  // ── Text chat: parse markdown table → <table> ────────────────
  const renderMarkdownTable = (markdown) => {
    if (!markdown) return null;
    // Split into lines, find table block(s)
    const lines = markdown.split('\n');
    // Identify text lines vs table lines
    const textLines = [];
    const tableLines = [];
    let inTable = false;
    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith('|')) {
        inTable = true;
        tableLines.push(trimmed);
      } else {
        if (inTable) inTable = false;
        textLines.push(line);
      }
    });

    // Build <table> from tableLines
    let tableEl = null;
    if (tableLines.length >= 2) {
      const parseRow = (row) =>
        row.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());

      const headerCells = parseRow(tableLines[0]);
      // tableLines[1] is the separator (--- row), skip it
      const bodyRows = tableLines.slice(2).map(parseRow);

      tableEl = (
        <div className="markdown-table-wrapper">
          <table className="markdown-table">
            <thead>
              <tr>{headerCells.map((h, i) => <th key={i}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {bodyRows.map((cells, ri) => (
                <tr key={ri}>
                  {cells.map((cell, ci) => <td key={ci}>{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Render non-table text
    const textContent = textLines.join('\n').trim();
    return { textContent, tableEl };
  };

  // ── Text chat: send a message to /chat/turn ──────────────────
  // withAudio=true → backend synthesizes TTS and returns audio_b64
  // autoRecord=true → after TTS finishes, auto-start mic (voice-in-chat mode)
  const sendChatMessage = async (msg, withAudio = false, autoRecord = false) => {
    if (!sessionId || !msg.trim()) return;
    const userMsg = msg.trim();
    setChatInput('');
    setChatSending(true);
    setChatTyping(true);

    // Optimistically add user bubble (hide [Greeting] from chat history)
    const tempId = `chat-${Date.now()}`;
    if (userMsg !== 'Hello' && userMsg !== 'नमस्ते') {
      setTurns(prev => [...prev, { id: tempId, userText: userMsg, agentText: null, action: 'CHAT' }]);
    } else {
      setTurns(prev => [...prev, { id: tempId, userText: null, agentText: null, action: 'CHAT' }]);
    }

    try {
      const res = await fetch(`${API_BASE}/chat/turn`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          session_id: sessionId,
          message: userMsg,
          language,
          with_audio: withAudio,
        }),
      });
      if (res.status === 401) { handleLogout(); return; }
      if (!res.ok) {
        setChatTyping(false);
        setChatSending(false);
        return;
      }
      const data = await res.json();

      setChatQState({ state: data.next_state, currentQuestion: data.current_question });

      // Turn off text mode automatically when questionnaire is complete
      if (data.next_state === 'COMPLETE') {
        setTimeout(() => {
          setChatModeActive(false);
          chatModeActiveRef.current = false;
        }, 1500); // 1.5s delay so user sees the transition
      }

      // Update the optimistic turn with agent reply + optional table
      setTurns(prev => prev.map(t =>
        t.id === tempId
          ? { ...t, agentText: data.agent_text, tableMarkdown: data.table_markdown || null, action: 'CHAT' }
          : t
      ));

      // Merge extracted slots into profile panel
      if (data.slots_extracted) setProfile(prev => ({ ...prev, ...data.slots_extracted }));
      await loadProfileFromDB(sessionId);

      // Play TTS audio if provided
      if (data.audio_b64) {
        setStatus('speaking');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
        audio.play().catch(() => { });
        audio.onended = () => {
          setStatus('idle');
          // Only auto-start mic in voice-driven chat mode (autoRecord flag)
          if (chatModeActiveRef.current && autoRecord) {
            startRecording();
          }
        };
      }

    } catch (err) {
      console.error('Chat turn error:', err);
    } finally {
      setChatTyping(false);
      setChatSending(false);
      // Refocus text input (only if in pure text mode, not voice mode)
      if (!withAudio) setTimeout(() => chatInputRef.current?.focus(), 80);
    }
  };

  const toggleChatMode = () => {
    const next = !chatModeActive;
    setChatModeActive(next);
    chatModeActiveRef.current = next;   // keep ref in sync for closure use in onstop
    if (next && sessionId && chatQState.state === 'GREETING') {
      // Kick off the questionnaire with TTS greeting; do NOT auto-start mic (text mode)
      sendChatMessage(language === 'hi' ? 'नमस्ते' : 'Hello', true, false);
    }
    if (next) setTimeout(() => chatInputRef.current?.focus(), 150);
  };

  const handleHowToApply = async (rec) => {
    // If opening from the modal, we might want to close the All Schemes modal, or just layer over it.
    // Let's close All Schemes to keep UI clean.
    setShowAllSchemes(false);
    setHowToApplyState({ loading: true, data: null, error: null, audio: null });

    try {
      const res = await fetch(`${API_BASE}/schemes/how-to-apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scheme_name_en: rec.scheme_name_en || rec.scheme_name,
          scheme_name_hi: rec.scheme_name_hi,
          language: language
        })
      });
      if (!res.ok) throw new Error('Network error');
      const data = await res.json();
      setHowToApplyState({ loading: false, data, error: null, audio: null });

      if (data.audio_b64) {
        setStatus('speaking');
        const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
        audio.play().catch(() => { });
        audio.onended = () => setStatus('idle');
        setHowToApplyState(prev => ({ ...prev, audio }));
      }
    } catch (err) {
      setHowToApplyState({ loading: false, data: null, error: 'Failed to load guide. Please try again.', audio: null });
    }
  };

  // ── Status label helper ──────────────────────────────────────
  const statusLabel = {
    idle: language === 'hi' ? 'बोलने के लिए माइक दबाएं' : 'Hold Mic to Speak',
    listening: language === 'hi' ? 'सुन रहे हैं…' : 'Listening…',
    processing: language === 'hi' ? 'सोच रहे हैं (Gemini & Engine)…' : 'Thinking (Gemini & Rules)…',
    speaking: language === 'hi' ? 'बोल रहे हैं (Rime Coda)…' : 'Speaking (Rime Coda)…',
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
            <Sparkles size={18} color="white" strokeWidth={2.5} />
          </div>
          <div className="brand-title">
            <h1>Jan Vaani</h1>
            <p>JAN VAANI · AI SCHEME FINDER</p>
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

          <div className="user-menu-wrapper">
            <button
              className={`hamburger-btn ${showUserMenu ? 'active' : ''}`}
              onClick={() => setShowUserMenu(!showUserMenu)}
              title="User menu"
            >
              <Menu size={20} />
            </button>

            {showUserMenu && authUser && (
              <div className="user-dropdown">
                <div className="user-dropdown-header">
                  <div className="user-dropdown-avatar">
                    {(userInfo?.full_name || authUser.email).charAt(0).toUpperCase()}
                  </div>
                  <div className="user-dropdown-info">
                    {userInfo?.full_name && <div className="user-dropdown-name">{userInfo.full_name}</div>}
                    <div className="user-dropdown-email">{authUser.email}</div>
                  </div>
                </div>
                {userInfo?.created_at && (
                  <div className="user-dropdown-meta">
                    <Calendar size={13} className="user-dropdown-meta-icon" />
                    Member since {new Date(userInfo.created_at.endsWith('Z') ? userInfo.created_at : userInfo.created_at + 'Z').toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </div>
                )}
                <button className="logout-btn" onClick={() => {
                  setShowUserMenu(false);
                  setShowLogoutConfirm(true);
                }}>
                  <LogOut size={14} />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Main Grid ── */}
      <div className="main-grid">

        {/* ── Left: Voice + Transcript ── */}
        <div className="workspace glass-panel unified-workspace">

          {/* Header */}
          <div className="unified-header">
            <h2>{language === 'hi' ? 'वॉयस असिस्टेंट' : 'Voice Assistant'}</h2>
            <p style={{ minHeight: '42px' }}>
              <TypewriterText
                texts={
                  language === 'hi'
                    ? [
                      'माइक पर टैप करें और उन योजनाओं को खोजने के लिए बोलना शुरू करें जिनके आप पात्र हैं।',
                      'माइक बटन को दबाए रखें, अपना प्रश्न बोलें, और छोड़ दें।',
                      'हिंदी या अंग्रेजी में सरकारी योजनाओं के बारे में पूछें।',
                      'पता करें कि कौन से कल्याणकारी कार्यक्रम आपकी प्रोफ़ाइल से मेल खाते हैं।'
                    ]
                    : [
                      'Tap the microphone and start speaking to find schemes you qualify for.',
                      'Hold the microphone button, speak your query, and release.',
                      'Ask about government schemes in Hindi or English.',
                      'Find out which welfare programs match your profile.'
                    ]
                }
                speed={40}
                pause={3000}
              />
            </p>
          </div>

          {/* Voice Hero — Rural Scene with animated characters + Mic */}
          <div className="voice-hero unified-mic-section">
            <div className="rural-scene">

              {/* Premium Floating Orbs & Icons arranged around mic */}
              <FloatingElements />

              {/* Mic in the center */}
              <div className="mic-center-area">
                <div className="mic-button-wrapper">
                  {status === 'idle' && (
                    <>
                      <div className="mic-ring-idle" />
                      <div className="mic-ring-idle" />
                      <div className="mic-ring-idle" />
                    </>
                  )}
                  {status === 'listening' && (
                    <>
                      <div className="mic-ripple" />
                      <div className="mic-ripple" />
                      <div className="mic-ripple" />
                    </>
                  )}
                  {status === 'processing' && <div className="mic-spinner-ring" />}
                  {status === 'speaking' && <Waveform />}
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
                      {recording ? <Square size={28} /> : <Mic size={36} />}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Mic label row */}
            <div style={{ textAlign: 'center', marginTop: '8px' }}>
              {status === 'idle' ? (
                <>
                  <p className="mic-hint">
                    {language === 'hi' ? 'बोलने के लिए लाल बटन को छुएं' : 'Hold the red button to speak'}
                  </p>
                  <p className="mic-sub-hint">
                    <TypewriterText
                      texts={
                        language === 'hi'
                          ? [
                            '"मुझे खेती-बाड़ी और किसान सम्मान निधि योजना के बारे में बताएं"',
                            '"मेरी उम्र 45 साल है और मैं हरियाणा में रहता हूं"',
                            '"मुझे वृद्धा पेंशन योजना के बारे में जानना है"'
                          ]
                          : [
                            '"Tell me about Kisan Samman Nidhi scheme"',
                            '"I am 45 years old and live in Haryana"',
                            '"What schemes am I eligible for?"'
                          ]
                      }
                      speed={40}
                      pause={3000}
                    />
                  </p>
                </>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                  {status !== 'idle' && (
                    <button id="interrupt-btn" className="interrupt-btn" onClick={handleInterrupt}>
                      <PhoneOff size={13} />
                      <span>{language === 'hi' ? 'रोकें' : 'Interrupt'}</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Transcript Panel */}
          <div className="transcript-panel unified-transcript-box">
            {/* Header row */}
            <div className="transcript-panel-header">
              <div className="transcript-panel-title">
                <div className="dot" />
                {language === 'hi' ? '\u092c\u093e\u0924\u091a\u0940\u0924' : 'Conversations'}
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  id="chat-mode-toggle-btn"
                  className={`chat-mode-toggle ${chatModeActive ? 'active' : ''}`}
                  onClick={toggleChatMode}
                  title={chatModeActive
                    ? (language === 'hi' ? '\u091f\u0947\u0915\u094d\u0938\u094d\u091f \u091a\u0948\u091f \u092c\u0902\u0926 \u0915\u0930\u0947\u0902' : 'Close text chat')
                    : (language === 'hi' ? '\u091f\u0947\u0915\u094d\u0938\u094d\u091f \u092e\u0947\u0902 \u092a\u0942\u091b\u0947\u0902' : 'Ask via text')}
                >
                  <MessageCircle size={11} />
                  {language === 'hi' ? '\u091f\u0947\u0915\u094d\u0938\u094d\u091f' : 'TEXT'}
                </button>
                <button
                  className="transcript-history-link"
                  onClick={showHistory ? closeHistory : openHistory}
                >
                  HISTORY
                </button>
              </div>
            </div>

            {/* Questionnaire progress bar */}
            {chatModeActive && chatQState.state === 'COLLECTING' && chatQState.currentQuestion != null && (
              <div style={{ padding: '6px 14px 0' }}>
                <div className="chat-progress-badge">
                  <span>📝</span>
                  {language === 'hi'
                    ? `\u092a\u094d\u0930\u0936\u094d\u0928 ${chatQState.currentQuestion} / 7`
                    : `Question ${chatQState.currentQuestion} of 7`}
                </div>
                <div className="chat-progress-bar-track">
                  <div
                    className="chat-progress-bar-fill"
                    style={{ width: `${(chatQState.currentQuestion / 7) * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="transcript-box">
              {turns.length === 0 ? (
                <div className="transcript-empty">
                  <div className="transcript-empty-icon">
                    <MessageSquare size={22} />
                  </div>
                  <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '700', color: 'var(--text-dark)' }}>
                    {language === 'hi' ? '\u0905\u092d\u0940 \u0924\u0915 \u0915\u094b\u0908 \u092c\u093e\u0924\u091a\u0940\u0924 \u0928\u0939\u0940\u0902 \u0939\u0941\u0908' : 'No conversations yet'}
                  </h3>
                  <p style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '0.83rem', lineHeight: 1.6 }}>
                    {language === 'hi'
                      ? '\u092e\u093e\u0907\u0915 \u0926\u092c\u093e\u0915\u0930 \u092a\u0942\u091b\u0947\u0902 \u092f\u093e \u090a\u092a\u0930 "\u091f\u0947\u0915\u094d\u0938\u094d\u091f" \u092c\u091f\u0928 \u0938\u0947 \u0905\u092a\u0928\u0940 \u091c\u093e\u0928\u0915\u093e\u0930\u0940 \u092d\u0930\u0947\u0902\u0964'
                      : 'Hold the mic to ask, or click "TEXT" above to fill your profile.'}
                  </p>
                </div>
              ) : (
                turns.map((t) => {
                  const tableData = t.tableMarkdown ? renderMarkdownTable(t.tableMarkdown) : null;
                  return (
                    <div key={t.id} className="turn-card">
                      {t.userText && t.userText !== '[Greeting]' && (
                        <div className="chat-bubble user">{t.userText}</div>
                      )}
                      {t.agentText && (
                        <div className={`chat-bubble agent ${language === 'hi' ? 'hindi-text' : ''} ${t.tableMarkdown ? 'complete-pulse' : ''
                          }`}>
                          {tableData ? (
                            <>
                              {tableData.textContent && (
                                <span style={{ display: 'block', marginBottom: tableData.tableEl ? '4px' : 0 }}>
                                  {tableData.textContent}
                                </span>
                              )}
                              {tableData.tableEl}
                            </>
                          ) : (
                            t.agentText
                          )}
                        </div>
                      )}
                      {!t.agentText && chatTyping && t.action === 'CHAT' && (
                        <div className="chat-bubble agent">
                          <div className="chat-typing-indicator">
                            <span /><span /><span />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
              <div ref={transcriptEndRef} />
            </div>

            {/* Chat text input bar */}
            {chatModeActive && (
              <div className="chat-input-bar">
                <input
                  ref={chatInputRef}
                  id="chat-text-input"
                  className="chat-input-field"
                  type="text"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !chatSending && chatInput.trim()) {
                      sendChatMessage(chatInput);
                    }
                  }}
                  placeholder={language === 'hi' ? '\u092f\u0939\u093e\u0901 \u091f\u093e\u0907\u092a \u0915\u0930\u0947\u0902\u2026' : 'Type your answer here\u2026'}
                  disabled={chatSending || chatQState.state === 'COMPLETE'}
                  maxLength={500}
                />
                <button
                  id="chat-send-btn"
                  className="chat-send-btn"
                  onClick={() => sendChatMessage(chatInput)}
                  disabled={chatSending || !chatInput.trim() || chatQState.state === 'COMPLETE'}
                  title={language === 'hi' ? '\u092d\u0947\u091c\u0947\u0902' : 'Send'}
                >
                  <Send size={16} />
                </button>
              </div>
            )}

            {status !== 'idle' && (
              <div className={`status-indicator ${status}`}>
                <Activity size={14} className="status-indicator-icon" />
                <span>{statusLabel}</span>
              </div>
            )}
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

            {/* Privacy note */}
            <p className="privacy-note" style={{ marginTop: 0, paddingTop: 0, borderTop: 'none', marginBottom: '12px' }}>
              * {language === 'hi'
                ? 'आपकी जानकारी पूरी तरह से सुरक्षित है और इसका उपयोग केवल कल्याणकारी योजनाओं की खोज के लिए किया जाएगा।'
                : 'Your information is fully secure and will only be used to find welfare schemes.'}
            </p>

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

          {/* ── Eligible Schemes Recommendations Panel ── */}
          {schemeRecommendations && schemeRecommendations.length > 0 ? (
            <div className="glass-panel scheme-rec-panel">
              <h3 className="panel-title">
                <Sparkles size={14} className="text-saffron" />
                <span className="text-saffron">
                  {language === 'hi' ? 'पात्र योजनाएं' : 'Eligible Schemes'}
                </span>
              </h3>
              <p className="scheme-rec-subtitle">
                {language === 'hi'
                  ? 'आपकी प्रोफ़ाइल के आधार पर संभावित योजनाएं'
                  : 'Recommended based on your profile'}
              </p>
              <div className="scheme-rec-list">
                {schemeRecommendations.slice(0, 1).map((rec, i) => (
                  <div key={i} className={`scheme-rec-item ${rec.likely_eligible ? 'eligible' : 'partial'}`}>
                    <div className="scheme-rec-top">
                      <div className="scheme-rec-name">
                        {language === 'hi' ? rec.scheme_name_hi : rec.scheme_name_en}
                      </div>
                      <span className={`scheme-rec-badge ${rec.likely_eligible ? 'eligible' : 'partial'}`}>
                        {rec.likely_eligible
                          ? (language === 'hi' ? '✓ पात्र' : '✓ Eligible')
                          : (language === 'hi' ? '~ आंशिक' : '~ Partial')}
                      </span>
                    </div>
                    <div className="scheme-rec-reason">{rec.reason}</div>
                    <button
                      className="how-to-apply-btn"
                      onClick={() => handleHowToApply(rec)}
                      style={{ marginTop: '8px', padding: '4px 8px', fontSize: '0.75rem', borderRadius: '4px', border: '1px solid var(--saffron)', background: 'var(--saffron-pale)', color: 'var(--saffron-dim)', cursor: 'pointer', fontWeight: 600 }}
                    >
                      {language === 'hi' ? 'आवेदन कैसे करें?' : 'How to Apply?'}
                    </button>
                  </div>
                ))}
              </div>
              {schemeRecommendations.length > 1 && (
                <button
                  className="scheme-rec-toggle-btn"
                  onClick={() => setShowAllSchemes(true)}
                  style={{ width: '100%', marginTop: '10px', padding: '6px', background: 'none', border: '1px dashed var(--border)', borderRadius: 'var(--r-xs)', color: 'var(--saffron-dim)', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}
                >
                  {language === 'hi' ? `सभी ${schemeRecommendations.length} दिखाएं` : `View all ${schemeRecommendations.length}`}
                </button>
              )}
            </div>
          ) : profileComplete ? (
            <div className="glass-panel scheme-rec-panel scheme-rec-loading">
              <h3 className="panel-title">
                <Sparkles size={14} className="text-saffron" />
                <span className="text-saffron">
                  {language === 'hi' ? 'पात्र योजनाएं' : 'Eligible Schemes'}
                </span>
              </h3>
              <div className="scheme-rec-spinner">
                <div className="scheme-rec-dot" />
                <div className="scheme-rec-dot" />
                <div className="scheme-rec-dot" />
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                {language === 'hi' ? 'योजनाएं ढूंढ रहे हैं…' : 'Finding schemes for you…'}
              </p>
            </div>
          ) : (
            <div className="glass-panel scheme-rec-panel scheme-rec-empty">
              <div className="scheme-rec-empty-icon">🏛️</div>
              <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-dark)', margin: '8px 0 4px' }}>
                {language === 'hi' ? 'पात्र योजनाएं' : 'Eligible Schemes'}
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                {language === 'hi'
                  ? 'अपनी जानकारी (उम्र, आय, जाति, राज्य) बोलें — AI आपके लिए सही योजनाएं खोजेगा।'
                  : 'Share your details (age, income, caste, state) — AI will find matching schemes.'}
              </p>
            </div>
          )}

          {/* Session Info + Session Controls */}
          {sessionId && (
            <div className="glass-panel">
              <div className="session-id-box">
                <div className="session-id-label">SESSION ID</div>
                <div className="session-id-value">{sessionId}</div>
              </div>

              <button
                id="new-session-btn"
                className="new-session-btn"
                onClick={() => initSession(language)}
              >
                <ChevronRight size={14} />
                {language === 'hi' ? 'नया सत्र शुरू करें' : 'Start New Session'}
              </button>

              <button
                id="end-chat-btn"
                className="end-session-btn"
                onClick={handleEndChat}
                disabled={endingChat || turns.length === 0}
                title={turns.length === 0 ? 'No conversation to save' : 'End this chat and save it'}
              >
                <StopCircle size={14} />
                {endingChat
                  ? (language === 'hi' ? 'सहेजा जा रहा है…' : 'Saving…')
                  : (language === 'hi' ? 'चैट समाप्त करें' : 'End Chat')
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
                <h2 style={{ fontSize: '1.15rem', color: 'var(--text-dark)', fontWeight: 800 }}>
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
            <h2 style={{ fontSize: '1.2rem', color: 'var(--text-dark)', fontWeight: 800, marginBottom: '8px' }}>
              {language === 'hi' ? 'लॉगआउट करें?' : 'Logout?'}
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '24px' }}>
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
                      <div className="history-session-title">
                        {s.title || (language === 'hi' ? 'नई चैट' : 'New Chat')}
                      </div>
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
                    : (viewingSession.session?.title || (language === 'hi' ? 'नई चैट' : 'New Chat'))
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

              <div className="transcript-modal-footer-actions">
                {/* End / Continue for active non-current sessions */}
                {!viewingSession.loading && viewingSession.session &&
                  viewingSession.session.session_id !== sessionId &&
                  viewingSession.session.status !== 'completed' && (
                    <>
                      <button
                        className="modal-action-btn modal-end-btn"
                        onClick={() => setShowEndConfirm(true)}
                        disabled={sessionActionLoading}
                        title={language === 'hi' ? 'इस सत्र को समाप्त करें' : 'Mark this session as completed'}
                      >
                        <StopCircle size={14} />
                        {sessionActionLoading
                          ? (language === 'hi' ? 'हो रहा है…' : 'Working…')
                          : (language === 'hi' ? 'समाप्त करें' : 'End Session')}
                      </button>
                      <button
                        className="modal-action-btn modal-continue-btn"
                        onClick={handleContinueSession}
                        disabled={sessionActionLoading}
                        title={language === 'hi' ? 'इस सत्र को जारी रखें' : 'Continue this chat session'}
                      >
                        <ChevronRight size={14} />
                        {sessionActionLoading
                          ? (language === 'hi' ? 'हो रहा है…' : 'Working…')
                          : (language === 'hi' ? 'जारी रखें' : 'Continue')}
                      </button>
                    </>
                  )}

                {/* Completed badge (read-only) */}
                {!viewingSession.loading && viewingSession.session &&
                  viewingSession.session.status === 'completed' && (
                    <span className="modal-completed-badge">
                      <CheckCircle2 size={13} />
                      {language === 'hi' ? 'पूर्ण' : 'Completed'}
                    </span>
                  )}
              </div>
            </div>
          </div>
        </div>
      )}
      {/* ── Confirm End Session Modal ── */}
      {showEndConfirm && (
        <div className="handoff-overlay" onClick={() => setShowEndConfirm(false)}>
          <div className="handoff-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '420px', textAlign: 'center' }}>
            <div style={{ marginBottom: 16, fontSize: '2rem' }}>⚠️</div>
            <h2 style={{ fontSize: '1.15rem', color: 'var(--text-dark)', fontWeight: 800, marginBottom: '8px' }}>
              {language === 'hi' ? 'सत्र समाप्त करें?' : 'End Session?'}
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '24px', lineHeight: 1.6 }}>
              {language === 'hi'
                ? 'क्या आप इस चैट सत्र को पूर्ण के रूप में चिह्नित करना चाहते हैं?'
                : 'Are you sure you want to mark this chat session as completed? This will close it permanently.'}
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                className="close-btn"
                style={{ marginTop: 0, flex: 1 }}
                onClick={() => setShowEndConfirm(false)}
                disabled={sessionActionLoading}
              >
                {language === 'hi' ? 'रद्द करें' : 'Cancel'}
              </button>
              <button
                className="close-btn"
                style={{ marginTop: 0, flex: 1, background: 'rgba(255, 90, 90, 0.12)', borderColor: 'rgba(255, 90, 90, 0.3)', color: '#ff9090' }}
                onClick={handleEndViewingSession}
                disabled={sessionActionLoading}
              >
                {sessionActionLoading
                  ? (language === 'hi' ? 'हो रहा है…' : 'Working…')
                  : (language === 'hi' ? 'हाँ, समाप्त करें' : 'Yes, End It')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── All Eligible Schemes Modal ── */}
      {showAllSchemes && (
        <div className="schemes-modal-overlay" onClick={() => setShowAllSchemes(false)}>
          <div className="schemes-modal" onClick={(e) => e.stopPropagation()}>
            <div className="schemes-modal-header">
              <div className="schemes-modal-title">
                <Sparkles size={18} className="text-saffron" />
                {language === 'hi' ? 'सभी पात्र योजनाएं' : 'All Eligible Schemes'}
              </div>
              <button className="modal-close-btn" onClick={() => setShowAllSchemes(false)} style={{ padding: '4px 8px' }}>
                <X size={16} />
              </button>
            </div>
            <div className="schemes-modal-body">
              {schemeRecommendations.map((rec, i) => (
                <div key={i} className={`scheme-rec-item ${rec.likely_eligible ? 'eligible' : 'partial'}`}>
                  <div className="scheme-rec-top">
                    <div className="scheme-rec-name" style={{ fontSize: '1rem' }}>
                      {language === 'hi' ? rec.scheme_name_hi : rec.scheme_name_en}
                    </div>
                    <span className={`scheme-rec-badge ${rec.likely_eligible ? 'eligible' : 'partial'}`}>
                      {rec.likely_eligible
                        ? (language === 'hi' ? '✓ पात्र' : '✓ Eligible')
                        : (language === 'hi' ? '~ आंशिक' : '~ Partial')}
                    </span>
                  </div>
                  <div className="scheme-rec-reason" style={{ fontSize: '0.85rem' }}>{rec.reason}</div>
                  <button
                    className="how-to-apply-btn"
                    onClick={() => handleHowToApply(rec)}
                    style={{ marginTop: '8px', alignSelf: 'flex-start', padding: '4px 10px', fontSize: '0.8rem', borderRadius: '4px', border: '1px solid var(--saffron)', background: 'var(--saffron-pale)', color: 'var(--saffron-dim)', cursor: 'pointer', fontWeight: 600 }}
                  >
                    {language === 'hi' ? 'आवेदन कैसे करें?' : 'How to Apply?'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── How to Apply Modal ── */}
      {(howToApplyState.loading || howToApplyState.data || howToApplyState.error) && (
        <div className="schemes-modal-overlay" onClick={() => {
          if (howToApplyState.audio) {
            howToApplyState.audio.pause();
            setStatus('idle');
          }
          setHowToApplyState({ loading: false, data: null, error: null, audio: null });
        }}>
          <div className="schemes-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
            <div className="schemes-modal-header">
              <div className="schemes-modal-title">
                <Sparkles size={18} className="text-saffron" />
                {howToApplyState.data ? howToApplyState.data.scheme_name : (language === 'hi' ? 'मार्गदर्शिका लोड हो रही है...' : 'Loading Guide...')}
              </div>
              <button className="modal-close-btn" onClick={() => {
                if (howToApplyState.audio) {
                  howToApplyState.audio.pause();
                  setStatus('idle');
                }
                setHowToApplyState({ loading: false, data: null, error: null, audio: null });
              }} style={{ padding: '4px 8px' }}>
                <X size={16} />
              </button>
            </div>

            <div className="schemes-modal-body">
              {howToApplyState.loading && (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
                  <div className="scheme-rec-spinner"><div className="scheme-rec-dot" /><div className="scheme-rec-dot" /><div className="scheme-rec-dot" /></div>
                  <p>{language === 'hi' ? 'आवेदन प्रक्रिया तैयार की जा रही है...' : 'Generating application steps...'}</p>
                </div>
              )}

              {howToApplyState.error && (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--crimson)' }}>
                  <AlertTriangle size={32} style={{ margin: '0 auto 12px' }} />
                  <p>{howToApplyState.error}</p>
                </div>
              )}

              {howToApplyState.data && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

                  {/* Speaker indicator */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', background: 'var(--cream-dark)', borderRadius: 'var(--r-sm)', color: 'var(--saffron)' }}>
                    <Activity size={16} className={status === 'speaking' ? 'status-indicator-icon' : ''} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                      {status === 'speaking'
                        ? (language === 'hi' ? 'AI बोल रहा है...' : 'AI is speaking...')
                        : (language === 'hi' ? 'मार्गदर्शिका' : 'Application Guide')}
                    </span>
                  </div>

                  {/* Steps Roadmap */}
                  <div>
                    <h4 style={{ color: 'var(--text-dark)', marginBottom: '12px', fontSize: '1.05rem' }}>
                      {language === 'hi' ? 'आवेदन करने के चरण' : 'Application Roadmap'}
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {howToApplyState.data.steps.map((step, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '12px', background: 'var(--paper)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--r-sm)' }}>
                          <div style={{ flexShrink: 0, width: '28px', height: '28px', borderRadius: '50%', background: 'var(--saffron)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: '0.9rem' }}>
                            {step.step_number}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-dark)', fontSize: '0.95rem', marginBottom: '4px' }}>{step.title}</div>
                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.5 }}>{step.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Documents */}
                  {howToApplyState.data.documents && howToApplyState.data.documents.length > 0 && (
                    <div style={{ background: 'rgba(212, 114, 12, 0.05)', padding: '16px', borderRadius: 'var(--r-sm)', border: '1px solid rgba(212, 114, 12, 0.2)' }}>
                      <h4 style={{ color: 'var(--text-dark)', marginBottom: '10px', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '1.2rem' }}>📄</span>
                        {language === 'hi' ? 'आवश्यक दस्तावेज़' : 'Required Documents'}
                      </h4>
                      <ul style={{ margin: 0, paddingLeft: '24px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {howToApplyState.data.documents.map((doc, idx) => (
                          <li key={idx} style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{doc}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
