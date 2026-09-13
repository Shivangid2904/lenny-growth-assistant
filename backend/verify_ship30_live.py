"""Live verification script for Ship30 essay generation."""
import asyncio
import sys
import os
import json

os.environ["DATABASE_URL"] = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth"
os.environ["MODEL_TIMEOUT_SECONDS"] = "300"

sys.path.insert(0, ".")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.session import Session
from app.config import settings
settings.model_timeout_seconds = 300.0
from app.services.agent_service import process_chat_message
from app.services.llm_provider import OllamaProvider

engine = create_engine("postgresql://postgres:postgrespassword@localhost:5432/lenny_growth")
SessionLocal = sessionmaker(bind=engine)

ESSAY_MIN = 1125
ESSAY_MAX = 1375


async def run_essay_test():
    db = SessionLocal()
    try:
        sess = Session(title="Ship30 Live Verification")
        db.add(sess)
        db.commit()
        db.refresh(sess)

        provider = OllamaProvider()
        tokens = []
        done_data = None

        print("Generating Ship30 essay with Ollama (this may take a few minutes)...")
        async for ev in process_chat_message(
            db=db,
            session_id=sess.id,
            user_content="Write a Ship 30 for 30 essay about the Four Fits framework and why startups fail to achieve product-market fit",
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
                        tokens.append(data["delta"])
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    elif ev_type == "done":
                        done_data = data
                    elif ev_type == "error":
                        print(f"\nERROR: {data}")
                        db.delete(sess)
                        db.commit()
                        return

        full_text = "".join(tokens)
        word_count = len(full_text.split())
        citations = done_data.get("citations", []) if done_data else []
        skill = done_data.get("skill", "unknown") if done_data else "unknown"
        ct = done_data.get("content_type", "unknown") if done_data else "unknown"

        print("\n\n=== LIVE VERIFICATION RESULT ===")
        print(f"Skill routed:               {skill}")
        print(f"Content type:               {ct}")
        print(f"Word count:                 {word_count}")
        in_range = ESSAY_MIN <= word_count <= ESSAY_MAX
        print(f"Within {ESSAY_MIN}-{ESSAY_MAX} range: {'PASS' if in_range else 'FAIL'}")
        print(f"Citations returned:          {len(citations)}")
        for c in citations:
            ep = c.get("episode_id", "?")
            guest = c.get("guest_name", "?")
            dist = c.get("distance", "?")
            print(f"  - {ep} | {guest} | dist={dist}")

        print("\nFirst 400 chars of essay:")
        print(full_text[:400])
        print("...")
        print("Last 200 chars:")
        print(full_text[-200:])

        try:
            with open("latest_essay.md", "w", encoding="utf-8") as f:
                f.write(full_text)
            print("\nSaved full essay to latest_essay.md")
        except Exception as e:
            print(f"\nCould not save latest_essay.md: {e}")

        db.delete(sess)
        db.commit()

    finally:
        db.close()


asyncio.run(run_essay_test())
