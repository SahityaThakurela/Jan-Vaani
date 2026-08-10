# Jan Vaani (janvaani.ai) — Rural Government Scheme Voice Helpline

> **StarForge Hackathon 2026 (VoxForge Track)**  
> *A voice-first platform for rural, low-literacy Indian users to navigate government welfare schemes hands-free, in their own language.*

---

## 🏗️ Architecture Overview

Jan Vaani uses a dual-brain architecture designed specifically for **High-Trust Voice Workflows**:

1. **LLM (Google Gemini 2.0 Flash)**: Handles natural speech understanding, intent classification, structured slot extraction, and short natural voice reply generation.
2. **Deterministic Rules Engine (Plain Python, Zero AI)**: Evaluates structured field/operator/value rules against collected profile data. **The LLM never makes eligibility decisions.**

```
User (Voice) ──► React Frontend (Push-to-talk / Interruption)
                       │
                       ▼
              FastAPI Backend Pipeline (/voice/turn)
                       │
         ┌─────────────┼─────────────────────────┐
         ▼             ▼                         ▼
   Deepgram STT   Gemini 2.0 Flash        Qdrant Vector DB
   (Nova-2)       (Intent & Slot Extr.)   (Scheme Knowledge Hybrid Search)
                       │
                       ▼
            State Machine & Slot Mgr
            (Correction Overwrite PK)
                       │
                       ▼
           Deterministic Rules Engine ──► Cross-Scheme Matcher
                       │
                       ▼
                 Rime TTS (Coda)
               (MP3 Voice Stream)
```

---

## 🌟 Key Features

- **Voice-First Navigation**: Optimized for rural Indian low-literacy users in Hindi and English.
- **Auditable Eligibility**: Rule evaluation done by pure Python engine with exact failed rule reports and missing slot lists.
- **Cross-Scheme Matching**: Automatically checks filled profile slots against all schemes in the database.
- **Correction Recovery**: Interruption or answer correction ("nahi, 3 acre zameen hai") overwrites existing slots seamlessly via SQLite `(session_id, slot_name)` composite primary key.
- **Tap to Interrupt**: Immediate state reset preserving captured slots so the user can re-ask or pivot without starting over.
- **Safe Human Handoff**: Triggers on low confidence, borderline eligibility, or explicit user request, sending a structured payload to a simulated human operator dashboard.
- **Mandatory Rime & Qdrant Integration**: Uses Rime Coda (`mist` model) for speech synthesis and Qdrant for hybrid knowledge retrieval.

---

## 📁 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI entrypoint
│   │   ├── config.py                 # Pydantic-settings config
│   │   ├── api/routes/              # Session, Voice, Schemes, Eligibility, Handoff
│   │   ├── core/                     # State machine & Slot manager
│   │   ├── services/                 # STT, TTS (Rime), LLM (Gemini), Qdrant, Eligibility Engine
│   │   ├── models/                   # SQLAlchemy DB models & Pydantic schemas
│   │   ├── data/                     # Seed JSON & Qdrant vector seed script
│   │   └── db/                       # Database initialization
│   ├── tests/                        # Pytest suite for eligibility engine
│   ├── .env.example
│   └── requirements.txt
└── frontend/                         # Vite + React interface
```

---

## ⚡ Quickstart

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` file (copied from `.env.example`):

```ini
RIME_API_KEY=HFlvOlQ-OmWTDmhaKR51NrlmJkBsTqSv0A-xR7_weXo
GEMINI_API_KEY=your-gemini-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key
QDRANT_URL=http://localhost:6333
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload --port 8000
```

Seed Qdrant Knowledge Vector DB (Requires Qdrant running locally or on Qdrant Cloud):

```bash
python -m app.data.seed_qdrant
```

### 2. Run Tests

```bash
cd backend
pytest tests/ -v
```

---

## ⚠️ Stated Limitations

1. **Seeded Data**: 2 core government schemes included for demo (PM-KISAN and PMAY-G).
2. **Turn-Based Interruption**: Push-to-talk turn-taking used rather than full-duplex barge-in.
3. **Simulated Handoff**: Handoff transfers structured JSON data to a simulated human agent UI rather than real PSTN telephony.
4. **Synthetic Data**: All test persona details are synthetic.
