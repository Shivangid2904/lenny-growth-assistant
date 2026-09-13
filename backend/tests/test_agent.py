import json
import uuid
from unittest.mock import patch
import pytest

from app.config import settings
from app.models.session import Session
from app.models.message import Message
from app.models.transcript_chunk import TranscriptChunk
from app.services.agent_service import (
    process_chat_message,
    REFUSAL_MESSAGE,
    SYSTEM_INSTRUCTION,
    build_evidence_context,
    get_conversation_history,
)
from app.services.llm_provider import (
    AnthropicProvider,
    OllamaProvider,
    FakeLLMProvider,
    get_llm_provider,
)
from app.services.skill_router import skill_router, ChatSkill, Ship30SkillStub, ArtifactSkillStub
from app.exceptions import (
    ClaudeNotConfiguredError,
    OllamaUnavailableError,
    ModelTimeoutError,
    ModelUnavailableError,
)


def parse_sse_events(raw_text: str):
    """Helper to parse raw SSE text into a list of (event_type, json_data) tuples."""
    events = []
    lines = raw_text.strip().split("\n")
    current_event = None
    for line in lines:
        line = line.strip()
        if line.startswith("event: "):
            current_event = line.replace("event: ", "").strip()
        elif line.startswith("data: ") and current_event:
            data_str = line.replace("data: ", "").strip()
            try:
                data_json = json.loads(data_str)
                events.append((current_event, data_json))
            except json.JSONDecodeError:
                events.append((current_event, data_str))
            current_event = None
    return events


# -----------------------------------------------------------------------------
# 1. Relevance Gate & Individual Chunk Filtering Tests
# -----------------------------------------------------------------------------

def test_relevance_threshold_gate_semantics():
    """Verify distance <= threshold is eligible, distance > threshold is rejected."""
    threshold = settings.rag_relevance_distance_threshold
    assert threshold > 0.0, "Threshold should be configured"

    # distance < threshold -> eligible
    c_lower = {"distance": threshold - 0.05, "id": "1"}
    # distance == threshold -> eligible
    c_equal = {"distance": threshold, "id": "2"}
    # distance > threshold -> rejected
    c_higher = {"distance": threshold + 0.05, "id": "3"}

    chunks = [c_lower, c_equal, c_higher]
    eligible = [c for c in chunks if c["distance"] <= threshold]

    assert len(eligible) == 2
    assert eligible[0]["id"] == "1"
    assert eligible[1]["id"] == "2"
    assert all(c["id"] != "3" for c in eligible)


def test_individual_chunk_filtering_not_passing_all_on_top_match():
    """Verify each chunk is filtered individually and weaker chunks do NOT hitchhike."""
    mock_chunks = [
        {"distance": 0.20, "chunk_index": 0, "episode_title": "Ep 1", "metadata": {"guest": "Guest A"}},
        {"distance": 0.24, "chunk_index": 1, "episode_title": "Ep 1", "metadata": {"guest": "Guest A"}},
        {"distance": 0.40, "chunk_index": 0, "episode_title": "Ep 2", "metadata": {"guest": "Guest B"}},
        {"distance": 0.52, "chunk_index": 1, "episode_title": "Ep 2", "metadata": {"guest": "Guest B"}},
        {"distance": 0.60, "chunk_index": 0, "episode_title": "Ep 3", "metadata": {"guest": "Guest C"}},
    ]
    test_threshold = 0.30
    eligible = [c for c in mock_chunks if c["distance"] <= test_threshold]

    assert len(eligible) == 2
    assert eligible[0]["distance"] == 0.20
    assert eligible[1]["distance"] == 0.24
    # Ensure rejected chunks (0.40, 0.52, 0.60) are not present
    for rejected in mock_chunks[2:]:
        assert rejected not in eligible


