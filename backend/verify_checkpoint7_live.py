"""Live verification script for Checkpoint 7: Artifact Generation and Security."""
import asyncio
import sys
import os
import json
import uuid

os.environ["DATABASE_URL"] = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth"
os.environ["MODEL_TIMEOUT_SECONDS"] = "180"

sys.path.insert(0, ".")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.session import Session
from app.models.message import Message
from app.models.artifact import Artifact
from app.config import settings
settings.model_timeout_seconds = 180.0
from app.services.agent_service import process_chat_message
from app.services.llm_provider import OllamaProvider

engine = create_engine("postgresql://postgres:postgrespassword@localhost:5432/lenny_growth")
SessionLocal = sessionmaker(bind=engine)


async def verify_answerable_artifact():
    print("\n========================================================")
    print("1. LIVE ARTIFACT GENERATION (ANSWERABLE QUERY)")
    print("========================================================")
    db = SessionLocal()
    try:
        sess = Session(title="Live Artifact Verification - Balfour")
        db.add(sess)
        db.commit()
        db.refresh(sess)

        provider = OllamaProvider()
        tokens = []
        done_data = None
        error_data = None

        query = "What does Brian Balfour say about product market fit? Create an HTML artifact visual summary of this framework."
        print(f"Submitting query: {query}")
        print("Generating with Ollama streaming (this may take 30-90 seconds)...")


        async for ev in process_chat_message(
            db=db,
            session_id=sess.id,
            user_content=query,
            provider=provider,
            relevance_threshold=0.35,
        ):
            lines = ev.strip().split("\n")
            ev_type = None
            for line in lines:
                if line.startswith("event: "):
                    ev_type = line[7:].strip()
                elif line.startswith("data: ") and ev_type:
                    data = json.loads(line[6:])
                    if ev_type == "token":
                        tokens.append(data.get("delta", ""))
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    elif ev_type == "done":
                        done_data = data
                    elif ev_type == "error":
                        error_data = data

        print("\nStreaming finished.")
        print(f"done_data: {done_data}")
        print(f"Tokens received ({len(tokens)}): {''.join(tokens)}")
        assert error_data is None, f"Unexpected error event: {error_data}"
        assert done_data is not None, "No done event received"
        assert done_data.get("status") == "completed", f"Status not completed: {done_data}"
        assert done_data.get("skill") == "artifact", f"Skill not artifact: {done_data.get('skill')}"
        assert done_data.get("content_type") == "html", f"Content type not html: {done_data.get('content_type')}"

        artifact = done_data.get("artifact")
        assert artifact is not None, "No artifact returned in done event"

        assert artifact.get("title"), "Artifact missing title"
        assert artifact.get("type") == "html", f"Artifact type != html: {artifact.get('type')}"
        assert len(artifact.get("content", "")) > 50, "Artifact content is too short"

        citations = done_data.get("citations", [])
        assert len(citations) > 0, "No citations returned for answerable query"

        # Check PostgreSQL persistence
        db_artifact = db.query(Artifact).filter(Artifact.session_id == sess.id).first()
        assert db_artifact is not None, "Artifact was not persisted to PostgreSQL"
        assert db_artifact.title == artifact["title"]

        db_msg = db.query(Message).filter(Message.id == uuid.UUID(done_data["message_id"])).first()
        assert db_msg is not None, "Assistant message was not persisted"
        assert db_msg.message_metadata.get("artifact") is not None

        print("\n--- Artifact Generation Results ---")
        print(f"Skill routed:        {done_data.get('skill')}")
        print(f"Content type:        {done_data.get('content_type')}")
        print(f"Artifact ID:         {artifact.get('id')}")
        print(f"Artifact Title:      {artifact.get('title')}")
        print(f"Artifact Type:       {artifact.get('type')}")
        print(f"Content Length:      {len(artifact.get('content'))} characters")
        print(f"Citations count:     {len(citations)}")
        for c in citations:
            print(f"  - {c.get('guest_name')} | {c.get('episode_title')} (dist: {c.get('distance')})")

        print(f"DB Artifact ID:      {db_artifact.id}")
        print(f"DB Message ID:       {db_msg.id}")
        print("PASS: Live artifact generation verified successfully.")
        return True
    finally:
        db.close()


