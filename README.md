# Jan Vaani (janvaani.ai) — Rural Government Scheme Voice Helpline

**Live Demo:** https://jan-vaani-01.vercel.app/

*A voice-first platform for rural, low-literacy Indian users to navigate government welfare schemes hands-free, in their own language.*

<p align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/Vite-B73BFE?style=for-the-badge&logo=vite&logoColor=FFD62E" alt="Vite" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Qdrant-1F1F1F?style=for-the-badge&logo=qdrant&logoColor=E5487B" alt="Qdrant" />
  <img src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

---

## 🎯 Why We Built This

In much of rural India, the biggest barrier to accessing government welfare schemes isn't awareness — it's the interface. Scheme portals assume literacy, English or formal Hindi comprehension, stable smartphone/data access, and the confidence to fill out forms correctly. For a large population, that gap means entitled benefits (pensions, housing, agricultural subsidies) simply go unclaimed, not because people are ineligible, but because the discovery and application process was never designed for them.

We built Jan Vaani because this is a solvable interface problem, not a policy problem. Everyone can speak; not everyone can read a government form. By making scheme discovery and eligibility-checking a natural spoken conversation in Hindi or English, we remove the literacy and digital-navigation barrier entirely — a user can just talk, the way they would to a helpful person at a local office.

**What this contributes technically:** the core challenge in a system like this isn't conversational fluency — LLMs handle that well. It's trust. A welfare eligibility determination has real consequences, so it cannot be left to a generative model's best guess. Jan Vaani's contribution is a **Dual-Brain Architecture** that cleanly separates these concerns:

- A **generative layer** (LLM) handles the genuinely unstructured part of the problem: understanding free-form speech, extracting intent, and pulling out demographic facts (age, income, state, etc.) from however the user happens to phrase them.
- A **deterministic rules engine** handles the high-stakes part: evaluating those extracted facts against scheme eligibility criteria using pure, auditable Python logic. The LLM never decides eligibility — it only ever populates the inputs to a rule it cannot influence.

This separation, combined with an auditable "why did/didn't I qualify" trace and a low-confidence human handoff path, is what makes a voice-AI system usable for something as consequential as welfare access, rather than just a novelty demo.

---

## 🎥 Product Demo