# -----------------------------------------------------------------------------
# 2. Refusal and Zero-Model-Invocation Tests
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_no_eligible_evidence_refusal_and_zero_model_calls(db):
    """When no retrieved chunk passes the threshold, the model must NOT be called."""
    session = Session(title="Test Refusal Session")
    db.add(session)
    db.commit()
    db.refresh(session)

    fake_provider = FakeLLMProvider(tokens=["Should not be called"])

    # Mock search_transcript_chunks to return chunks with distance > threshold
    mock_irrelevant_chunks = [
        {"distance": 0.85, "chunk_index": 0, "episode_title": "Irrelevant Ep", "content": "Unrelated", "metadata": {}}
    ]

    with patch("app.services.agent_service.search_transcript_chunks", return_value=mock_irrelevant_chunks):
        events = []
        async for event_str in process_chat_message(
            db=db,
            session_id=session.id,
            user_content="How do I launch rockets to Mars?",
            provider=fake_provider,
            relevance_threshold=0.35,
        ):
            events.append(event_str)

    # 1. Reasoning provider was NEVER invoked
    assert fake_provider.invoked is False
    assert len(fake_provider.invocations) == 0

    # 2. Stream contains refusal tokens and done event
    combined_events = "".join(events)
    parsed = parse_sse_events(combined_events)
    token_texts = "".join([d["delta"] for ev, d in parsed if ev == "token"])
    assert REFUSAL_MESSAGE in token_texts

    done_events = [d for ev, d in parsed if ev == "done"]
    assert len(done_events) == 1
    assert done_events[0]["citations"] == []

    # 3. Assistant response was persisted to DB as completed refusal
    persisted_assistant_msg = (
        db.query(Message)
        .filter(Message.session_id == session.id, Message.role == "assistant")
        .first()
    )
    assert persisted_assistant_msg is not None
    assert persisted_assistant_msg.content == REFUSAL_MESSAGE
    assert persisted_assistant_msg.message_metadata.get("citations") == []


@pytest.mark.anyio
async def test_empty_corpus_refusal(db):
    """When corpus is empty (0 chunks found), return refusal without invoking model."""
    session = Session(title="Empty Corpus Session")
    db.add(session)
    db.commit()
    db.refresh(session)

    fake_provider = FakeLLMProvider()

    with patch("app.services.agent_service.search_transcript_chunks", return_value=[]):
        events = []
        async for event_str in process_chat_message(
            db=db,
            session_id=session.id,
            user_content="What is retention?",
            provider=fake_provider,
        ):
            events.append(event_str)

    assert fake_provider.invoked is False
    parsed = parse_sse_events("".join(events))
    token_texts = "".join([d["delta"] for ev, d in parsed if ev == "token"])
    assert REFUSAL_MESSAGE in token_texts


