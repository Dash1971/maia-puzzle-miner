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
    scan_parser.add_argument("--model-path", type=Path, required=True)
    scan_parser.add_argument("--max-correct-probability", type=float, default=0.05)
    scan_parser.add_argument("--limit", type=int)
    scan_parser.add_argument("--sample-modulus", type=int)
    scan_parser.add_argument("--min-plays", type=int, default=0)
    scan_parser.add_argument("--min-popularity", type=int, default=-100)
    scan_parser.add_argument("--min-rating", type=int, default=0)
    scan_parser.add_argument("--max-rating", type=int, default=4000)

    export_parser = subparsers.add_parser("export", help="export selected rows as JSONL")
    export_parser.add_argument("--database", type=Path, required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--min-selected-elos", type=int, default=1)
    export_parser.add_argument("--max-puzzles", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "scan":
        if not 0 <= args.max_correct_probability <= 1:
            raise SystemExit("--max-correct-probability must be between 0 and 1")
        if args.sample_modulus is not None and args.sample_modulus < 1:
            raise SystemExit("--sample-modulus must be positive")
        provider = Maia3PolicyProvider(model_path=args.model_path)
        stats = scan(
            source=args.source,
            database=args.database,
            elos=args.elo,
            provider=provider,
            max_correct_probability=args.max_correct_probability,
            limit=args.limit,
            sample_modulus=args.sample_modulus,
            min_plays=args.min_plays,
            min_popularity=args.min_popularity,
            min_rating=args.min_rating,
            max_rating=args.max_rating,
        )
        print(json.dumps(stats.__dict__, sort_keys=True))
        return

    store = AssessmentStore(args.database)
    try:
        with args.output.open("w", encoding="utf-8") as output:
            for item in store.selected_grouped_json(
                min_selected_elos=args.min_selected_elos,
                limit=args.max_puzzles,
            ):
                output.write(json.dumps(item, separators=(",", ":")) + "\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
