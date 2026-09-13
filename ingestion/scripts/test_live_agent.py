#!/usr/bin/env python3
"""
Live Agent Layer verification script for Checkpoint 4.

Tests end-to-end agent execution against the real PostgreSQL + pgvector corpus:
  1. Grounded answerable query (produces answer + citations)
  2. Unsupported query (0 eligible chunks -> grounded refusal, LLM not called)
  3. Mixed-relevance query (only eligible chunks cited)
  4. Follow-up query in same session (conversation history loaded and isolated)
  5. Live Ollama model provider verification (end-to-end streaming)
"""
import sys
import asyncio
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.session import SessionLocal
from app.models.session import Session
from app.models.message import Message
from app.services.agent_service import process_chat_message
from app.services.llm_provider import FakeLLMProvider, OllamaProvider
from app.config import settings


async def parse_sse_stream(generator):
    """Consume SSE stream and parse event dictionaries."""
    events = []
    full_text = ""
    current_event = "message"

    async for raw in generator:
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                payload = line[6:].strip()
                if payload == "[DONE]":
                    events.append({"event": "done_marker", "data": {}})
                    continue
                try:
                    data = json.loads(payload)
                    events.append({"event": current_event, "data": data})
                    if current_event == "token":
                        full_text += data.get("delta", "")
                except json.JSONDecodeError:
                    pass
    return events, full_text