# -----------------------------------------------------------------------------
# 3. Grounded Context, Prompt-Injection Delimiters & Citations
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_grounded_answer_delimiting_and_citations(db):
    """Verify eligible evidence is delimited in <transcript_evidence> and structured citations are generated."""
    session = Session(title="Grounded Session")
    db.add(session)
    db.commit()
    db.refresh(session)

    eligible_chunk = {
        "id": str(uuid.uuid4()),
        "episode_id": "ep-retention",
        "episode_title": "Casey Winters on Retention",
        "chunk_index": 2,
        "content": "Cohort retention curves that flatten indicate product-market fit.",
        "distance": 0.18,
        "similarity": 0.82,
        "metadata": {
            "guest": "Casey Winters",
            "source_url": "https://lenny.com/casey-winters",
        },
    }

    fake_provider = FakeLLMProvider(tokens=["Retention curves ", "that flatten indicate PMF."])

    with patch("app.services.agent_service.search_transcript_chunks", return_value=[eligible_chunk]):
        events = []
        async for event_str in process_chat_message(
            db=db,
            session_id=session.id,
            user_content="How do retention curves indicate PMF?",
            provider=fake_provider,
            relevance_threshold=0.35,
        ):
            events.append(event_str)

    # Reasoning provider was invoked
    assert fake_provider.invoked is True
    call_args = fake_provider.invocations[0]

    # Verify system prompt has strict grounding instructions
    assert "STRICT GROUNDING POLICY" in call_args["system_prompt"]
    assert "PROMPT-INJECTION TRUST BOUNDARY" in call_args["system_prompt"]

    # Verify prompt contains <transcript_evidence> block
    prompt_content = call_args["messages"][-1]["content"]
    assert "<transcript_evidence>" in prompt_content
    assert "</transcript_evidence>" in prompt_content
    assert "Casey Winters on Retention" in prompt_content
    assert "Cohort retention curves that flatten" in prompt_content

    # Verify SSE done event contains structured citation metadata
    parsed = parse_sse_events("".join(events))
    done_event = [d for ev, d in parsed if ev == "done"][0]
    citations = done_event["citations"]
    assert len(citations) == 1
    assert citations[0]["episode_title"] == "Casey Winters on Retention"
    assert citations[0]["guest_name"] == "Casey Winters"
    assert citations[0]["source_url"] == "https://lenny.com/casey-winters"
    assert citations[0]["chunk_index"] == 2

    # Verify DB persistence of citations
    persisted_msg = (
        db.query(Message)
        .filter(Message.session_id == session.id, Message.role == "assistant")
        .first()
    )
    assert persisted_msg is not None
    assert persisted_msg.content == "Retention curves that flatten indicate PMF."
    assert persisted_msg.message_metadata["citations"] == citations


# -----------------------------------------------------------------------------
# 4. Session Isolation & Conversation Context Limit
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_session_isolation(db):
    """Verify session A never receives conversation history from session B."""
    session_a = Session(title="Session A")
    session_b = Session(title="Session B")
    db.add_all([session_a, session_b])
    db.commit()

    # Add messages to Session A
    msg_a1 = Message(session_id=session_a.id, role="user", content="Secret A query", message_metadata={})
    msg_a2 = Message(session_id=session_a.id, role="assistant", content="Secret A answer", message_metadata={})
    # Add messages to Session B
    msg_b1 = Message(session_id=session_b.id, role="user", content="Public B query", message_metadata={})
    msg_b2 = Message(session_id=session_b.id, role="assistant", content="Public B answer", message_metadata={})
    db.add_all([msg_a1, msg_a2, msg_b1, msg_b2])
    db.commit()

    fake_provider = FakeLLMProvider()
    mock_chunk = {
        "episode_id": "ep1",
        "episode_title": "Ep 1",
        "chunk_index": 0,
        "content": "Content",
        "distance": 0.15,
        "metadata": {"guest": "G1", "source_url": "url"},
    }

    with patch("app.services.agent_service.search_transcript_chunks", return_value=[mock_chunk]):
        async for _ in process_chat_message(
            db=db,
            session_id=session_b.id,
            user_content="New message in session B",
            provider=fake_provider,
        ):
            pass

    assert fake_provider.invoked is True
    invoked_messages = fake_provider.invocations[0]["messages"]

    # Must contain Session B previous messages
    contents = [m["content"] for m in invoked_messages]
    assert "Public B query" in contents
    assert "Public B answer" in contents

    # Must NOT contain any Session A messages
    assert "Secret A query" not in contents
    assert "Secret A answer" not in contents


