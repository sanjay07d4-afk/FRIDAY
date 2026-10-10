import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from app.core.emergency import emergency_controller
from app.core.config import settings
from app.models.contact import ContactModel
from app.models.memory import MemoryModel
from app.models.reminder import ReminderModel
from app.messaging.service import messaging_service
from app.memory.service import memory_service
from app.scheduler.service import scheduler_service
from app.tasks.engine import task_engine
from app.tools.registry import tool_registry
from app.ai.providers import OpenAIProvider
from app.voice.verification import speaker_authenticator

@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Verify health endpoint returns healthy status and DB connectivity."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "FRIDAY AI" in data["service"]

@pytest.mark.asyncio
async def test_strict_saved_contact_auto_reply_blocked(client, db_session):
    """
    CRITICAL POLICY 1:
    Saved contacts must NEVER receive automatic replies under any circumstances.
    """
    # Register a saved contact
    saved_contact = ContactModel(
        name="Tony Stark",
        phone_number="+919876543210",
        is_saved=True,
        auto_reply_permitted=False
    )
    db_session.add(saved_contact)
    await db_session.commit()

    # Verify contact policy verdict
    policy = await messaging_service.verify_contact_policy(db_session, "+919876543210")
    assert policy["is_saved_contact"] is True
    assert policy["can_auto_reply"] is False
    assert policy["verdict"] == "DENIED"

    # Simulate inbound message from saved contact
    result = await messaging_service.process_inbound_message(
        db=db_session,
        sender_phone="+919876543210",
        message_text="Hey Friday, is the lab ready?"
    )
    assert result["auto_reply_sent"] is False
    assert result["status"] == "received_no_auto_reply"

@pytest.mark.asyncio
async def test_unknown_contact_auto_reply_policy(client, db_session):
    """
    CRITICAL POLICY 2:
    Unknown or ambiguous contact status results in no automatic reply when disabled.
    """
    settings.MESSAGING_AUTO_REPLY_ENABLED = False
    policy = await messaging_service.verify_contact_policy(db_session, "+919999999999")
    assert policy["is_saved_contact"] is False
    assert policy["can_auto_reply"] is False
    assert policy["verdict"] == "DENIED"

@pytest.mark.asyncio
async def test_disabling_automation_prevents_outgoing_actions(db_session):
    """
    CRITICAL POLICY 3:
    Disabling automation in settings prevents any automated reply even for unsaved numbers.
    """
    settings.MESSAGING_AUTO_REPLY_ENABLED = False
    inbound_res = await messaging_service.process_inbound_message(
        db=db_session,
        sender_phone="+918888888888",
        message_text="Hello, who is this?"
    )
    assert inbound_res["auto_reply_sent"] is False

@pytest.mark.asyncio
async def test_unauthorized_user_permission_rejection():
    """
    CRITICAL POLICY 4:
    Unauthorized users cannot execute protected tool operations without proper permissions.
    """
    # 'open_application' requires 'device:execute'
    with pytest.raises(PermissionError) as exc:
        await tool_registry.execute(
            tool_name="open_application",
            parameters={"app_name": "notepad"},
            context={"roles": ["guest"], "permissions": ["system:read"]}
        )
    assert "Missing required permission" in str(exc.value)

@pytest.mark.asyncio
async def test_emergency_stop_halts_automation(db_session):
    """
    CRITICAL POLICY 5:
    Emergency stop blocks new automation and safely cancels running tasks.
    """
    # 1. Activate Emergency Stop
    await emergency_controller.trigger(triggered_by="admin_test", reason="Security diagnostic test")
    assert emergency_controller.is_active is True

    # 2. Attempt task creation
    task = await task_engine.create_and_enqueue_task(
        task_type="system_info",
        title="Diagnostic Check"
    )
    await asyncio.sleep(0.1)
    task_res = task_engine.get_task(task["id"])
    assert task_res["status"] == "cancelled"
    assert "Emergency stop active" in task_res["error"]

    # 3. Attempt message dispatch
    msg_res = await messaging_service.send_message(
        db=db_session,
        recipient_phone="+919876543210",
        message_text="Test emergency block"
    )
    assert msg_res["sent"] is False
    assert "Emergency stop active" in msg_res["reason"]

    # 4. Reset Emergency Stop
    await emergency_controller.reset(reset_by="admin_test")
    assert emergency_controller.is_active is False

@pytest.mark.asyncio
async def test_secrets_not_exposed_in_api_responses(client):
    """
    CRITICAL POLICY 6:
    Secrets (API keys, secret keys, passwords) are not exposed in logs or API responses.
    """
    res = await client.get("/api/v1/health")
    text = res.text
    assert settings.SECRET_KEY not in text
    assert settings.API_KEY not in text