> **[Add your demo video link/embed here — e.g. a YouTube link or a GitHub-hosted MP4]**
>
> Example once you have it:
> [![Watch the demo](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://youtu.be/YOUR_VIDEO_ID)

You can also try the live deployment directly: **https://jan-vaani-01.vercel.app/**

---

## 🏗️ Architecture Overview

Jan Vaani uses a pipeline optimized for **high-trust voice workflows**:

```text
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

### The Pipeline Flow:
1. **Speech-to-Text (Deepgram)**: Converts user's audio into text (Hindi/English).
2. **Intent & Slot Extraction (Gemini)**: The LLM classifies what the user wants (search, detail, check eligibility, correct information) and extracts demographic facts (age, income, state, etc.).
3. **State Management**: A finite state machine tracks the conversation context (e.g., waiting for scheme name, collecting slots).
4. **Knowledge Retrieval (Qdrant)**: RAG (Retrieval-Augmented Generation) is used to pull specific scheme details from a vector database.
5. **Eligibility Engine (Python)**: If checking eligibility, a pure Python rules engine evaluates the extracted slots against the scheme's criteria.
6. **Text-to-Speech (Rime)**: The agent's text response is converted back into high-quality, natural-sounding audio. Hindi uses the **Coda** model (`nadi` speaker), while English uses the **Mist** model (`maya` speaker).

---

## 🌟 Key Features

- **Voice-First Navigation**: Optimized for rural Indian low-literacy users in Hindi and English. No typing required.
- **Auditable Eligibility**: Rule evaluation is done by a pure Python engine with exact failed rule reports and missing slot lists.
- **Cross-Scheme Matching**: Automatically checks filled profile slots against all schemes in the database to recommend alternatives.
- **Correction Recovery**: Interruption or answer correction (e.g., "nahi, meri aayu 25 hai") overwrites existing slots seamlessly via the composite primary key.
- **Tap to Interrupt**: Immediate state reset preserving captured slots so the user can re-ask or pivot without starting over.
- **Live Extracted Profile**: The frontend updates in real-time, showing a dashboard of "Collected Facts" and the user's basic credentials.
- **Safe Human Handoff**: Triggers on low confidence, borderline eligibility, or explicit user request, sending a structured payload to a human operator dashboard.
- **Session History**: Users can view transcripts and extracted facts from past conversations.

---

## 💻 Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **Database**: SQLite with SQLAlchemy ORM (async)
- **Vector DB**: Qdrant (for RAG scheme knowledge)
- **AI / LLM**: Google Gemini (gemini-2.0-flash)
- **STT (Speech-to-Text)**: Deepgram (Nova-2)
- **TTS (Text-to-Speech)**: Rime AI (Coda model for Hindi, Mist model for English)

### Frontend
- **Framework**: React 19 + Vite
- **Styling**: Vanilla CSS (Glassmorphic, responsive design)
- **Icons**: Lucide React
- **Routing**: React Router DOM

---

## 📁 Repository Structure

```text
Jan-Vaani/
├── backend/                          # FastAPI Backend Application
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/               # API Endpoints (auth, voice, session, etc.)
│   │   ├── core/                     # Core logic (auth, state machine, slot manager)
│   │   ├── data/                     # Seed data (JSON) & Qdrant vector seed script
│   │   ├── db/                       # Database connection and session setup
│   │   ├── models/                   # SQLAlchemy DB models & Pydantic schemas
│   │   ├── services/                 # External service integrations (STT, TTS, LLM, Engine)
│   │   ├── utils/                    # Helper functions (audio conversion, logging)
│   │   ├── config.py                 # Centralized environment variable management
│   │   └── main.py                   # FastAPI application entrypoint
│   ├── tests/                        # Pytest suite for eligibility engine and core logic
│   ├── .env.example                  # Environment variables template
│   └── requirements.txt              # Python dependencies
│
└── frontend/                         # React Frontend Application
    ├── public/                       # Static assets
    ├── src/
    │   ├── pages/                    # Route components (Landing, Login, Register)
    │   ├── App.jsx                   # Main application interface and voice workspace
    │   ├── index.css                 # Global styles and design system
    │   └── main.jsx                  # React entrypoint
    ├── index.html
    ├── package.json                  # Node.js dependencies
    └── vite.config.js                # Vite bundler configuration
```

---

## ⚡ Reproducibility / Quickstart

Follow these steps to set up the project locally and reproduce the results described above.

### 1. Backend Setup

Navigate to the backend directory and set up a virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Populate the `.env` file with your API keys:
```ini
RIME_API_KEY=your_rime_key
GEMINI_API_KEY=your_gemini_key
DEEPGRAM_API_KEY=your_deepgram_key
QDRANT_URL=http://localhost:6333
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

*Optional*: Seed the Qdrant Knowledge Vector DB (Requires Qdrant running locally or on Qdrant Cloud):
```bash
python -m app.data.seed_qdrant
```

### 2. Frontend Setup

In a new terminal window, navigate to the frontend directory:

```bash
cd frontend
npm install
```

Start the Vite development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`.

### 3. Docker Setup (Qdrant Vector DB)

The recommended way to run the Qdrant Vector DB locally is via Docker. Ensure you have Docker installed and running, then execute the following command:

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

Once the container is running, the Qdrant API will be available at `http://localhost:6333`. This matches the default `QDRANT_URL` in your `.env` file. You can then proceed to run the seeding script:

```bash
python -m app.data.seed_qdrant
```

*(Note: If you plan to containerize the entire application stack later, you can create a `docker-compose.yml` file to orchestrate the FastAPI backend, Vite frontend, and Qdrant database together.)*

### 4. Running Tests

To verify the deterministic eligibility engine is working as expected after setup:

```bash
cd backend
pytest tests/ -v
```

---

## 📊 Performance Metrics

> **[Fill in with your actual measured numbers before evaluation — see note below]**

| Metric | Result | Why this metric |
|---|---|---|
| Eligibility rule accuracy (test suite pass rate) | *e.g. XX/XX tests passing* | Eligibility is the highest-stakes output of the system; correctness here is measured deterministically via `pytest tests/`, not sampled, since the rules engine is pure logic. |
| End-to-end voice turn latency (STT → LLM → TTS) | *e.g. ~X.Xs avg* | Directly determines whether the conversation feels natural on a phone call vs. frustratingly slow — critical for a voice-first, hands-free UX. |
| Intent/slot extraction accuracy | *e.g. XX% on test utterances* | Measures how reliably the LLM layer captures the right facts (age, income, state, etc.) before they reach the deterministic engine — errors here are the main risk to correct eligibility outcomes. |
| RAG retrieval relevance (Qdrant) | *e.g. top-k hit rate* | Confirms the scheme knowledge surfaced to the user actually matches their query, rather than the LLM hallucinating scheme details. |

*(Replace the placeholder values with numbers from your own test runs/logs — see the note below.)*

---

## 🤝 Credits

This project was made possible by the tools and infrastructure provided by our hackathon partners:

- **[Pathway](https://pathway.com/)**
- **[Rime](https://rime.ai/)** — powering natural, low-latency Hindi and English text-to-speech (Coda and Mist models).
- **[Weya](https://weya.ai/)**
- **[Qdrant](https://qdrant.tech/)** — powering hybrid vector search over our government scheme knowledge base for RAG-based retrieval.

---

## ⚠️ Limitations & Notes

1. **Seeded Data**: Currently includes core government schemes for demonstration (e.g., PM-KISAN, PMAY-G).
2. **Turn-Based Interruption**: Uses a push-to-talk turn-taking mechanism rather than full-duplex barge-in (though interruption is supported via UI).
3. **Simulated Handoff**: Handoff transfers structured JSON data to a simulated human agent UI rather than real PSTN telephony.
4. **TTS Latency**: Audio generation latency depends on the Rime AI network response.