@pytest.mark.anyio
async def test_conversation_history_limit_window(db):
    """Verify only the most recent 10 messages from the session are passed into context."""
    session = Session(title="History Window Session")
    db.add(session)
    db.commit()

    from datetime import datetime, timedelta, timezone
    base_time = datetime.now(timezone.utc)

    # Add 14 messages (7 user/assistant turns) with distinct timestamps
    for i in range(14):
        role = "user" if i % 2 == 0 else "assistant"
        db.add(Message(
            session_id=session.id,
            role=role,
            content=f"Message {i}",
            message_metadata={},
            created_at=base_time + timedelta(seconds=i),
        ))
    db.commit()


    fake_provider = FakeLLMProvider()
    mock_chunk = {
        "episode_id": "ep1",
        "episode_title": "Ep 1",
        "chunk_index": 0,
        "content": "Content",
        "distance": 0.10,
        "metadata": {"guest": "G1", "source_url": "url"},
    }

    with patch("app.services.agent_service.search_transcript_chunks", return_value=[mock_chunk]):
        async for _ in process_chat_message(
            db=db,
            session_id=session.id,
            user_content="Follow up turn 8",
            provider=fake_provider,
            history_limit=10,
        ):
            pass

    assert fake_provider.invoked is True
    invoked_messages = fake_provider.invocations[0]["messages"]
    # 10 history messages + 1 current prompt = 11 messages total
    assert len(invoked_messages) == 11
    # Oldest messages (Message 0, 1, 2, 3) must NOT be present
    history_contents = [m["content"] for m in invoked_messages[:-1]]
    assert "Message 0" not in history_contents
    assert "Message 1" not in history_contents
    assert "Message 2" not in history_contents
    assert "Message 3" not in history_contents
    # Recent messages (Message 4 to 13) MUST be present in order
    assert "Message 4" in history_contents
    assert "Message 13" in history_contents


# -----------------------------------------------------------------------------
# 5. Model Provider Abstraction & Error Handling Tests
# -----------------------------------------------------------------------------

def test_provider_factory_selection():
    """Verify get_llm_provider respects configuration and explicit arguments."""
    with patch("app.config.settings.llm_provider", "anthropic"):
        p1 = get_llm_provider()
        assert isinstance(p1, AnthropicProvider)

    with patch("app.config.settings.llm_provider", "ollama"):
        p2 = get_llm_provider()
        assert isinstance(p2, OllamaProvider)

    p3 = get_llm_provider("fake")
    assert isinstance(p3, FakeLLMProvider)

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm_provider("invalid_cloud_provider")


@pytest.mark.anyio
async def test_anthropic_missing_key_structured_error():
    """When Anthropic API key is missing, raise structured ClaudeNotConfiguredError."""
    provider = AnthropicProvider(api_key="", model="claude-3-5-sonnet")
    with pytest.raises(ClaudeNotConfiguredError) as exc_info:
        async for _ in provider.stream_chat(system_prompt="sys", messages=[{"role": "user", "content": "hi"}]):
            pass
    assert exc_info.value.code == "CLAUDE_NOT_CONFIGURED"


@pytest.mark.anyio
async def test_ollama_unavailable_structured_error():
    """When Ollama port is unreachable, raise structured OllamaUnavailableError."""
    # Point to an unused local port
    provider = OllamaProvider(base_url="http://localhost:59999", model="llama3.2:latest")
    with pytest.raises(OllamaUnavailableError) as exc_info:
        async for _ in provider.stream_chat(system_prompt="sys", messages=[{"role": "user", "content": "hi"}], timeout=1.0):
            pass
    assert exc_info.value.code == "OLLAMA_UNAVAILABLE"


@pytest.mark.anyio
async def test_provider_timeout_handling(db):
    """When reasoning model generation exceeds timeout, emit structured MODEL_TIMEOUT error."""
    session = Session(title="Timeout Session")
    db.add(session)
    db.commit()

    mock_chunk = {
        "episode_id": "ep1",
        "episode_title": "Ep 1",
        "chunk_index": 0,
        "content": "Content",
        "distance": 0.10,
        "metadata": {},
    }

    # Fake provider configured to raise ModelTimeoutError
    timing_out_provider = FakeLLMProvider(
        error_to_raise=ModelTimeoutError("Generation timed out.")
    )

    with patch("app.services.agent_service.search_transcript_chunks", return_value=[mock_chunk]):
        events = []
        async for ev in process_chat_message(
            db=db,
            session_id=session.id,
            user_content="Test query",
            provider=timing_out_provider,
        ):
            events.append(ev)

    parsed = parse_sse_events("".join(events))
    error_events = [d for ev, d in parsed if ev == "error"]
    assert len(error_events) == 1
    assert error_events[0]["code"] == "MODEL_TIMEOUT"

    # Incomplete generation must NOT persist an assistant message
    msg = db.query(Message).filter(Message.session_id == session.id, Message.role == "assistant").first()
    assert msg is None


