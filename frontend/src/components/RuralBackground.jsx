import React from 'react';

function RuralFarmer() {
  return (
    <svg viewBox="0 0 80 150" fill="none" xmlns="http://www.w3.org/2000/svg" className="rural-char rural-char-farmer">
      {/* Turban */}
      <path d="M25 45 Q30 35 45 40 Q55 45 50 55 Q40 60 25 50 Z" fill="#D4720C"/>
      <path d="M45 40 Q50 30 60 38 Q55 48 45 40 Z" fill="#F5A623"/>
      {/* Turban tail */}
      <path d="M50 50 Q60 70 55 90" stroke="#D4720C" strokeWidth="8" strokeLinecap="round" fill="none"/>
      {/* Head */}
      <circle cx="40" cy="52" r="12" fill="#FDBF6F"/>
      {/* Mustache */}
      <path d="M34 56 Q40 52 46 56" stroke="#3D2B1F" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
      <path d="M34 56 Q32 58 35 60" stroke="#3D2B1F" strokeWidth="2" fill="none" strokeLinecap="round"/>
      <path d="M46 56 Q48 58 45 60" stroke="#3D2B1F" strokeWidth="2" fill="none" strokeLinecap="round"/>
      {/* Eyes */}
      <circle cx="36" cy="50" r="1.5" fill="#3D2B1F"/>
      <circle cx="44" cy="50" r="1.5" fill="#3D2B1F"/>
      {/* Body / Kurta */}
      <path d="M25 65 Q40 60 55 65 L60 100 Q40 105 20 100 Z" fill="#F5F0E8"/>
      {/* Arms */}
      <path d="M25 68 L15 95 L22 98" stroke="#FDBF6F" strokeWidth="7" strokeLinecap="round" fill="none"/>
      <path d="M55 68 L65 95 L58 98" stroke="#FDBF6F" strokeWidth="7" strokeLinecap="round" fill="none"/>
      {/* Dhoti */}
      <path d="M20 100 L15 135 Q40 145 65 135 L60 100 Z" fill="#FFFFFF" stroke="#E0E0E0" strokeWidth="1"/>
      <path d="M40 105 L40 138" stroke="#E0E0E0" strokeWidth="2"/>
      {/* Feet */}
      <ellipse cx="25" cy="140" rx="8" ry="4" fill="#FDBF6F"/>
      <ellipse cx="55" cy="140" rx="8" ry="4" fill="#FDBF6F"/>
      {/* Stick / Lathi */}
      <line x1="62" y1="50" x2="68" y2="145" stroke="#6B4226" strokeWidth="4" strokeLinecap="round"/>
    </svg>
  );
}

function RuralWomanWater() {
  return (
    <svg viewBox="0 0 80 150" fill="none" xmlns="http://www.w3.org/2000/svg" className="rural-char rural-char-woman">
      {/* Pot on head */}
      <ellipse cx="40" cy="20" rx="14" ry="5" fill="#C1440E"/>
      <path d="M28 20 Q20 35 40 40 Q60 35 52 20 Z" fill="#A03008"/>
      <ellipse cx="40" cy="15" rx="8" ry="2" fill="#D4720C"/>
      <rect x="32" y="15" width="16" height="5" fill="#C1440E"/>
      {/* Head cloth */}
      <path d="M26 40 Q40 35 54 40 L58 60 Q40 50 22 60 Z" fill="#D4720C"/>
      {/* Head */}
      <circle cx="40" cy="48" r="11" fill="#FDBF6F"/>
      {/* Hair peeking */}
      <path d="M29 45 Q40 38 51 45" fill="#3D2B1F"/>
      {/* Earrings */}
      <circle cx="28" cy="50" r="2" fill="#E8C547"/>
      <circle cx="52" cy="50" r="2" fill="#E8C547"/>
      {/* Bindi */}
      <circle cx="40" cy="44" r="1.5" fill="#C1440E"/>
      {/* Eyes */}
      <circle cx="35" cy="48" r="1.2" fill="#3D2B1F"/>
      <circle cx="45" cy="48" r="1.2" fill="#3D2B1F"/>
      {/* Smile */}
      <path d="M37 53 Q40 55 43 53" stroke="#A03008" strokeWidth="1" fill="none"/>
      {/* Saree - upper body */}
      <path d="M28 65 Q40 60 52 65 L55 105 L25 105 Z" fill="#E8803A"/>
      {/* Saree drape */}
      <path d="M52 65 Q58 70 55 80 L52 75 Z" fill="#D4720C"/>
      {/* Border design */}
      <rect x="25" y="100" width="30" height="5" fill="#D4720C"/>
      {/* Arms - raised to support pot */}
      <path d="M28 68 L22 45 L26 43" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none"/>
      <path d="M52 68 L58 45 L54 43" stroke="#FDBF6F" strokeWidth="6" strokeLinecap="round" fill="none"/>
      {/* Skirt/saree lower */}
      <path d="M25 105 Q30 130 35 135 L45 135 Q50 130 55 105 Z" fill="#E8803A"/>
      {/* Feet */}
      <ellipse cx="35" cy="136" rx="7" ry="4" fill="#FDBF6F"/>
      <ellipse cx="45" cy="136" rx="7" ry="4" fill="#FDBF6F"/>
      {/* Anklets */}
      <rect x="28" y="132" width="14" height="2" rx="1" fill="#E8C547"/>
      <rect x="38" y="132" width="14" height="2" rx="1" fill="#E8C547"/>
    </svg>
  );
}

