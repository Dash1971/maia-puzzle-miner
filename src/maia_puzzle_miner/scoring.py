from __future__ import annotations

import math

import chess

from .domain import Assessment, Puzzle
from .policy.base import PolicyProvider


def assess(
    puzzle: Puzzle,
    elo: int,
    provider: PolicyProvider,
    max_correct_probability: float,
) -> Assessment:
    board = chess.Board(puzzle.presented_fen)
    probabilities = dict(provider.probabilities(board, elo))
    legal_moves = {move.uci() for move in board.legal_moves}
    if set(probabilities) != legal_moves:
        missing = sorted(legal_moves - set(probabilities))
        extra = sorted(set(probabilities) - legal_moves)
        raise ValueError(f"policy does not match legal moves; missing={missing}, extra={extra}")

    total = sum(probabilities.values())
    if total <= 0:
        raise ValueError("policy probability total must be positive")
    normalized = {move: value / total for move, value in probabilities.items()}
    ordered = sorted(normalized.items(), key=lambda item: (-item[1], item[0]))
    correct_probability = normalized[puzzle.correct_move]
    correct_rank = next(
        i for i, item in enumerate(ordered, start=1) if item[0] == puzzle.correct_move
    )
    top_move, top_probability = ordered[0]

    return Assessment(
        puzzle=puzzle,
        target_elo=elo,
        model=provider.model_id,
        correct_probability=correct_probability,
        correct_rank=correct_rank,
        top_move=top_move,
        top_probability=top_probability,
        surprise_bits=-math.log2(max(correct_probability, 1e-15)),
        selected=correct_probability <= max_correct_probability,
    )
