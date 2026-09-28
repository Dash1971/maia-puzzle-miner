from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from pathlib import Path

import chess

PIECE_CHANNEL = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
    chess.KING: 5,
}


def mirror_move(uci: str) -> str:
    def mirror_square(square: str) -> str:
        return f"{square[0]}{9 - int(square[1])}"

    promotion = uci[4:] if len(uci) == 5 else ""
    return f"{mirror_square(uci[:2])}{mirror_square(uci[2:4])}{promotion}"


def move_index(uci: str, black_to_move: bool) -> int:
    normalized = mirror_move(uci) if black_to_move else uci
    if len(normalized) == 5:
        from_file = ord(normalized[0]) - ord("a")
        to_file = ord(normalized[2]) - ord("a")
        piece = {"q": 0, "r": 1, "b": 2, "n": 3}[normalized[4]]
        return 4096 + ((from_file * 8 + to_file) * 4 + piece)

    def square_index(square: str) -> int:
        return ord(square[0]) - ord("a") + (int(square[1]) - 1) * 8

    return square_index(normalized[:2]) * 64 + square_index(normalized[2:4])


def historical_tokens(board: chess.Board):
    """Encode the released Maia-3 current-position-only 64x97 tensor."""
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Maia-3 ONNX support requires pip install -e '.[maia3]'") from exc

    perspective = board.mirror() if board.turn == chess.BLACK else board
    tokens = np.zeros((1, 64, 97), dtype=np.float32)
    for square, piece in perspective.piece_map().items():
        channel = PIECE_CHANNEL[piece.piece_type] + (0 if piece.color == chess.WHITE else 6)
        for history in range(8):
            tokens[0, square, history * 12 + channel] = 1.0
    return tokens


class Maia3PolicyProvider:
    """Read the full legal-move policy from a Maia-3 ONNX model."""

    def __init__(self, model_path: Path) -> None:
        if not model_path.is_file():
            raise RuntimeError(f"Maia-3 ONNX model not found: {model_path}")
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Maia-3 ONNX support requires pip install -e '.[maia3]'") from exc

        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        self.model_id = f"{model_path.stem}-onnx-{digest[:12]}"
        self._session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])

    def probabilities(self, board: chess.Board, elo: int) -> Mapping[str, float]:
        return self.probabilities_many(board, [elo])[elo]

    def probabilities_many(
        self, board: chess.Board, elos: list[int]
    ) -> Mapping[int, Mapping[str, float]]:
        import numpy as np

        tokens = np.repeat(historical_tokens(board), len(elos), axis=0)
        elo_values = np.asarray(elos, dtype=np.int64)
        logits = self._session.run(
            ["move_logits"],
            {
                "tokens": tokens,
                "self_elo": elo_values,
                "opponent_elo": elo_values,
            },
        )[0]
        legal_moves = [move.uci() for move in board.legal_moves]
        indices = [move_index(move, board.turn == chess.BLACK) for move in legal_moves]
        result: dict[int, Mapping[str, float]] = {}
        for elo, policy_logits in zip(elos, logits, strict=True):
            scores = [float(policy_logits[index]) for index in indices]
            maximum = max(scores)
            weights = [math.exp(score - maximum) for score in scores]
            total = sum(weights)
            result[elo] = {
                move: weight / total for move, weight in zip(legal_moves, weights, strict=True)
            }
        return result
