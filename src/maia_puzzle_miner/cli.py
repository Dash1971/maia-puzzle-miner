from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import scan
from .policy.maia3 import Maia3PolicyProvider
from .store import AssessmentStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="maia-puzzle-miner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="score a Lichess puzzle corpus")
    scan_parser.add_argument("source", type=Path)
    scan_parser.add_argument("--database", type=Path, required=True)
    scan_parser.add_argument("--elo", type=int, action="append", required=True)
    scan_parser.add_argument("--model", default="maia3-5m")
    scan_parser.add_argument("--device")
    scan_parser.add_argument("--max-correct-probability", type=float, default=0.05)
    scan_parser.add_argument("--limit", type=int)

    export_parser = subparsers.add_parser("export", help="export selected rows as JSONL")
    export_parser.add_argument("--database", type=Path, required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "scan":
        if not 0 <= args.max_correct_probability <= 1:
            raise SystemExit("--max-correct-probability must be between 0 and 1")
        provider = Maia3PolicyProvider(model=args.model, device=args.device)
        stats = scan(
            source=args.source,
            database=args.database,
            elos=args.elo,
            provider=provider,
            max_correct_probability=args.max_correct_probability,
            limit=args.limit,
        )
        print(json.dumps(stats.__dict__, sort_keys=True))
        return

    store = AssessmentStore(args.database)
    try:
        with args.output.open("w", encoding="utf-8") as output:
            for item in store.selected_json():
                output.write(json.dumps(item, separators=(",", ":")) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