@pytest.mark.asyncio
async def test_memory_creation_search_and_deletion(client, db_session):
    """
    CRITICAL POLICY 7:
    Deleted memories are no longer available through ordinary retrieval.
    """
    # 1. Save memory
    mem = await memory_service.save_memory(
        db=db_session,
        content="Primary workshop security code is calibrated to Mark 42",
        category="fact",
        user_id="user_tony"
    )
    assert mem.id is not None

    # 2. Search memory
    results = await memory_service.search_memories(db_session, query="Mark 42", user_id="user_tony")
    assert len(results) == 1

    # 3. Delete memory
    deleted = await memory_service.delete_memory(db_session, memory_id=mem.id, user_id="user_tony")
    assert deleted is True

    # 4. Verify deleted memory is not returned
    post_delete_search = await memory_service.search_memories(db_session, query="Mark 42", user_id="user_tony")
    assert len(post_delete_search) == 0

@pytest.mark.asyncio
async def test_forbidden_sensitive_data_memory_rejection(db_session):
    """
    Verify privacy filter rejects storing passwords, PINs, and credit card credentials.
    """
    with pytest.raises(ValueError) as exc:
        await memory_service.save_memory(
            db=db_session,
            content="My banking password is secure1234",
            category="fact"
        )
    assert "Privacy policy violation" in str(exc.value)

@pytest.mark.asyncio
async def test_scheduled_reminders_survive_restart(db_session):
    """
    CRITICAL POLICY 8:
    Scheduled reminders persist in database and reload cleanly on server restart.
    """
    # 1. Create reminder scheduled for future
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    reminder = await scheduler_service.create_reminder(
        db=db_session,
        title="Check Arc Reactor Core",
        due_at=future_time
    )
    assert reminder.id is not None
    assert reminder.status == "scheduled"

    # 2. Simulate server restart by reloading pending reminders
    from tests.conftest import TestSessionLocal
    await scheduler_service.reload_pending_reminders(session_factory=TestSessionLocal)

    # 3. Verify reminder is present in APScheduler jobs
    job = scheduler_service.scheduler.get_job(f"reminder_{reminder.id}")
    assert job is not None

@pytest.mark.asyncio
async def test_missing_credentials_fails_honestly():
    """
    CRITICAL POLICY 9:
    Failed integrations / missing API credentials produce clear, honest errors (no fake success).
    """
    provider = OpenAIProvider(api_key="")
    assert provider.is_configured() is False
    with pytest.raises(RuntimeError) as exc:
        await provider.generate_response("test prompt")
    assert "OPENAI_API_KEY is missing" in str(exc.value)

@pytest.mark.asyncio
async def test_voice_verification_anti_replay_and_secondary_auth():
    """
    CRITICAL POLICY 10:
    Voice verification enforces anti-replay safeguards and requires secondary auth for high-risk actions.
    """
    # 1. Enroll speaker
    enroll_res = speaker_authenticator.enroll_speaker(
        speaker_name="Tony Stark",
        voice_sample_bytes=b"sample_audio_voice_print_12345"
    )
    assert enroll_res["status"] == "enrolled"

    # 2. Verify with valid nonce
    verify_res = speaker_authenticator.verify_voice(
        audio_bytes=b"sample_audio_voice_print_12345",
        action_type="general",
        nonce="nonce_unique_token_001"
    )
    assert verify_res["verified"] is True
    assert verify_res["anti_replay_passed"] is True

    # 3. Replay attack attempt with duplicate nonce
    replay_res = speaker_authenticator.verify_voice(
        audio_bytes=b"sample_audio_voice_print_12345",
        action_type="general",
        nonce="nonce_unique_token_001" # reused nonce
    )
    assert replay_res["verified"] is False
    assert replay_res["anti_replay_passed"] is False
    assert "Replay attack detected" in replay_res["error"]

    # 4. Sensitive action requires secondary authentication
    financial_res = speaker_authenticator.verify_voice(
        audio_bytes=b"sample_audio_voice_print_12345",
        action_type="financial",
        nonce="nonce_unique_token_002"
    )
    assert financial_res["requires_secondary_auth"] is True