async def verify_unsupported_refusal():
    print("\n========================================================")
    print("2. LIVE ARTIFACT GROUNDED REFUSAL (OUT-OF-CORPUS QUERY)")
    print("========================================================")
    db = SessionLocal()
    try:
        sess = Session(title="Live Artifact Refusal Verification")
        db.add(sess)
        db.commit()
        db.refresh(sess)

        provider = OllamaProvider()
        tokens = []
        done_data = None
        error_data = None

        query = "Create an HTML artifact showing quantum chromodynamics in string theory"
        print(f"Submitting query: {query}")

        async for ev in process_chat_message(
            db=db,
            session_id=sess.id,
            user_content=query,
            provider=provider,
            relevance_threshold=0.35,
        ):
            lines = ev.strip().split("\n")
            ev_type = None
            for line in lines:
                if line.startswith("event: "):
                    ev_type = line[7:].strip()
                elif line.startswith("data: ") and ev_type:
                    data = json.loads(line[6:])
                    if ev_type == "token":
                        tokens.append(data.get("delta", ""))
                    elif ev_type == "done":
                        done_data = data
                    elif ev_type == "error":
                        error_data = data

        assert error_data is None, f"Unexpected error event: {error_data}"
        assert done_data is not None, "No done event received"
        assert done_data.get("status") == "completed", f"Status not completed: {done_data}"
        assert done_data.get("citations") == [], "Citations should be empty on refusal"
        assert done_data.get("artifact") is None, "Artifact should be None on refusal"

        full_refusal = "".join(tokens)
        assert "couldn't find" in full_refusal.lower(), f"Refusal text unexpected: {full_refusal}"

        # Verify DB persistence of refusal message
        assistant_msg = db.query(Message).filter(
            Message.session_id == sess.id,
            Message.role == "assistant",
        ).first()
        assert assistant_msg is not None
        assert "couldn't find" in assistant_msg.content.lower()
        assert assistant_msg.message_metadata.get("citations") == []

        # Verify 0 artifacts created in DB for this session
        art_count = db.query(Artifact).filter(Artifact.session_id == sess.id).count()
        assert art_count == 0, f"Expected 0 artifacts, found {art_count}"

        print("\n--- Grounded Refusal Results ---")
        print(f"Status:              {done_data.get('status')}")
        print(f"Refusal message:     {full_refusal}")
        print(f"Citations count:     {len(done_data.get('citations', []))}")
        print(f"Artifact in done:    {done_data.get('artifact')}")
        print(f"DB Artifacts count:  {art_count}")
        print("PASS: Live grounded refusal verified successfully (done event, 0 errors).")
        return True
    finally:
        db.close()


def verify_security_contract():
    print("\n========================================================")
    print("3. SECURITY CONTRACT VERIFICATION")
    print("========================================================")
    # Check that in ArtifactViewer.tsx:
    # 1. The iframe uses sandbox="allow-same-origin"
    # 2. The sandbox attribute value itself NEVER includes "allow-scripts"
    # 3. dangerouslySetInnerHTML is absent
    #
    # NOTE: "allow-scripts" may legitimately appear inside JSX comments that explicitly
    # prohibit it (e.g. "NEVER include allow-scripts"). We therefore check only the
    # actual sandbox attribute value, not the raw file text.
    import re

    viewer_path = os.path.join("..", "frontend", "src", "components", "ArtifactViewer.tsx")
    with open(viewer_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify sandbox="allow-same-origin" is present
    assert 'sandbox="allow-same-origin"' in content, "iframe must have sandbox='allow-same-origin'"

    # Extract the actual sandbox attribute values and verify none include allow-scripts
    sandbox_values = re.findall(r'sandbox=[\"\']([^\"\']*)[\"\'"]', content)
    for val in sandbox_values:
        assert "allow-scripts" not in val, (
            f"SECURITY VIOLATION: sandbox attribute contains 'allow-scripts': sandbox=\"{val}\""
        )

    # No dangerouslySetInnerHTML allowed
    assert "dangerouslySetInnerHTML" not in content, "SECURITY VIOLATION: dangerouslySetInnerHTML found!"

    print("Sandbox attribute:   sandbox='allow-same-origin' (VERIFIED)")
    print(f"Sandbox values found: {sandbox_values}")
    print("allow-scripts in sandbox values: STRICTLY ABSENT (VERIFIED)")
    print("dangerouslySetInnerHTML:         ABSENT (VERIFIED)")
    print("Security boundary:   Browser iframe sandbox isolates parent React DOM from any malicious scripts.")
    print("PASS: Security contract verified.")
    return True


async def main():
    print("================================================================")
    print("CHECKPOINT 7: REAL LIVE VERIFICATION (OLLAMA + POSTGRESQL)")
    print("================================================================")
    ok1 = await verify_answerable_artifact()
    ok2 = await verify_unsupported_refusal()
    ok3 = verify_security_contract()

    if ok1 and ok2 and ok3:
        print("\n================================================================")
        print("ALL CHECKPOINT 7 LIVE VERIFICATIONS PASSED SUCCESSFULLY!")
        print("================================================================")
    else:
        print("\nFAILURES OCCURRED IN LIVE VERIFICATION.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