function RuralTree({ x, y, scale = 1, flip = false }) {
  const leafDuration = 5 + (x % 3);
  return (
    <svg 
      style={{
        position: 'absolute',
        bottom: `${y}px`,
        left: flip ? 'auto' : `${x}px`,
        right: flip ? `${x}px` : 'auto',
        transform: `scale(${scale}) ${flip ? 'scaleX(-1)' : ''}`,
        transformOrigin: 'bottom center',
        pointerEvents: 'none',
        opacity: 0.8
      }}
      width="120" height="160" viewBox="0 0 120 160" fill="none"
    >
      <path d="M50 160 Q55 100 60 160 Z" fill="#6B4226" />
      <path d="M55 120 Q70 100 80 90" stroke="#6B4226" strokeWidth="4" strokeLinecap="round" />
      <path d="M55 130 Q40 110 30 100" stroke="#6B4226" strokeWidth="4" strokeLinecap="round" />
      <g style={{ transformOrigin: '60px 110px', animation: `wave-leaves ${leafDuration}s ease-in-out infinite` }}>
        <ellipse cx="60" cy="70" rx="45" ry="50" fill="#2D6A4F" />
        <ellipse cx="40" cy="50" rx="30" ry="35" fill="#52B788" />
        <ellipse cx="80" cy="60" rx="35" ry="40" fill="#1A4A2E" />
        <ellipse cx="60" cy="40" rx="25" ry="25" fill="#74C69D" />
      </g>
    </svg>
  );
}

function RuralCloud({ x, y, scale = 1, opacity = 0.6 }) {
  // Use a different animation duration based on scale/x to make them look distinct
  const duration = 15 + (x % 10);
  return (
    <div style={{
      position: 'absolute',
      top: `${y}px`,
      left: `${x}%`,
      animation: `float-cloud ${duration}s ease-in-out infinite`,
      pointerEvents: 'none',
      opacity
    }}>
      <svg
        style={{ transform: `scale(${scale})` }}
        width="100" height="40" viewBox="0 0 100 40" fill="none"
      >
        <path d="M20 25 Q20 15 30 15 Q35 5 50 5 Q65 5 70 15 Q80 15 80 25 Z" fill="#DCE5ED" />
        <path d="M10 30 Q10 20 20 20 L80 20 Q90 20 90 30 Z" fill="#DCE5ED" />
        <rect x="10" y="25" width="80" height="10" rx="5" fill="#DCE5ED" />
      </svg>
    </div>
  );
}

