# Maia Puzzle Miner

Find Lichess puzzles where the objectively correct move is statistically unlikely to
be played by a human at a chosen rating, according to Maia. These are candidates for
counterintuitive, explanation-rich training puzzles.

This repository is the data-generation side of
[`maia-chess-android-preview` issue #34](https://github.com/Dash1971/maia-chess-android-preview/issues/34).

## Status

Early scaffold. The streaming parser, puzzle reconstruction, SQLite schema, scoring,
resumption, JSONL export, and Maia-3 policy adapter are in place. A representative
end-to-end scan with a downloaded Maia checkpoint is the next milestone.

## Why this is distinct

Existing projects evaluate Maia's aggregate puzzle performance, predict puzzle ratings,
or filter Lichess puzzles with Stockfish. This pipeline targets a different question:

> At rating *R*, how unlikely is the known correct move under Maia's legal-move policy?

The first ranking signal is `-log2(P(correct move | position, Elo))`. The database also
keeps the correct move's policy rank and the most likely human move for later Maia versus
Stockfish explanations.

## Pipeline

1. Stream the Lichess puzzle CSV without expanding it on disk.
2. Apply the first move in `Moves` to the source FEN. Lichess defines that as the
   opponent's setup move; the second move is the solver's first correct move.
3. Ask Maia-3 for a probability over all legal moves at the target Elo.
4. Persist the assessment in SQLite. Rows at or below `--max-correct-probability` are
   marked selected.
5. Export selected rows as JSONL for review or Android ingestion.

## Setup

Python 3.10+ is required.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev,maia3]'
```

The Maia-3 extra is pinned to a reviewed upstream commit. The first real scan downloads
the selected model checkpoint from Hugging Face unless it is already cached.

## Scan

```bash
maia-puzzle-miner scan ~/Downloads/lichess_db_puzzle.csv.zst \
  --database puzzles.sqlite \
  --elo 1500 \
  --model maia3-5m \
  --max-correct-probability 0.05
```

Safe smoke test:

```bash
maia-puzzle-miner scan tests/fixtures/puzzles.csv \
  --database smoke.sqlite --elo 1500 --model maia3-5m --limit 2
```

Export selected candidates:

```bash
maia-puzzle-miner export --database puzzles.sqlite --output selected.jsonl
```

Re-running `scan` against the same database skips already assessed puzzle/Elo pairs.
The source files, model checkpoints, and generated databases are intentionally ignored.

## Important limitations

- Lichess's puzzle CSV provides a FEN and continuation, not the preceding game history.
  Maia-3 therefore receives the presented position padded as history. A future optional
  game-PGN join can restore true history.
- Low policy probability is a candidate signal, not proof of instructional quality.
  Candidates still need uniqueness checks, deduplication, and human review.
- Maia's policy models likely human play; Stockfish remains the authority for objective
  move quality and explanation lines.

## Data and licensing

- Lichess database exports are published under CC0. Do not commit the source corpus or
  generated bulk databases here.
- This project's original code is MIT-licensed.
- Maia-3 is an optional external dependency licensed under AGPL-3.0. Installing,
  distributing, or deploying the combined system remains subject to Maia-3's upstream
  license terms; this repository's MIT license does not relicense Maia-3.
- No Maia model weights are redistributed by this repository.

See [docs/research.md](docs/research.md) for the prior-art search and design rationale.
