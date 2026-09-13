#!/usr/bin/env python3
"""
Real corpus ingestion script for Checkpoint 4.

Fetches episodes from the cloned authoritative repository:
  https://github.com/ChatPRD/lennys-podcast-transcripts

Uses corpus_manifest.json to select and drive ingestion.
Runs idempotent upsert into PostgreSQL + pgvector.

Usage:
    python ingestion/scripts/ingest_real_corpus.py [--refresh]

Arguments:
    --refresh   Truncate all transcript_chunks before ingesting (full reload).
                Default: idempotent upsert (safe to re-run).
"""
import sys
import os
import json
import argparse
import logging
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.session import SessionLocal
from app.services.ingestion_service import ingest_manifest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest real Lenny transcript corpus.")
    parser.add_argument("--refresh", action="store_true", help="Truncate chunks table before ingesting.")
    parser.add_argument("--reembed", action="store_true", help="Force re-embedding even if episode exists in DB (for idempotency check).")
    args = parser.parse_args()

    manifest_path = ROOT / "ingestion" / "data" / "corpus_manifest.json"
    raw_repo_dir = ROOT / "ingestion" / "data" / "raw_repo"

    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    if not raw_repo_dir.exists():
        logger.error(
            f"Raw repo directory not found: {raw_repo_dir}\n"
            "Please clone the authoritative source repository first:\n"
            "  git clone https://github.com/ChatPRD/lennys-podcast-transcripts ingestion/data/raw_repo"
        )
        sys.exit(1)

    # Validate manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    episodes = manifest_data.get("episodes", [])
    source_commit = manifest_data.get("metadata", {}).get("source_commit_hash", "unknown")
    logger.info(f"Corpus manifest: {len(episodes)} episodes, source commit: {source_commit}")

    # Validate selected episode files exist before starting
    missing = []
    for ep in episodes:
        rel = ep.get("source_path", "")
        fpath = raw_repo_dir / rel
        if not fpath.exists():
            missing.append((ep.get("episode_id"), str(fpath)))
    if missing:
        for ep_id, fp in missing:
            logger.error(f"MISSING: {ep_id} -> {fp}")
        logger.error(f"{len(missing)} episode files missing. Aborting.")
        sys.exit(1)

    logger.info(f"All {len(episodes)} episode files verified present.")
    logger.info(f"Refresh mode: {args.refresh}, Re-embed mode: {args.reembed}")

    db = SessionLocal()
    try:
        results = ingest_manifest(
            manifest_path=manifest_path,
            raw_repo_dir=raw_repo_dir,
            db=db,
            refresh=args.refresh,
            skip_existing=not args.reembed,
        )
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("INGESTION RESULTS")
    print("=" * 60)
    print(f"Source commit:    {source_commit}")
    print(f"Episodes in manifest: {len(episodes)}")
    print(f"Files processed:  {results['files_processed']}")
    print(f"Total chunks:     {results['total_chunks']}")
    print(f"Duration:         {results['duration_sec']}s")
    print()

    succeeded = [d for d in results["details"] if d.get("status") == "success"]
    skipped = [d for d in results["details"] if d.get("status") != "success"]

    print(f"Succeeded: {len(succeeded)}")
    for d in succeeded:
        print(f"  {d.get('episode_id','?'):35s} {d.get('chunks', 0):4d} chunks  [{d.get('episode_title','')[:50]}]")

    if skipped:
        print(f"\nSkipped/Failed: {len(skipped)}")
        for d in skipped:
            print(f"  {d.get('episode_id', '?'):35s} reason={d.get('reason', '?')}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
