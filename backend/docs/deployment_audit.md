# FRIDAY AI — Pre-Deployment Architecture & Issue Audit

**Audit Date**: 2026-10-10T19:40:00+05:30  
**Target Environments**:  
- **Frontend**: Vercel (Vite + React SPA)  
- **Backend**: Render Web Service (FastAPI ASGI + Uvicorn)  
- **Protocols**: HTTPS (REST) & WSS (WebSockets)  

---

## 1. Discovered Architecture & Components

### Frontend
- **Framework**: React 19 + Vite 8
- **Styling**: Vanilla CSS (`App.css`, `index.css`) with strict HUD theme: `#000000` pure black background, `#D84B10` / `#FF8C42` holographic accents, floating HUD cards, 3D Fibonacci network sphere canvas.
- **Computer Vision / Gestures**: `@mediapipe/tasks-vision` (HandLandmarker) in `useHandGesture.js`.
- **State & Networking**: `useFridayState.js`, `fridayApi.js` (REST fetch + native WebSocket client).

### Backend
- **Framework**: Python 3.13 + FastAPI
- **Database**: SQLAlchemy 2.0 Async + SQLite (`aiosqlite`) / PostgreSQL (`asyncpg`)
- **Scheduler**: APScheduler 3.10 (timezone-aware `Asia/Kolkata`)
- **Execution & AI**: Async task engine with bounded concurrency, AI orchestrator with rule-based NLP + external provider interfaces (OpenAI / Gemini).
- **Security & Safety**: Biometric acoustic voice verification, anti-replay nonce tracking, strict block on automated replies to saved contacts, emergency kill-switch.

---

## 2. Issues Identified During Pre-Deployment Audit

### Issue 1: Voice Command Pipeline Incomplete / Silent Failure
- **Root Cause**: The frontend did not connect microphone input to browser speech recognition (`window.SpeechRecognition` / `window.webkitSpeechRecognition`). Clicking the central globe or toggling states merely altered the visual state variable without opening audio capture or dispatching speech to `/api/v1/commands`.
- **Impact**: When speaking, FRIDAY remained silent and executed no backend tasks.
- **Required Fix**: Implement a comprehensive `useVoiceAssistant` hook that initiates speech recognition on user interaction, passes the final transcript to `FridayApiClient.submitCommand`, spawns returned tasks in the HUD, and audibly synthesizes the response using `window.speechSynthesis`.

### Issue 2: Hand-Gesture Camera Initialization & Video Lifecycle
- **Root Cause**: In `useHandGesture.js`, `video.onloadeddata` could hang without firing in certain browser security contexts. The MediaPipe WASM CDN used `@latest` which can cause version mismatch with the installed `@mediapipe/tasks-vision` package.
- **Impact**: Camera state could stay stuck in `requesting` or fail silently.
- **Required Fix**: Update `onloadedmetadata` event listener, attach explicit video track dimensions, handle fallback for vision task resolvers, and ensure clean stream/animation frame cleanup.

### Issue 3: Hardcoded Localhost API & Insecure WebSocket URLs
- **Root Cause**: `frontend/src/services/fridayApi.js` hardcoded `http://localhost:8000/api/v1` and `ws://localhost:8000/ws/tasks`.
- **Impact**: When deployed to Vercel, the frontend would fail to connect to the deployed Render backend and cause Mixed Content (HTTPS -> HTTP / WSS -> WS) security blocks.
- **Required Fix**: Derive API base and WebSocket URLs dynamically from `import.meta.env.VITE_API_BASE_URL` with automatic protocol upgrade (`http -> ws`, `https -> wss`).

### Issue 4: Missing Vercel SPA Routing Configuration
- **Root Cause**: No `vercel.json` rewrite file existed in `frontend/`.
- **Impact**: Direct navigation or page refreshes on sub-routes in Vercel would return 404 Not Found.
- **Required Fix**: Create `frontend/vercel.json` with SPA rewrite rules to `/index.html`.

### Issue 5: Render Production Configuration & Database Persistence
- **Root Cause**: Backend lacked a `render.yaml` blueprint, and `app/database/session.py` only handled local SQLite paths without parsing managed PostgreSQL URLs (`postgres://` / `postgresql+asyncpg://`).
- **Impact**: Render deployments would lack build/start specifications, and ephemeral disk restarts would lose database state if Postgres or persistent disk is not configured.
- **Required Fix**: Create `render.yaml`, adapt `app/database/session.py` to support both SQLite persistent disk and Render PostgreSQL (`asyncpg`), bind dynamically to `$PORT`, and configure CORS for Vercel production domains.

---

## 3. Implementation Plan

1. **Voice Pipeline**: Build and wire `useVoiceAssistant.js` with speech recognition, NLP command execution, task spawning, and speech synthesis.
2. **Gesture Tracking**: Harden `useHandGesture.js` for reliable camera permissions, frame capture, and cleanup.
3. **API & WebSockets**: Update `fridayApi.js` to support environment variables, `wss://`, and connection recovery.
4. **Vercel Setup**: Add `frontend/vercel.json` and `.env.example`.
5. **Render Setup**: Add `render.yaml`, update `app/core/config.py` and `app/database/session.py`.
6. **Testing & Verification**: Execute backend test suite, run Vite production build, verify live server, and generate comprehensive documentation.
