#!/usr/bin/env python3
"""
Deterministic retrieval evaluation script for Checkpoint 4.

Runs vector retrieval for every evaluation question without invoking the
reasoning LLM. Records cosine distances, top-k results, and relevant evidence.

Used to calibrate RAG_RELEVANCE_DISTANCE_THRESHOLD empirically.

Usage:
    python ingestion/scripts/run_retrieval_eval.py [--top-k 5] [--output eval_results.json]
"""
import sys
import os
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.session import SessionLocal
from app.services.retrieval_service import search_transcript_chunks
from app.services.embedding_service import embedding_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_retrieval_eval(top_k: int = 5, output_path: Path = None) -> Dict[str, Any]:
    eval_path = ROOT / "ingestion" / "data" / "eval_dataset.json"
    if not eval_path.exists():
        logger.error(f"Eval dataset not found: {eval_path}")
        sys.exit(1)

    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    questions = eval_data.get("questions", [])
    logger.info(f"Loaded {len(questions)} evaluation questions.")

    db = SessionLocal()
    results = []
    answerable_distances = []
    unanswerable_distances = []

    try:
        for q in questions:
            qid = q["id"]
            question_text = q["question"]
            label = q["label"]
            expected_ep = q.get("expected_supporting_episode")
            logger.info(f"[{qid}] {question_text[:80]}...")

            # Run deterministic retrieval (no LLM call)
            chunks = search_transcript_chunks(
                db=db,
                query=question_text,
                top_k=top_k,
            )

            chunk_results = []
            min_distance = None
            relevant_found = False
            relevant_rank = None

            for rank, chunk in enumerate(chunks, start=1):
                distance = float(chunk.get("distance", 1.0))
                ep_id = chunk.get("episode_id", "")
                is_relevant = (
                    expected_ep is not None and
                    ep_id == expected_ep
                )

                if is_relevant and not relevant_found:
                    relevant_found = True
                    relevant_rank = rank

                if min_distance is None or distance < min_distance:
                    min_distance = distance

                chunk_results.append({
                    "rank": rank,
                    "episode_id": ep_id,
                    "episode_title": chunk.get("episode_title", ""),
                    "chunk_index": chunk.get("chunk_index"),
                    "distance": round(distance, 4),
                    "is_relevant_episode": is_relevant,
                    "content_preview": chunk.get("content", "")[:200],
                })

            result = {
                "id": qid,
                "question": question_text,
                "label": label,
                "expected_episode": expected_ep,
                "top_k": top_k,
                "chunks_retrieved": len(chunk_results),
                "min_distance": round(min_distance, 4) if min_distance is not None else None,
                "relevant_evidence_found": relevant_found,
                "relevant_rank": relevant_rank,
                "results": chunk_results,
            }
            results.append(result)

            if label == "answerable_from_corpus" and min_distance is not None:
                answerable_distances.append(min_distance)
            elif label == "unanswerable_from_corpus" and min_distance is not None:
                unanswerable_distances.append(min_distance)

    finally:
        db.close()

    # Distribution summary
    def dist_summary(vals):
        if not vals:
            return {}
        return {
            "count": len(vals),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "mean": round(sum(vals) / len(vals), 4),
            "sorted": [round(v, 4) for v in sorted(vals)],
        }

    output = {
        "metadata": eval_data.get("metadata", {}),
        "top_k": top_k,
        "results": results,
        "distribution": {
            "answerable_min_distances": dist_summary(answerable_distances),
            "unanswerable_min_distances": dist_summary(unanswerable_distances),
        },
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        logger.info(f"Results written to {output_path}")

    return output


def print_summary(output: Dict[str, Any]):
    print("\n" + "=" * 70)
    print("RETRIEVAL EVALUATION SUMMARY")
    print("=" * 70)

    dist = output.get("distribution", {})
    ans = dist.get("answerable_min_distances", {})
    unans = dist.get("unanswerable_min_distances", {})

    print(f"\nAnswerable questions ({ans.get('count', 0)}):")
    print(f"  Min distance range:  {ans.get('min', 'N/A')} – {ans.get('max', 'N/A')}")
    print(f"  Mean min distance:   {ans.get('mean', 'N/A')}")
    print(f"  Distances (sorted):  {ans.get('sorted', [])}")

    print(f"\nUnanswerable questions ({unans.get('count', 0)}):")
    print(f"  Min distance range:  {unans.get('min', 'N/A')} – {unans.get('max', 'N/A')}")
    print(f"  Mean min distance:   {unans.get('mean', 'N/A')}")
    print(f"  Distances (sorted):  {unans.get('sorted', [])}")

    print("\nPer-question results:")
    print(f"{'ID':4} {'Label':30} {'MinDist':8} {'RelevRank':10} {'Top Episode'}")
    print("-" * 80)
    for r in output.get("results", []):
        top_ep = r["results"][0]["episode_id"] if r["results"] else "N/A"
        rel_rank = str(r.get("relevant_rank", "-"))
        label_short = r["label"].replace("_from_corpus", "")
        print(
            f"{r['id']:4} {label_short:30} {str(r['min_distance'] or 'N/A'):8} "
            f"{rel_rank:10} {top_ep}"
        )

    print("\n" + "=" * 70)

    # Threshold recommendation
    if ans.get("max") and unans.get("min"):
        ans_max = ans["max"]
        unans_min = unans["min"]
        if ans_max < unans_min:
            midpoint = round((ans_max + unans_min) / 2, 3)
            print(f"\nDistributions show separation: answerable max={ans_max}, unanswerable min={unans_min}")
            print(f"Suggested threshold midpoint: {midpoint}")
        else:
            print(f"\nDistributions OVERLAP: answerable max={ans_max}, unanswerable min={unans_min}")
            print("No clean threshold boundary visible from this evaluation set.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Run deterministic retrieval evaluation.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve per question.")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path for results.")
    args = parser.parse_args()

    output_path = None
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = ROOT / "ingestion" / "data" / "eval_results.json"

    output = run_retrieval_eval(top_k=args.top_k, output_path=output_path)
    print_summary(output)


if __name__ == "__main__":
    main()
