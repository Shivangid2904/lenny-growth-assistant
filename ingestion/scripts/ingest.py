#!/usr/bin/env python3
"""
Transcript Ingestion CLI for Lenny Growth Assistant.

Usage:
    python ingestion/scripts/ingest.py [--data-dir PATH] [--refresh] [--chunk-size N] [--chunk-overlap N]
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.db.session import SessionLocal
from app.services.ingestion_service import ingest_directory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest")


def main():
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts into PostgreSQL/pgvector.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(BASE_DIR / "ingestion" / "data" / "transcripts"),
        help="Path to directory containing transcript files (.json, .md, .txt)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Full refresh: wipe existing transcript_chunks before re-ingesting",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Target chunk size in characters (approx 200-250 words)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=150,
        help="Overlap characters between adjacent chunks",
    )
    args = parser.parse_args()

    data_path = Path(args.data_dir)
    print(f"[*] Starting ingestion from: {data_path.resolve()}")
    print(f"[*] Mode: {'Full Refresh (TRUNCATE)' if args.refresh else 'Idempotent Upsert'}")
    print(f"[*] Embedding Model: {settings.ollama_embedding_model} (768-dim) via {settings.ollama_base_url}")
    print(f"[*] Database: {settings.database_url}")

    db = SessionLocal()
    try:
        summary = ingest_directory(
            directory_path=data_path,
            db=db,
            refresh=args.refresh,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print("\n[+] Ingestion Completed Successfully:")
        print(f"    - Files processed: {summary['files_processed']}")
        print(f"    - Total chunks stored: {summary['total_chunks']}")
        print(f"    - Duration: {summary['duration_sec']}s")
        for detail in summary["details"]:
            print(f"      * {detail.get('episode_title', detail.get('file'))}: {detail.get('chunks', 0)} chunks ({detail.get('status')})")
    except Exception as exc:
        print(f"\n[-] Ingestion failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
