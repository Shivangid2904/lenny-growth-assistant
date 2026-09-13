import asyncio
import json
import time
from app.db.session import SessionLocal
from app.models.session import Session as DbSessionModel
from app.models.message import Message
from app.services.agent_service import process_chat_message
from app.services.llm_provider import OllamaProvider
from app.services.retrieval_service import search_transcript_chunks
from app.config import settings


def parse_sse(events_raw):
    tokens = []
    done_payload = None
    error_payload = None
    combined = "".join(events_raw)
    for line in combined.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if "delta" in d:
                    tokens.append(d["delta"])
                elif "message_id" in d:
                    done_payload = d
                elif "code" in d:
                    error_payload = d
            except json.JSONDecodeError:
                pass
    return "".join(tokens), done_payload, error_payload



async def run_verifications():
    db = SessionLocal()
    ollama_provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2:latest")

    print("================================================================================")
    print("VERIFICATION 1: GROUNDED QUERY WITH OLLAMA REASONING")
    print("================================================================================")
    sess1 = DbSessionModel(title="PMF & Retention Session")
    db.add(sess1)
    db.commit()
    db.refresh(sess1)

    query1 = "How do you know if you have product-market fit using cohort retention curves?"
    print(f"User Query: {query1}")
    print(f"Session ID: {sess1.id}")

    # Inspect raw retrieval first
    raw_chunks = search_transcript_chunks(db, query=query1, top_k=5)
    print(f"Retrieved {len(raw_chunks)} chunks:")
    for c in raw_chunks:
        print(f"  - Distance: {c['distance']:.4f} | Title: {c['episode_title']} | Chunk: {c['chunk_index']}")

    events1 = []
    t0 = time.time()
    # Use threshold 0.35 (configured placeholder) or 0.45 for fixture testing
    async for ev in process_chat_message(
        db=db,
        session_id=sess1.id,
        user_content=query1,
        provider=ollama_provider,
        relevance_threshold=0.45,
    ):
        events1.append(ev)
    elapsed1 = time.time() - t0

    full_text1, done1, err1 = parse_sse(events1)
    print(f"\nResponse Time: {elapsed1:.2f}s")
    if err1:
        print(f"ERROR: {err1}")
    else:
        print(f"Assistant Answer:\n{full_text1}")
        print(f"\nDone Payload: {json.dumps(done1, indent=2)}")

    print("\n================================================================================")
    print("VERIFICATION 2: UNSUPPORTED QUERY (NO MODEL INVOCATION)")
    print("================================================================================")
    sess2 = DbSessionModel(title="Unsupported Query Session")
    db.add(sess2)
    db.commit()
    db.refresh(sess2)

    query2 = "What is the best recipe for baking chocolate chip cookies on Mars?"
    print(f"User Query: {query2}")

    raw_chunks2 = search_transcript_chunks(db, query=query2, top_k=5)
    print(f"Retrieved {len(raw_chunks2)} chunks:")
    for c in raw_chunks2:
        print(f"  - Distance: {c['distance']:.4f} | Title: {c['episode_title']}")

    events2 = []
    t0 = time.time()
    async for ev in process_chat_message(
        db=db,
        session_id=sess2.id,
        user_content=query2,
        provider=ollama_provider,
        relevance_threshold=0.35,
    ):
        events2.append(ev)
    elapsed2 = time.time() - t0

    full_text2, done2, err2 = parse_sse(events2)
    print(f"\nResponse Time: {elapsed2:.2f}s")
    print(f"Assistant Answer:\n{full_text2}")
    print(f"Done Payload: {json.dumps(done2, indent=2)}")

    print("\n================================================================================")
    print("VERIFICATION 3: FOLLOW-UP TWO-TURN CONVERSATION IN SAME SESSION")
    print("================================================================================")
    sess3 = DbSessionModel(title="Two-Turn Follow-up Session")
    db.add(sess3)
    db.commit()
    db.refresh(sess3)

    # Turn 1
    t1_query = "What did Brian Balfour say about retention?"
    print(f"Turn 1 Query: {t1_query}")
    events_t1 = []
    async for ev in process_chat_message(
        db=db,
        session_id=sess3.id,
        user_content=t1_query,
        provider=ollama_provider,
        relevance_threshold=0.45,
    ):
        events_t1.append(ev)
    t1_text, done_t1, _ = parse_sse(events_t1)
    print(f"Turn 1 Answer:\n{t1_text[:200]}...")
    print(f"Turn 1 Citations: {json.dumps(done_t1.get('citations', []) if done_t1 else [], indent=2)}")

    # Turn 2 (Follow-up grounded question in same session)
    t2_query = "What does Elena Verna say about product-led growth and sales in B2B?"
    print(f"\nTurn 2 Follow-up Query: {t2_query}")
    events_t2 = []
    async for ev in process_chat_message(
        db=db,
        session_id=sess3.id,
        user_content=t2_query,
        provider=ollama_provider,
        relevance_threshold=0.45,
    ):
        events_t2.append(ev)
    t2_text, done_t2, _ = parse_sse(events_t2)
    print(f"Turn 2 Answer:\n{t2_text[:200]}...")
    print(f"Turn 2 Citations: {json.dumps(done_t2.get('citations', []) if done_t2 else [], indent=2)}")

    # Check total messages in sess3
    sess3_messages = db.query(Message).filter(Message.session_id == sess3.id).order_by(Message.created_at.asc()).all()
    print(f"\nTotal persisted messages in Turn 2 session: {len(sess3_messages)}")
    for m in sess3_messages:
        print(f"  [{m.role.upper()}]: {m.content[:80]}... (citations: {len(m.message_metadata.get('citations', []))})")

    db.close()


if __name__ == "__main__":
    asyncio.run(run_verifications())