@pytest.mark.asyncio
async def test_voice_verification_acoustic_mismatch_rejected():
    """
    CRITICAL POLICY 10 (Part 2):
    Mismatched speaker acoustic features are rejected even with unique valid nonces.
    """
    # Enrolled speaker profile
    speaker_authenticator.enroll_speaker(
        speaker_name="Tony Stark",
        voice_sample_bytes=b"low_frequency_deep_voice_sample_profile_111"
    )
    # Imposter sample with completely different acoustic byte distribution
    imposter_sample = bytes([i % 256 for i in range(500)])
    verify_res = speaker_authenticator.verify_voice(
        audio_bytes=imposter_sample,
        action_type="general",
        nonce="nonce_imposter_001"
    )
    assert verify_res["verified"] is False
    assert verify_res["confidence"] < 0.85

@pytest.mark.asyncio
async def test_running_tasks_cancelled_on_emergency_trigger():
    """
    CRITICAL POLICY 5 (Part 2):
    Verify currently running and queued tasks are immediately cancelled upon emergency trigger.
    """
    # 1. Start a long simulated task
    task = await task_engine.create_and_enqueue_task(
        task_type="summarize_text",
        title="Background Processing Job",
        payload={"content": "Detailed long telemetry dataset analysis."}
    )
    assert task["id"] is not None

    # 2. Trigger emergency stop immediately
    await emergency_controller.trigger(triggered_by="safety_system", reason="Critical breach test")

    # 3. Verify task is cancelled
    cancelled_task = task_engine.get_task(task["id"])
    assert cancelled_task["status"] == "cancelled"
    assert "Execution halted:" in cancelled_task["error"] or "Emergency stop" in cancelled_task["error"]

    # Reset
    await emergency_controller.reset(reset_by="test_cleanup")