# -----------------------------------------------------------------------------
# 6. SSE Endpoint HTTP Tests
# -----------------------------------------------------------------------------

def test_messages_endpoint_session_not_found(client):
    """Verify sending a message to a non-existent session returns 404 SESSION_NOT_FOUND."""
    random_id = uuid.uuid4()
    response = client.post(
        f"/api/sessions/{random_id}/messages",
        json={"content": "Hello?"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "SESSION_NOT_FOUND"


def test_messages_endpoint_empty_content_validation_failed(client, db):
    """Verify sending empty or whitespace message returns 422 VALIDATION_FAILED."""
    session = Session(title="Val Session")
    db.add(session)
    db.commit()

    # Empty string
    res1 = client.post(f"/api/sessions/{session.id}/messages", json={"content": ""})
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "VALIDATION_FAILED"

    # Whitespace only
    res2 = client.post(f"/api/sessions/{session.id}/messages", json={"content": "   \n  "})
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "VALIDATION_FAILED"


def test_messages_endpoint_sse_streaming(client, db):
    """Verify POST /api/sessions/{session_id}/messages streams tokens and completes with done."""
    session = Session(title="Chat SSE Session")
    db.add(session)
    db.commit()

    fake_provider = FakeLLMProvider(tokens=["Retention ", "is ", "growth."])
    mock_chunk = {
        "episode_id": "ep-ret",
        "episode_title": "Retention Masterclass",
        "chunk_index": 1,
        "content": "Retention drives the compounding loop.",
        "distance": 0.15,
        "similarity": 0.85,
        "metadata": {"guest": "Elena Verna", "source_url": "https://example.com/elena"},
    }

    with patch("app.services.agent_service.get_llm_provider", return_value=fake_provider):
        with patch("app.services.agent_service.search_transcript_chunks", return_value=[mock_chunk]):
            response = client.post(
                f"/api/sessions/{session.id}/messages",
                json={"content": "How does retention drive growth?"},
            )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = parse_sse_events(response.text)
    token_events = [d for ev, d in events if ev == "token"]
    assert len(token_events) == 3
    assert token_events[0]["delta"] == "Retention "
    assert token_events[1]["delta"] == "is "
    assert token_events[2]["delta"] == "growth."

    done_events = [d for ev, d in events if ev == "done"]
    assert len(done_events) == 1
    assert done_events[0]["status"] == "completed"
    assert len(done_events[0]["citations"]) == 1
    assert done_events[0]["citations"][0]["guest_name"] == "Elena Verna"


# -----------------------------------------------------------------------------
# 7. Skill Router Tests
# -----------------------------------------------------------------------------

def test_skill_router_registration_and_routing():
    """Verify backend-authoritative skill registry and routing rules."""
    skills = skill_router.list_skills()
    skill_names = [s["name"] for s in skills]
    assert "chat" in skill_names
    assert "ship30" in skill_names
    assert "artifact" in skill_names

    # Default routing returns chat
    s1 = skill_router.route("Explain product market fit")
    assert s1.name == "chat"
    assert isinstance(s1, ChatSkill)

    # Inferred routing detects Ship 30 intent
    s2 = skill_router.route("Write an atomic essay using Ship 30 style")
    assert s2.name == "ship30"
    assert isinstance(s2, Ship30SkillStub)

    # Explicit routing works
    s3 = skill_router.route("Anything", explicit_skill="artifact")
    assert s3.name == "artifact"

    # Arbitrary functions cannot be invoked
    with pytest.raises(ValueError, match="Invalid skill"):
        skill_router.route("Anything", explicit_skill="__import__('os').system")
