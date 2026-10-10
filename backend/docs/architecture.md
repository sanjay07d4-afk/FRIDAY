# FRIDAY AI — Subsystem Architecture & Integration Contracts

```mermaid
graph TD
    Client[Web Frontend / Windows Agent / Android Companion] -->|REST / WebSocket| Gateway[FastAPI API Gateway]
    
    subgraph Security_Layer [Security & Privacy Layer]
        Gateway --> Auth[API Key & JWT Auth]
        Gateway --> Emergency[Emergency Stop Controller]
        Gateway --> ContactPolicy[Strict Saved-Contact Filter]
    end

    subgraph Core_Intelligence [Core Intelligence & Planning]
        Auth --> Orchestrator[FridayAIOrchestrator]
        Orchestrator --> IntentParser[Intent & Entity Classifier]
        Orchestrator --> StepPlanner[Multi-Step Dependency Planner]
        Orchestrator --> AIProviders[OpenAI / Gemini / LocalRuleBased]
    end

    subgraph Execution_Engine [Task & Tool Execution]
        StepPlanner --> TaskEngine[Bounded TaskExecutionEngine]
        TaskEngine --> ToolRegistry[Secure ToolRegistry]
        ToolRegistry --> SysTool[system_info]
        ToolRegistry --> AppTool[open_application]
        ToolRegistry --> DocTool[summarize_text]
        ToolRegistry --> WeatherTool[get_weather]
    end

    subgraph Persistence_Subsystems [Persistent Storage Subsystems]
        Gateway --> MemorySvc[MemoryService\n(Facts, Preferences, Instructions)]
        Gateway --> SchedulerSvc[PersistentSchedulerService\n(APScheduler + Timezone)]
        Gateway --> MessagingSvc[MessagingAutomationService]
        Gateway --> CallSvc[PhoneCallService]
        
        MemorySvc --> SQLite[(friday.db\nSQLAlchemy Async)]
        SchedulerSvc --> SQLite
        MessagingSvc --> SQLite
        TaskEngine --> SQLite
    end

    subgraph RealTime_Streaming [Real-time Events]
        TaskEngine --> WS[WebSocket Broadcaster /ws/tasks]
        WS --> Client
    end
```

---

## Key Subsystem Contracts

### 1. Messaging Automation Contact Policy
- **Absolute Rule**: `is_saved == True` $\rightarrow$ `can_auto_reply = False` (Verdict: `DENIED`).
- **Unsaved Contacts**: Evaluated against explicit rule permissions (`MESSAGING_AUTO_REPLY_ENABLED`).
- **Audit Requirement**: Every incoming message and outbound reply logs an immutable audit entry in `audit_logs`.

### 2. Task Execution Lifecycle
- **States**: `queued` $\rightarrow$ `running` $\rightarrow$ (`completed` | `failed` | `cancelled` | `awaiting_confirmation`).
- **Concurrency**: Controlled via `asyncio.Semaphore(MAX_CONCURRENT_TASKS)` ensuring the server is never overwhelmed.
- **WebSockets**: Every state change broadcasts immediately to connected frontend clients on `/ws/tasks`.

### 3. Personal Memory Privacy
- **Consent-based**: Saved exclusively upon user instruction or explicit API invocation.
- **Forbidden Filter**: Rejects passwords, credit card numbers, CVVs, and secret tokens before committing to the database.
- **Deletion**: Soft or hard deletion removes records from search indexing immediately.