@pytest.mark.asyncio
async def test_device_registration_and_auth(client):
    """
    Verify device registration returns unique key once and device is listed.
    """
    reg_res = await client.post("/api/v1/devices/register", json={
        "device_name": "Lab Windows Workstation",
        "platform": "windows",
        "capabilities": ["open_app", "system_telemetry"]
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert "api_key" in data
    assert data["platform"] == "windows"
    assert data["is_active"] is True

    # List devices
    list_res = await client.get("/api/v1/devices")
    assert list_res.status_code == 200
    devices = list_res.json()
    assert any(d["device_name"] == "Lab Windows Workstation" for d in devices)

@pytest.mark.asyncio
async def test_phone_call_ambiguity_and_direct_dial(client, db_session):
    """
    Verify phone call resolution handles ambiguous matches and direct dials correctly.
    """
    # 1. Add two contacts with similar names
    c1 = ContactModel(name="Peter Parker", phone_number="+919111111111", is_saved=True)
    c2 = ContactModel(name="Peter Quill", phone_number="+919222222222", is_saved=True)
    db_session.add_all([c1, c2])
    await db_session.commit()

    # 2. Ambiguous query
    ambig_res = await client.post("/api/v1/calls/initiate", json={
        "contact_name_or_number": "Peter",
        "purpose": "Mission briefing"
    })
    assert ambig_res.status_code == 400
    detail = ambig_res.json()["detail"]
    assert "Found 2 contacts" in detail["message"]
    assert len(detail["candidates"]) == 2

    # 3. Direct number dialing
    direct_res = await client.post("/api/v1/calls/initiate", json={
        "contact_name_or_number": "+919876500000",
        "purpose": "Direct emergency channel"
    })
    assert direct_res.status_code == 200
    call_data = direct_res.json()
    assert call_data["status"] == "awaiting_device_confirmation"
    assert call_data["target"] == "+919876500000"

@pytest.mark.asyncio
async def test_reminder_crud_lifecycle(client):
    """
    Verify full reminder creation, listing, and cancellation API flow.
    """
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    # Create reminder
    create_res = await client.post("/api/v1/reminders", json={
        "title": "Calibrate Mark 85 repulsors",
        "due_at": future_time,
        "description": "Routine diagnostics"
    })
    assert create_res.status_code == 200
    rem = create_res.json()
    rem_id = rem["id"]
    assert rem["status"] == "scheduled"

    # List reminders
    list_res = await client.get("/api/v1/reminders?status=scheduled")
    assert list_res.status_code == 200
    assert any(r["id"] == rem_id for r in list_res.json())

    # Cancel reminder
    cancel_res = await client.delete(f"/api/v1/reminders/{rem_id}")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

@pytest.mark.asyncio
async def test_natural_language_command_orchestration(client):
    """
    Verify natural language command submission decomposes intent and executes workflow.
    """
    response = await client.post("/api/v1/commands", json={
        "command": "Hey Friday, check the weather in Tokyo",
        "client_platform": "web"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["intent"] == "weather_query"
    assert data["intent"]["entities"]["location"] == "Tokyo"
    assert len(data["tasks_spawned"]) >= 1
    assert "Atmospheric telemetry" in data["response_text"]

@pytest.mark.asyncio
async def test_voice_api_enroll_and_verify_endpoints(client):
    """
    Verify voice enrollment and verification via REST API.
    """
    import base64
    sample_b64 = base64.b64encode(b"voice_profile_sample_tony_999").decode()
    
    # Enroll
    enroll_res = await client.post("/api/v1/voice/enroll", json={
        "speaker_name": "Tony Stark",
        "audio_sample_base64": sample_b64
    })
    assert enroll_res.status_code == 200
    assert enroll_res.json()["status"] == "enrolled"

    # Verify with matching sample
    verify_res = await client.post("/api/v1/voice/verify", json={
        "audio_sample_base64": sample_b64,
        "action_type": "general",
        "nonce": "api_nonce_001"
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["verified"] is True
    assert verify_res.json()["anti_replay_passed"] is True

    # Replay attack attempt with same nonce
    replay_res = await client.post("/api/v1/voice/verify", json={
        "audio_sample_base64": sample_b64,
        "action_type": "general",
        "nonce": "api_nonce_001"
    })
    assert replay_res.status_code == 200
    assert replay_res.json()["verified"] is False
    assert replay_res.json()["anti_replay_passed"] is False

@pytest.mark.asyncio
async def test_task_batch_and_cancel_api(client):
    """
    Verify task batch creation and cancellation via REST API.
    """
    batch_res = await client.post("/api/v1/tasks/batch", json={
        "tasks": [
            {"type": "weather", "title": "Atmospheric Check Tokyo"},
            {"type": "system_info", "title": "Diagnostic Telemetry"}
        ]
    })
    assert batch_res.status_code == 200
    spawned = batch_res.json()
    assert len(spawned) == 2
    task_id = spawned[0]["id"]

    # Cancel task
    cancel_res = await client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] in ["cancelled", "completed"]

@pytest.mark.asyncio
async def test_memory_export_api(client, db_session):
    """
    Verify full memory export endpoint.
    """
    await memory_service.save_memory(
        db=db_session,
        content="Flight stabilizer pitch is tuned to 14.2 degrees",
        category="fact",
        user_id="default_user"
    )
    res = await client.get("/api/v1/memory/export")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any("Flight stabilizer" in m["content"] for m in data)

@pytest.mark.asyncio
async def test_windows_and_android_agent_services():
    """
    Verify Windows and Android agent protocol services.
    """
    from app.agents.windows_agent import windows_agent_service
    from app.agents.android_agent import android_agent_service

    # Windows agent
    win_client = windows_agent_service.register_client("win_pc_01", "Lab Desktop")
    assert win_client["status"] == "online"
    assert windows_agent_service.record_heartbeat("win_pc_01") is True
    assert windows_agent_service.get_status("win_pc_01")["status"] == "online"

    # Android agent
    droid_dev = android_agent_service.register_device("droid_01", "Galaxy S24")
    assert droid_dev["status"] == "online"
    intent = android_agent_service.queue_call_intent("call_99", "Pepper Potts", "+919876543211")
    assert intent["status"] == "pending_device_ack"
    ack = android_agent_service.acknowledge_call_intent("call_99", "initiated")
    assert ack["status"] == "initiated"

@pytest.mark.asyncio
async def test_emergency_stop_toggle_api(client):
    """
    Verify emergency stop API toggle and status endpoint.
    """
    # Trigger emergency stop
    res = await client.post("/api/v1/emergency/toggle", json={
        "activate": True,
        "reason": "Test Emergency API"
    })
    assert res.status_code == 200
    assert res.json()["emergency_stop_active"] is True

    # Status
    status_res = await client.get("/api/v1/emergency/status")
    assert status_res.status_code == 200
    assert status_res.json()["emergency_stop_active"] is True

    # Reset
    reset_res = await client.post("/api/v1/emergency/toggle", json={
        "activate": False
    })
    assert reset_res.status_code == 200
    assert reset_res.json()["emergency_stop_active"] is False

def test_websocket_tasks_channel():
    """
    Verify live WebSocket tasks channel snapshot and ping-pong loop.
    """
    from starlette.testclient import TestClient
    from app.main import app
    with TestClient(app) as test_client:
        with test_client.websocket_connect("/ws/tasks") as websocket:
            data = websocket.receive_json()
            assert data["event_type"] == "initial_snapshot"
            assert "tasks" in data
            # Send ping
            websocket.send_json({"action": "ping"})
            pong = websocket.receive_json()
            assert pong["event_type"] == "pong"
