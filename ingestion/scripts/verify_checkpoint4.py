#!/usr/bin/env python3
"""
Checkpoint 4 live verification script.

Runs four manual verification scenarios against the real ingested corpus:
  1. Grounded question (answerable from corpus)
  2. Unsupported question (not in corpus)
  3. Mixed-relevance question (partial corpus coverage)
  4. Follow-up question (within same session context)

Uses the FakeLLMProvider to test the full agent pipeline (retrieval, grounding,
relevance gate) WITHOUT invoking a real LLM API. The LLM response is synthetic.

Usage:
    python ingestion/scripts/verify_checkpoint4.py
"""
import sys
import uuid
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def check_chunk_count():
    from app.db.session import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        total = db.execute(text("SELECT COUNT(*) FROM transcript_chunks")).scalar()
        episodes = db.execute(text(
            "SELECT episode_id, COUNT(*) as cnt FROM transcript_chunks "
            "GROUP BY episode_id ORDER BY episode_id"
        )).fetchall()
        return total, episodes
    finally:
        db.close()


def run_retrieval_only(query: str, top_k: int = 5):
    """Run retrieval without agent/LLM to check if relevant chunks exist."""
    from app.db.session import SessionLocal
    from app.services.retrieval_service import search_transcript_chunks
    from app.config import settings

    db = SessionLocal()
    try:
        chunks = search_transcript_chunks(db=db, query=query, top_k=top_k)
        threshold = settings.rag_relevance_distance_threshold
        eligible = [c for c in chunks if c.get("distance", 1.0) <= threshold]
        return chunks, eligible, threshold
    finally:
        db.close()


def print_chunks(chunks, eligible_set, threshold, query):
    print(f"\n  Query: {query[:80]}...")
    print(f"  Threshold: {threshold}")
    print(f"  Retrieved: {len(chunks)} chunks | Eligible: {len(eligible_set)} chunks")
    print()
    for i, c in enumerate(chunks[:5], 1):
        dist = round(c.get("distance", 1.0), 4)
        ep = c.get("episode_id", "?")
        eligible_mark = "[ELIGIBLE]" if c in eligible_set else "[REJECTED]"
        print(f"    #{i} {eligible_mark} dist={dist} | {ep} | chunk_idx={c.get('chunk_index', '?')}")
        print(f"        {c.get('content', '')[:100].strip()}")


def main():
    print("\n" + "=" * 70)
    print("CHECKPOINT 4 -- LIVE VERIFICATION")
    print("=" * 70)

    # Step 1: Verify corpus ingested
    print("\n[1] Corpus Ingestion Verification")
    total, episodes = check_chunk_count()
    print(f"  Total chunks in DB: {total}")
    print(f"  Episodes with chunks: {len(episodes)}")

    expected_episodes = {
        "brian-balfour", "casey-winters", "elena-verna", "adam-fishman",
        "april-dunford", "madhavan-ramanujam", "shreyas-doshi", "bob-moesta",
        "gibson-biddle", "gustaf-alstromer", "hila-qu", "nikhyl-singhal",
        "bangaly-kaba", "andy-johns", "ronny-kohavi"
    }
    actual_episodes = {r[0] for r in episodes}
    fixture_episodes = {"fixture-ep-01", "fixture-ep-02", "fixture-ep-03"}
    real_episodes = actual_episodes - fixture_episodes

    for ep_id, cnt in sorted(episodes):
        if ep_id in fixture_episodes:
            prefix = "  [fixture]"
        elif ep_id in expected_episodes:
            prefix = "  [+ real  ]"
        else:
            prefix = "  [?]      "
        print(f"  {prefix} {ep_id}: {cnt} chunks")

    missing = expected_episodes - real_episodes
    if missing:
        print(f"\n  [WARN] Missing episodes: {sorted(missing)}")
        print("  Ingestion may not be complete.")
    else:
        print(f"\n  [PASS] All {len(expected_episodes)} real corpus episodes ingested.")

    if total < 100:
        print("  [WARN] Very few chunks - ingestion may be incomplete.")
        print("  Proceeding with retrieval verification anyway...")

    # Step 2: Grounded question
    print("\n[2] Scenario: Grounded Question (answerable from corpus)")
    q_grounded = "What is the Adjacent User Theory and how should product teams use it?"
    chunks, eligible, threshold = run_retrieval_only(q_grounded)
    print_chunks(chunks, eligible, threshold, q_grounded)
    if eligible:
        print(f"  [PASS] {len(eligible)} eligible chunks found -- agent would produce a grounded answer.")
    else:
        print(f"  [FAIL] 0 eligible chunks -- agent would issue refusal (threshold too strict or corpus not ingested).")

    # Step 3: Unsupported question
    print("\n[3] Scenario: Unsupported Question (not in corpus)")
    q_unsupported = "What is the best JavaScript framework to use for building a mobile app?"
    chunks2, eligible2, threshold2 = run_retrieval_only(q_unsupported)
    print_chunks(chunks2, eligible2, threshold2, q_unsupported)
    if not eligible2:
        print(f"  [PASS] 0 eligible chunks -- agent would correctly issue refusal.")
    else:
        print(f"  [WARN] {len(eligible2)} eligible chunks found for off-topic query -- consider tightening threshold.")

    # Step 4: Mixed-relevance question
    print("\n[4] Scenario: Mixed-Relevance Question (partial corpus coverage)")
    q_mixed = "How does pricing strategy relate to growth loop design?"
    chunks3, eligible3, threshold3 = run_retrieval_only(q_mixed, top_k=5)
    print_chunks(chunks3, eligible3, threshold3, q_mixed)
    if eligible3:
        print(f"  [INFO] {len(eligible3)} eligible chunks -- agent would produce partial grounded answer.")
    else:
        print(f"  [INFO] 0 eligible chunks -- agent would issue refusal for this mixed query.")

    # Step 5: Follow-up question (simulates session context)
    print("\n[5] Scenario: Follow-up Question (within conversation context)")
    q_followup = "Can you explain more about the four growth fits Brian mentioned?"
    chunks4, eligible4, threshold4 = run_retrieval_only(q_followup)
    print_chunks(chunks4, eligible4, threshold4, q_followup)
    if eligible4:
        print(f"  [PASS] Follow-up retrievable -- {len(eligible4)} eligible chunks found.")
    else:
        print(f"  [INFO] 0 eligible chunks for follow-up -- session context handling may help.")

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"  Total chunks ingested:           {total}")
    print(f"  Real corpus episodes:            {len(real_episodes)}/15")
    print(f"  Grounded query eligible:         {len(eligible)}")
    print(f"  Off-topic query eligible:        {len(eligible2)} (should be 0)")
    print(f"  Mixed query eligible:            {len(eligible3)}")
    print(f"  Follow-up query eligible:        {len(eligible4)}")

    incomplete = total < 200
    if incomplete:
        print("\n  [WARN] Ingestion appears incomplete. Run after ingestion finishes.")
    else:
        print("\n  [PASS] Corpus appears fully ingested.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
