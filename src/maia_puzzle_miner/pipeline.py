from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import chess

from .policy.base import PolicyProvider
from .scoring import assess, assess_probabilities
from .source import iter_puzzles
from .store import AssessmentStore


@dataclass
class ScanStats:
    sampled: int = 0
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
    sample_modulus: int | None = None,
    min_plays: int = 0,
    min_popularity: int = -100,
    min_rating: int = 0,
    max_rating: int = 4000,
) -> ScanStats:
    stats = ScanStats()
    elo_values = list(elos)
    store = AssessmentStore(database)
    try:
        iterator = iter_puzzles(source, sample_modulus=sample_modulus)
        while limit is None or stats.read < limit:
            try:
                puzzle = next(iterator)
            except StopIteration:
                break
            except (KeyError, TypeError, ValueError):
                stats.invalid += 1
                continue

            stats.sampled += 1
            if not (
                puzzle.plays >= min_plays
                and puzzle.popularity >= min_popularity
                and min_rating <= puzzle.rating <= max_rating
            ):
                continue
            stats.read += 1
            pending_elos = [
                elo
                for elo in elo_values
                if not store.contains(puzzle.puzzle_id, elo, provider.model_id)
            ]
            stats.skipped += len(elo_values) - len(pending_elos)
            if not pending_elos:
                continue

            probabilities_many = getattr(provider, "probabilities_many", None)
            policies = (
                probabilities_many(chess.Board(puzzle.presented_fen), pending_elos)
                if probabilities_many is not None
                else None
            )
            for elo in pending_elos:
                item = (
                    assess_probabilities(
                        puzzle,
                        elo,
                        provider.model_id,
                        policies[elo],
                        max_correct_probability,
                    )
                    if policies is not None
                    else assess(puzzle, elo, provider, max_correct_probability)
                )
                store.put(item)
                stats.assessed += 1
                stats.selected += int(item.selected)
                if stats.assessed % commit_every == 0:
                    store.commit()
        store.commit()
    finally:
        store.close()
    return stats
