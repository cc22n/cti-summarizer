"""Manual ingestion CLI script.

Usage:
    python -m scripts.run_ingestion --source nvd
    python -m scripts.run_ingestion --source cisa_kev
    python -m scripts.run_ingestion --all
"""

import argparse
import asyncio
import logging
import sys

from app.database import SessionLocal
from app.services.ingestion import NVDAdapter, CISAKEVAdapter
from app.services.ingestion_orchestrator import IngestionOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

ADAPTERS = {
    "nvd": NVDAdapter,
    "cisa_kev": CISAKEVAdapter,
}


async def run_ingestion(source_keys: list[str]):
    """Run ingestion for specified sources."""
    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db)
        for key in source_keys:
            adapter_cls = ADAPTERS.get(key)
            if not adapter_cls:
                print(f"Unknown source: {key}")
                continue

            print(f"\n--- Ingesting: {key} ---")
            adapter = adapter_cls()
            result = await orchestrator.run(adapter)
            print(f"  Status: {result.status}")
            print(f"  Fetched: {result.alerts_fetched}")
            print(f"  New: {result.alerts_new}")
            if result.error_message:
                print(f"  Error: {result.error_message}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Run CTI feed ingestion")
    parser.add_argument(
        "--source",
        choices=list(ADAPTERS.keys()),
        help="Source to ingest",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest from all sources",
    )
    args = parser.parse_args()

    if args.all:
        keys = list(ADAPTERS.keys())
    elif args.source:
        keys = [args.source]
    else:
        parser.print_help()
        sys.exit(1)

    asyncio.run(run_ingestion(keys))


if __name__ == "__main__":
    main()
