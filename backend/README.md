# FRIDAY AI — Backend Service

A production-oriented, modular backend architecture for **FRIDAY**, the personal AI assistant.

---

## 1. Architecture Overview & Tech Stack

- **Framework**: Python 3.13 + [FastAPI](https://fastapi.tiangolo.com/) (Async ASGI)
- **Database**: [SQLAlchemy 2.0 Async](https://www.sqlalchemy.org/) + SQLite ([aiosqlite](https://github.com/omnilib/aiosqlite))
- **Scheduler**: [APScheduler 3.10](https://apscheduler.readthedocs.io/) (Database-backed, Timezone: `Asia/Kolkata`)
- **Schema Validation**: [Pydantic v2](https://docs.pydantic.dev/) + `pydantic-settings`
- **Authentication**: Bearer JWT + API Key headers (`X-API-Key`) + Role-based permissions
- **Testing**: [pytest](https://docs.pytest.org/) + `pytest-asyncio` + `httpx`

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── agents/          # Windows Desktop & Android Companion protocols
│   ├── ai/              # AI Orchestrator, multi-step planning, providers
│   ├── api/v1/          # REST & WebSocket API endpoints
│   ├── calls/           # Phone call workflow & contact resolution
│   ├── core/            # Config, security, emergency stop
│   ├── database/        # Async session engine & declarative Base
│   ├── memory/          # Permanent memory service (facts, preferences)
│   ├── messaging/       # WhatsApp automation & strict saved-contact policy
│   ├── models/          # SQLAlchemy ORM models
│   ├── scheduler/       # Timezone-aware persistent reminder scheduler
│   ├── schemas/         # Pydantic v2 request/response models
│   ├── tasks/           # Bounded concurrency task execution engine
│   ├── tools/           # Secure tool registry (system_info, open_app, etc.)
│   ├── voice/           # Voice session state machine, STT, TTS, biometric auth
│   └── main.py          # FastAPI application entrypoint & lifespan
├── docs/                # Architecture diagrams & implementation plan
├── tests/               # Automated test suite
├── .env.example         # Environment template
├── pytest.ini           # Test runner configuration
├── requirements.txt     # Python dependencies manifest
└── README.md
```

---

## 3. Installation & Quick Start

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.15)
- Windows / macOS / Linux

### Setup Instructions

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be live at:
- **API Base**: `http://localhost:8000/api/v1`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **WebSocket Tasks Stream**: `ws://localhost:8000/ws/tasks`

---

## 4. Running Automated Tests

```bash
cd backend
.\venv\Scripts\pytest -v
```

**Test Verification Summary**:
- `test_health_endpoint`: Verified service readiness & database connectivity.
- `test_strict_saved_contact_auto_reply_blocked`: Verified that saved contacts are **strictly blocked** from receiving auto-replies.
- `test_unknown_contact_auto_reply_policy`: Verified default-deny fail-safe on unknown numbers.
- `test_memory_creation_search_and_deletion`: Verified persistent memory storage, keyword search, and immediate deletion.
- `test_forbidden_sensitive_data_memory_rejection`: Verified rejection of passwords, PINs, and credit cards.
- `test_task_execution_lifecycle_and_progress`: Verified task concurrency, progress reporting, and completion.
- `test_emergency_stop_halts_automation`: Verified global emergency kill-switch halts all tasks and messages.
- `test_natural_language_command_orchestration`: Verified multi-step planning and tool execution.

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health, DB connectivity, and emergency stop status |
| `POST` | `/api/v1/commands` | Natural language instruction orchestration |
| `POST` | `/api/v1/tasks` | Create and enqueue an asynchronous task |
| `POST` | `/api/v1/tasks/batch` | Enqueue multiple concurrent tasks |
| `GET` | `/api/v1/tasks` | List recent task states and execution telemetry |
| `POST` | `/api/v1/tasks/{id}/cancel` | Cancel an active task |
| `GET` | `/api/v1/memory` | Retrieve saved facts and user preferences |
| `POST` | `/api/v1/memory` | Store a new approved memory |
| `DELETE` | `/api/v1/memory/{id}` | Delete a memory upon explicit user request |
| `GET` | `/api/v1/reminders` | List scheduled reminders and cron jobs |
| `POST` | `/api/v1/reminders` | Schedule a timezone-aware reminder |
| `POST` | `/api/v1/messaging/inbound` | Inbound message webhook with saved-contact check |
| `GET` | `/api/v1/messaging/policy-check` | Verify auto-reply policy for a phone number |
| `POST` | `/api/v1/calls/initiate` | Initiate call workflow with Android companion |
| `POST` | `/api/v1/voice/enroll` | Enroll primary speaker voice signature |
| `POST` | `/api/v1/voice/verify` | Verify speaker biometric confidence score |
| `POST` | `/api/v1/emergency/toggle` | Toggle emergency kill-switch |
| `WS` | `/ws/tasks` | Live WebSocket streaming for frontend task pop-ups |

---

## 6. Frontend Integration

The frontend ([`frontend/`](file:///c:/Users/HP/OneDrive/Desktop/FRIDAY/frontend)) is pre-configured with [`fridayApi.js`](file:///c:/Users/HP/OneDrive/Desktop/FRIDAY/frontend/src/services/fridayApi.js). 

When the backend server runs on `http://localhost:8000`:
1. The frontend automatically detects the active backend.
2. WebSocket task updates stream directly into the floating task HUD windows.
3. Natural language commands submitted through the interface are processed by the core AI orchestrator.
4. When the backend is offline, the frontend falls back to local simulation mode without errors.

---

## 7. Platform Integration Contracts

### Windows Client Agent
- Dispatches requests to open approved applications (`chrome`, `notepad`, `calculator`, `powershell`, `code`).
- Requires authenticated device token with `device:execute` capability.

### Android Companion Client
- Phone calls and messaging adhere to Android permission boundaries.
- The companion app must explicitly confirm outgoing calls and access contact address books.
