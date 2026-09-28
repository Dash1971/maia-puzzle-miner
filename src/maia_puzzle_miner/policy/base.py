from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import chess


class PolicyProvider(Protocol):
    model_id: str

    def probabilities(self, board: chess.Board, elo: int) -> Mapping[str, float]: ...