function RuralBird({ x, y, scale = 1, flip = false }) {
  const duration = 5 + (x % 5);
  return (
    <div style={{
      position: 'absolute',
      top: `${y}px`,
      left: flip ? 'auto' : `${x}%`,
      right: flip ? `${x}%` : 'auto',
      animation: `fly-bird ${duration}s ease-in-out infinite`,
      pointerEvents: 'none',
      opacity: 0.5
    }}>
      <svg
        style={{ transform: `scale(${scale}) ${flip ? 'scaleX(-1)' : ''}` }}
        width="40" height="20" viewBox="0 0 40 20" fill="none"
      >
        <path d="M5 10 Q10 0 20 10 Q30 0 35 10" stroke="#3D2B1F" strokeWidth="2" strokeLinecap="round" fill="none" />
      </svg>
    </div>
  );
}

function RuralSun() {
  return (
    <div style={{
      position: 'absolute',
      top: '20px',
      right: '40px',
      pointerEvents: 'none'
    }}>
      <svg
        style={{ animation: 'spin-slow 20s linear infinite' }}
        width="80" height="80" viewBox="0 0 80 80" fill="none"
      >
        <circle cx="40" cy="40" r="36" fill="#F5A623" opacity="0.1" style={{ transformOrigin: '40px 40px', animation: 'pulse-sun-outer 4s ease-in-out infinite' }} />
        <circle cx="40" cy="40" r="28" fill="#F5A623" opacity="0.3" style={{ transformOrigin: '40px 40px', animation: 'pulse-sun 4s ease-in-out infinite' }} />
        <circle cx="40" cy="40" r="20" fill="#F5A623" />
      </svg>
    </div>
  );
}

export default function RuralBackground() {
  return (
    <div className="rural-background-container" style={{
      position: 'absolute',
      inset: 0,
      overflow: 'hidden',
      pointerEvents: 'none',
      zIndex: 0
    }}>
      {/* Background soft hills */}
      <svg style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: '30vh', opacity: 0.15 }} viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path fill="#2D6A4F" fillOpacity="1" d="M0,224L60,208C120,192,240,160,360,170.7C480,181,600,235,720,234.7C840,235,960,181,1080,170.7C1200,160,1320,192,1380,208L1440,224L1440,320L1380,320C1320,320,1200,320,1080,320C960,320,840,320,720,320C600,320,480,320,360,320C240,320,120,320,60,320L0,320Z"></path>
      </svg>
      
      <svg style={{ position: 'absolute', bottom: 0, left: 0, width: '100%', height: '20vh', opacity: 0.2 }} viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path fill="#52B788" fillOpacity="1" d="M0,160L80,165.3C160,171,320,181,480,170.7C640,160,800,128,960,133.3C1120,139,1280,181,1360,202.7L1440,224L1440,320L1360,320C1280,320,1120,320,960,320C800,320,640,320,480,320C320,320,160,320,80,320L0,320Z"></path>
      </svg>

      {/* Sky elements */}
      <RuralSun />
      <RuralCloud x={10} y={40} scale={1.2} opacity={0.8} />
      <RuralCloud x={75} y={20} scale={0.8} opacity={0.65} />
      <RuralCloud x={45} y={60} scale={1} opacity={0.75} />
      
      <RuralBird x={15} y={50} scale={0.8} />
      <RuralBird x={18} y={40} scale={0.6} />
      <RuralBird x={70} y={30} scale={0.9} flip={true} />
      <RuralBird x={74} y={35} scale={0.7} flip={true} />

      {/* Trees */}
      <RuralTree x={40} y={10} scale={1.2} />
      <RuralTree x={120} y={30} scale={0.8} flip={true} />
      <RuralTree x={40} y={15} scale={1.4} flip={true} /> {/* For right side when flip is used for positioning in props above */}

      <div style={{ position: 'absolute', bottom: '20px', left: '10%', transform: 'scale(1.2)' }}>
        <RuralFarmer />
      </div>
      <div style={{ position: 'absolute', bottom: '30px', right: '15%', transform: 'scale(1.15) scaleX(-1)' }}>
        <RuralWomanWater />
      </div>
      
      <RuralTree x={80} y={5} scale={1.5} flip={true} />
    </div>
  );
}
