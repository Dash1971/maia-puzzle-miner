from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .policy.base import PolicyProvider
from .scoring import assess
from .source import iter_puzzles
from .store import AssessmentStore


@dataclass
class ScanStats:
    read: int = 0
    assessed: int = 0
    skipped: int = 0
    selected: int = 0
    invalid: int = 0


def scan(
    source: Path,
    database: Path,
    elos: Iterable[int],
    provider: PolicyProvider,
    max_correct_probability: float,
    limit: int | None = None,
    commit_every: int = 100,
) -> ScanStats:
    stats = ScanStats()
    store = AssessmentStore(database)
    try:
        iterator = iter_puzzles(source)
        while limit is None or stats.read < limit:
            try:
                puzzle = next(iterator)
            except StopIteration:
                break
            except (KeyError, TypeError, ValueError):
                stats.invalid += 1
                continue

            stats.read += 1
            for elo in elos:
                if store.contains(puzzle.puzzle_id, elo, provider.model_id):
                    stats.skipped += 1
                    continue
                item = assess(puzzle, elo, provider, max_correct_probability)
                store.put(item)
                stats.assessed += 1
                stats.selected += int(item.selected)
                if stats.assessed % commit_every == 0:
                    store.commit()
        store.commit()
    finally:
        store.close()
    return stats