async def run_tests():
    print("\n" + "=" * 70)
    print("CHECKPOINT 4 -- LIVE AGENT LAYER VERIFICATION")
    print("=" * 70)

    db = SessionLocal()
    try:
        # Create a test session
        test_session = Session(title="Checkpoint 4 Live Test Session")
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        session_id = test_session.id
        print(f"\n[INIT] Test session created: {session_id}")

        # -------------------------------------------------------------
        # Test 1: Grounded Answerable Query (with FakeLLMProvider spy)
        # -------------------------------------------------------------
        print("\n[TEST 1] Grounded Answerable Query")
        fake_llm = FakeLLMProvider(tokens=[
            "The Adjacent User Theory, developed by Bangaly Kaba, focuses on users who are aware of a product but struggle to become active."
        ])
        q1 = "What is the Adjacent User Theory and how should product teams use it?"
        events, full_text = await parse_sse_stream(
            process_chat_message(
                db=db,
                session_id=session_id,
                user_content=q1,
                provider=fake_llm,
            )
        )

        # Verify LLM was called
        assert fake_llm.invoked is True, "Expected LLM to be invoked for grounded query"
        assert len(fake_llm.invocations) == 1, f"Expected 1 LLM call, got {len(fake_llm.invocations)}"

        # Verify done event and citations
        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) == 1, "Expected 1 done event"
        done_data = done_events[0]["data"]
        citations = done_data.get("citations", [])
        assert len(citations) > 0, "Expected non-empty citations for grounded query"

        # Verify citations metadata
        for cit in citations:
            assert "episode_id" in cit
            assert "chunk_index" in cit
            assert cit["distance"] <= settings.rag_relevance_distance_threshold
            assert cit["episode_id"] == "bangaly-kaba"

        # Verify DB persistence
        assistant_msg = db.query(Message).filter(
            Message.session_id == session_id,
            Message.role == "assistant"
        ).order_by(Message.created_at.desc()).first()
        assert assistant_msg is not None
        assert "Adjacent User Theory" in assistant_msg.content
        assert len(assistant_msg.message_metadata.get("citations", [])) > 0
        print(f"  [PASS] Grounded query returned {len(citations)} citations from episode '{citations[0]['episode_id']}'")
        print(f"  [PASS] Assistant message persisted with citations: {len(assistant_msg.message_metadata['citations'])}")

        # -------------------------------------------------------------
        # Test 2: Unsupported Query (Grounded Refusal)
        # -------------------------------------------------------------
        print("\n[TEST 2] Unsupported Query (Out-of-Scope)")
        fake_llm2 = FakeLLMProvider(tokens=["This should never be reached!"])
        q2 = "What is the correct calorie intake for building muscle as an athlete?"
        events2, full_text2 = await parse_sse_stream(
            process_chat_message(
                db=db,
                session_id=session_id,
                user_content=q2,
                provider=fake_llm2,
            )
        )

        # Verify LLM was NOT called
        assert fake_llm2.invoked is False, f"LLM MUST NOT be called for unsupported query! Invoked: {fake_llm2.invoked}"
        done_events2 = [e for e in events2 if e["event"] == "done"]
        assert len(done_events2) == 1
        done_data2 = done_events2[0]["data"]
        assert done_data2.get("citations") == [], "Expected empty citations"
        assert "enough relevant material in" in full_text2
        print(f"  [PASS] LLM was NOT called (0 invocations)")
        print(f"  [PASS] Grounded refusal returned: '{full_text2.strip()}'")
        print(f"  [PASS] Citations list is strictly empty")

        # -------------------------------------------------------------
        # Test 3: Mixed-Relevance Query
        # -------------------------------------------------------------
        print("\n[TEST 3] Mixed-Relevance Query (Per-Chunk Distance Filtering)")
        fake_llm3 = FakeLLMProvider(tokens=["Pricing strategy connects directly to compounding growth loops."])
        q3 = "How does pricing strategy relate to growth loop design?"
        events3, full_text3 = await parse_sse_stream(
            process_chat_message(
                db=db,
                session_id=session_id,
                user_content=q3,
                provider=fake_llm3,
            )
        )
        done_events3 = [e for e in events3 if e["event"] == "done"]
        assert len(done_events3) == 1
        done_data3 = done_events3[0]["data"]
        for c in done_data3.get("citations", []):
            assert c["distance"] <= settings.rag_relevance_distance_threshold, f"Chunk distance {c['distance']} exceeds threshold!"
        print(f"  [PASS] All {len(done_data3.get('citations', []))} cited chunks have distance <= {settings.rag_relevance_distance_threshold}")

        # -------------------------------------------------------------
        # Test 4: Follow-up Query in Same Session Context
        # -------------------------------------------------------------
        print("\n[TEST 4] Follow-up Query (Session Context & Isolation)")
        fake_llm4 = FakeLLMProvider(tokens=["As mentioned regarding the Adjacent User Theory, Instagram used this to expand beyond power users."])
        q4 = "How did Instagram apply that theory?"
        events4, full_text4 = await parse_sse_stream(
            process_chat_message(
                db=db,
                session_id=session_id,
                user_content=q4,
                provider=fake_llm4,
            )
        )
        # Check that LLM received conversation history
        call_messages = fake_llm4.invocations[0]["messages"]
        assert len(call_messages) >= 4, f"Expected at least 4 previous messages in context, got {len(call_messages)}"
        print(f"  [PASS] LLM received {len(call_messages)} previous conversation messages in context")

        # Verify session isolation: create a different session and check its history is empty
        other_session = Session(title="Isolated Session")
        db.add(other_session)
        db.commit()
        db.refresh(other_session)
        from app.services.agent_service import get_conversation_history
        isolated_history = get_conversation_history(db=db, session_id=other_session.id)
        assert len(isolated_history) == 0, f"Expected isolated session history to be empty, got {len(isolated_history)}"
        print(f"  [PASS] Strict session isolation verified: other session has 0 messages")

        # -------------------------------------------------------------
        # Test 5: Live Ollama LLM Provider Verification
        # -------------------------------------------------------------
        print("\n[TEST 5] Live Ollama LLM Provider (End-to-End Local Inference)")
        ollama_provider = OllamaProvider(model=settings.ollama_model)
        live_session = Session(title="Live Ollama Test Session")
        db.add(live_session)
        db.commit()
        db.refresh(live_session)

        q_live = "What is the four fits framework by Brian Balfour?"
        print(f"  Query: {q_live}")
        print("  Generating response with local Ollama model...")
        events_live, full_text_live = await parse_sse_stream(
            process_chat_message(
                db=db,
                session_id=live_session.id,
                user_content=q_live,
                provider=ollama_provider,
            )
        )
        assert len(full_text_live.strip()) > 0, "Expected non-empty live Ollama response"
        done_live = [e for e in events_live if e["event"] == "done"][0]["data"]
        print(f"  [PASS] Live Ollama generated response ({len(full_text_live)} chars)")
        print(f"  [PASS] Live citations returned: {len(done_live.get('citations', []))}")
        print(f"  Response preview: {full_text_live[:150].strip()}...")

        print("\n" + "=" * 70)
        print("ALL 5 LIVE AGENT TESTS PASSED SUCCESSFULLY!")
        print("=" * 70 + "\n")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
